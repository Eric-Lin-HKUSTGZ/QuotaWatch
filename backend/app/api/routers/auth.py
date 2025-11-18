"""
认证路由模块
提供用户注册、登录和获取当前用户信息的 API 端点
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from pydantic import BaseModel, EmailStr
from app.core.database import get_session
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.models import User

router = APIRouter()


class Token(BaseModel):
    """Token 响应模型"""
    access_token: str  # JWT 访问令牌
    token_type: str  # Token 类型（通常是 "bearer"）


class UserCreate(BaseModel):
    """用户创建请求模型"""
    email: EmailStr  # 用户邮箱（必须是有效的邮箱格式）
    password: str  # 用户密码（明文）


class UserResponse(BaseModel):
    """用户响应模型"""
    id: int  # 用户 ID
    email: str  # 用户邮箱
    is_active: bool  # 账户是否激活

    class Config:
        from_attributes = True  # 允许从 ORM 对象创建


@router.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, session: Session = Depends(get_session)):
    """
    注册新用户
    :param user_data: 用户注册信息（邮箱和密码）
    :param session: 数据库会话
    :return: 创建的用户信息
    :raises HTTPException: 如果邮箱已被注册
    """
    # 检查用户是否已存在
    existing_user = session.exec(select(User).where(User.email == user_data.email)).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被注册"
        )
    
    # 创建新用户
    hashed_password = get_password_hash(user_data.password)  # 对密码进行哈希处理
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True  # 默认激活账户
    )
    session.add(new_user)
    session.commit()
    session.refresh(new_user)  # 刷新以获取数据库生成的 ID
    
    return new_user


@router.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: Session = Depends(get_session)
):
    """
    用户登录
    使用 OAuth2 密码流进行认证，返回 JWT token
    :param form_data: OAuth2 表单数据（包含 username 和 password）
    :param session: 数据库会话
    :return: JWT token 和类型
    :raises HTTPException: 如果邮箱或密码错误，或账户未激活
    """
    # 查找用户（OAuth2PasswordRequestForm 使用 username 字段存储邮箱）
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    
    # 验证密码
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查账户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户未激活"
        )
    
    # 创建 JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email},  # "sub" 是 JWT 标准中的 subject 字段
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户信息
    需要有效的 JWT token
    :param current_user: 当前用户（通过 JWT token 自动获取）
    :return: 用户信息
    """
    return current_user
