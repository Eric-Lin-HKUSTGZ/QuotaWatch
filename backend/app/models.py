"""
数据模型定义
使用 SQLModel 定义数据库表结构和关系
"""
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class User(SQLModel, table=True):
    """
    用户模型
    存储用户账户信息
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键
    email: str = Field(unique=True, index=True)  # 邮箱，唯一且建立索引
    hashed_password: str  # 加密后的密码
    is_active: bool = Field(default=True)  # 账户是否激活
    created_at: datetime = Field(default_factory=datetime.utcnow)  # 创建时间
    
    # 关系：一个用户可以有多个 API 密钥
    api_keys: List["ManagedApiKey"] = Relationship(back_populates="user")


class PlatformProvider(SQLModel, table=True):
    """
    平台提供商模型
    存储支持的 API 平台信息（如 OpenRouter、OpenAI 等）
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键
    name: str  # 平台名称（如 "OpenRouter"）
    slug: str = Field(unique=True, index=True)  # 平台标识符（如 "openrouter"），唯一且建立索引
    adapter_identifier: str  # 适配器标识符，用于查找对应的适配器类（如 "openrouter", "openai"）
    created_at: datetime = Field(default_factory=datetime.utcnow)  # 创建时间
    
    # 关系：一个平台可以有多个 API 密钥
    api_keys: List["ManagedApiKey"] = Relationship(back_populates="platform")


class ManagedApiKey(SQLModel, table=True):
    """
    管理的 API 密钥模型
    存储用户添加的 API 密钥信息（密钥已加密存储）
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键
    name: str  # 密钥名称（用户自定义）
    api_key_encrypted: str  # 加密后的 API 密钥（使用 Fernet 对称加密）
    metadata: Dict[str, Any] = Field(default_factory=dict, sa_column_kwargs={"type_": "JSON"})  # 元数据（JSON 格式，如 OpenAI 的 total_grant）
    last_known_balance: Optional[float] = None  # 最后已知的余额
    last_checked: Optional[datetime] = None  # 最后检查时间
    user_id: int = Field(foreign_key="user.id")  # 外键：所属用户
    platform_id: int = Field(foreign_key="platformprovider.id")  # 外键：所属平台
    created_at: datetime = Field(default_factory=datetime.utcnow)  # 创建时间
    updated_at: datetime = Field(default_factory=datetime.utcnow)  # 更新时间
    
    # 关系定义
    user: User = Relationship(back_populates="api_keys")  # 所属用户
    platform: PlatformProvider = Relationship(back_populates="api_keys")  # 所属平台
    balance_logs: List["BalanceLog"] = Relationship(back_populates="api_key")  # 余额历史记录
    notification_rule: Optional["NotificationRule"] = Relationship(back_populates="api_key")  # 通知规则（可选）


class BalanceLog(SQLModel, table=True):
    """
    余额日志模型
    记录每次余额检查的历史数据，用于绘制余额趋势图
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)  # 记录时间，建立索引以便快速查询
    balance: float  # 余额值
    key_id: int = Field(foreign_key="managedapikey.id")  # 外键：关联的 API 密钥
    
    # 关系：属于某个 API 密钥
    api_key: ManagedApiKey = Relationship(back_populates="balance_logs")


class NotificationRule(SQLModel, table=True):
    """
    通知规则模型
    定义当余额低于阈值时如何发送通知
    """
    id: Optional[int] = Field(default=None, primary_key=True)  # 主键
    threshold_amount: float  # 阈值金额，当余额低于此值时触发通知
    notification_channel: str  # 通知渠道："email" 或 "webhook"
    channel_address: str  # 渠道地址：邮箱地址或 Webhook URL
    key_id: int = Field(foreign_key="managedapikey.id", unique=True)  # 外键：关联的 API 密钥（唯一，一个密钥只能有一个通知规则）
    created_at: datetime = Field(default_factory=datetime.utcnow)  # 创建时间
    
    # 关系：属于某个 API 密钥
    api_key: ManagedApiKey = Relationship(back_populates="notification_rule")
