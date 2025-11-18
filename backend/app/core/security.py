"""
安全服务模块
提供 API 密钥加密/解密、密码哈希和 JWT 认证功能
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from cryptography.fernet import Fernet
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select
from app.core.database import get_session
from app.models import User

# 从环境变量获取主加密密钥
MASTER_ENCRYPTION_KEY = os.getenv("MASTER_ENCRYPTION_KEY")
if not MASTER_ENCRYPTION_KEY:
    raise ValueError("MASTER_ENCRYPTION_KEY 环境变量必须设置")

# 如果设置为 "generate"，则自动生成密钥（仅用于开发环境）
if MASTER_ENCRYPTION_KEY == "generate":
    MASTER_ENCRYPTION_KEY = Fernet.generate_key().decode()
    print(f"生成的加密密钥: {MASTER_ENCRYPTION_KEY}")
    print("警告: 请保存此密钥用于生产环境！")


class EncryptionService:
    """
    加密服务类
    使用 Fernet 对称加密算法对 API 密钥进行加密和解密
    """
    
    def __init__(self, key: bytes):
        """
        初始化加密服务
        :param key: Fernet 加密密钥（字节格式）
        """
        self.fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """
        加密字符串数据
        :param data: 要加密的明文字符串
        :return: 加密后的密文字符串
        """
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, token: str) -> str:
        """
        解密字符串数据
        :param token: 要解密的密文字符串
        :return: 解密后的明文字符串
        """
        return self.fernet.decrypt(token.encode()).decode()


# 初始化加密服务实例（全局单例）
encryption_service = EncryptionService(MASTER_ENCRYPTION_KEY.encode())

# 密码哈希上下文，使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 配置
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")  # JWT 签名密钥
ALGORITHM = os.getenv("ALGORITHM", "HS256")  # JWT 签名算法
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))  # Token 过期时间（分钟）

# OAuth2 密码承载方案，用于从请求中提取 JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希密码是否匹配
    :param plain_password: 明文密码
    :param hashed_password: 哈希密码
    :return: 是否匹配
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    对密码进行哈希处理
    :param password: 明文密码
    :return: 哈希后的密码
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT 访问令牌
    :param data: 要编码到 token 中的数据（通常包含用户邮箱）
    :param expires_delta: 可选的过期时间增量
    :return: 编码后的 JWT token 字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})  # 添加过期时间
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: Session = Depends(get_session)
) -> User:
    """
    获取当前认证用户（FastAPI 依赖项）
    从 JWT token 中提取用户信息并验证
    :param token: JWT token（从请求头中自动提取）
    :param session: 数据库会话
    :return: 用户对象
    :raises HTTPException: 如果 token 无效或用户不存在
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码并验证 JWT token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")  # 从 payload 中获取用户邮箱
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 从数据库查询用户
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户未激活"
        )
    return user
