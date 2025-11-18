"""
API 密钥路由模块
提供 API 密钥的 CRUD 操作、测试、触发检查和余额历史查询
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from pydantic import BaseModel
from arq import create_pool
from app.core.database import get_session
from app.core.security import get_current_user, encryption_service
from app.models import User, ManagedApiKey, PlatformProvider, BalanceLog
from app.services.adapter_factory import AdapterFactory
from app.services.adapters.base import BalanceFetchResult
from app.worker import redis_settings

router = APIRouter()


class ApiKeyCreate(BaseModel):
    """创建 API 密钥请求模型"""
    name: str  # 密钥名称
    api_key: str  # API 密钥（明文，会在存储前加密）
    platform_id: int  # 平台 ID
    metadata: Optional[Dict[str, Any]] = None  # 元数据（如 OpenAI 的 total_grant）


class ApiKeyResponse(BaseModel):
    """API 密钥响应模型"""
    id: int  # 密钥 ID
    name: str  # 密钥名称
    platform_id: int  # 平台 ID
    metadata: Dict[str, Any]  # 元数据
    last_known_balance: Optional[float]  # 最后已知余额
    last_checked: Optional[datetime]  # 最后检查时间
    created_at: datetime  # 创建时间
    updated_at: datetime  # 更新时间

    class Config:
        from_attributes = True


class ApiKeyTestRequest(BaseModel):
    """测试 API 密钥请求模型"""
    platform_id: int  # 平台 ID
    api_key: str  # API 密钥（明文）
    metadata: Optional[Dict[str, Any]] = None  # 元数据


class BalanceHistoryResponse(BaseModel):
    """余额历史响应模型"""
    id: int  # 记录 ID
    timestamp: datetime  # 记录时间
    balance: float  # 余额值

    class Config:
        from_attributes = True


@router.get("/platforms", response_model=List[PlatformProvider])
async def list_platforms(session: Session = Depends(get_session)):
    """
    获取所有可用的平台提供商列表
    不需要认证，用于前端下拉选择框
    :param session: 数据库会话
    :return: 平台提供商列表
    """
    platforms = session.exec(select(PlatformProvider)).all()
    return platforms


@router.get("/keys", response_model=List[ApiKeyResponse])
async def list_keys(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    获取当前用户的所有 API 密钥列表
    需要认证
    :param current_user: 当前登录用户
    :param session: 数据库会话
    :return: API 密钥列表
    """
    keys = session.exec(
        select(ManagedApiKey).where(ManagedApiKey.user_id == current_user.id)
    ).all()
    return keys


@router.post("/keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    key_data: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    创建新的 API 密钥
    重要：API 密钥会在存储前使用 Fernet 加密
    需要认证
    :param key_data: API 密钥创建数据
    :param current_user: 当前登录用户
    :param session: 数据库会话
    :return: 创建的 API 密钥信息
    :raises HTTPException: 如果平台不存在
    """
    # 验证平台是否存在
    platform = session.exec(
        select(PlatformProvider).where(PlatformProvider.id == key_data.platform_id)
    ).first()
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="平台不存在"
        )
    
    # 加密 API 密钥（重要：只存储加密后的密钥）
    encrypted_key = encryption_service.encrypt(key_data.api_key)
    
    # 创建新的 API 密钥记录
    new_key = ManagedApiKey(
        name=key_data.name,
        api_key_encrypted=encrypted_key,  # 存储加密后的密钥
        platform_id=key_data.platform_id,
        user_id=current_user.id,
        metadata=key_data.metadata or {},
    )
    session.add(new_key)
    session.commit()
    session.refresh(new_key)
    
    return new_key


@router.post("/keys/test", response_model=BalanceFetchResult)
async def test_key(
    test_data: ApiKeyTestRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    测试 API 密钥（不保存到数据库）
    用于在添加密钥前验证密钥是否有效
    需要认证
    :param test_data: 测试数据
    :param current_user: 当前登录用户
    :param session: 数据库会话
    :return: 余额查询结果
    :raises HTTPException: 如果平台不存在或测试失败
    """
    # 获取平台信息
    platform = session.exec(
        select(PlatformProvider).where(PlatformProvider.id == test_data.platform_id)
    ).first()
    if not platform:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="平台不存在"
        )
    
    try:
        # 创建适配器并获取余额
        adapter = AdapterFactory.create_adapter(
            adapter_identifier=platform.adapter_identifier,
            api_key=test_data.api_key,
            metadata=test_data.metadata or {}
        )
        result = await adapter.fetch_balance()
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"测试 API 密钥失败: {str(e)}"
        )


@router.post("/keys/{key_id}/trigger-check", status_code=status.HTTP_202_ACCEPTED)
async def trigger_check(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    手动触发指定密钥的余额检查
    将检查任务加入 Arq 队列，立即执行
    需要认证
    :param key_id: API 密钥 ID
    :param current_user: 当前登录用户
    :param session: 数据库会话
    :return: 任务已加入队列的确认信息
    :raises HTTPException: 如果密钥不存在或不属于当前用户
    """
    # 验证密钥是否存在且属于当前用户
    api_key = session.exec(
        select(ManagedApiKey).where(
            ManagedApiKey.id == key_id,
            ManagedApiKey.user_id == current_user.id
        )
    ).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API 密钥不存在"
        )
    
    # 将检查任务加入队列
    try:
        redis_pool = await create_pool(redis_settings)
        await redis_pool.enqueue_job("check_single_key", key_id=key_id)
        await redis_pool.close()
        return {"message": "余额检查任务已加入队列", "key_id": key_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"加入队列失败: {str(e)}"
        )


@router.get("/keys/{key_id}/balance-history", response_model=List[BalanceHistoryResponse])
async def get_balance_history(
    key_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    获取指定密钥的余额历史记录
    按时间倒序排列，用于绘制余额趋势图
    需要认证
    :param key_id: API 密钥 ID
    :param current_user: 当前登录用户
    :param session: 数据库会话
    :return: 余额历史记录列表
    :raises HTTPException: 如果密钥不存在或不属于当前用户
    """
    # 验证密钥是否存在且属于当前用户
    api_key = session.exec(
        select(ManagedApiKey).where(
            ManagedApiKey.id == key_id,
            ManagedApiKey.user_id == current_user.id
        )
    ).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API 密钥不存在"
        )
    
    # 获取余额日志（按时间倒序）
    logs = session.exec(
        select(BalanceLog)
        .where(BalanceLog.key_id == key_id)
        .order_by(BalanceLog.timestamp.desc())
    ).all()
    
    return logs
