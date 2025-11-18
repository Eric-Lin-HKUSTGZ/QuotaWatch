"""
数据库配置模块
提供数据库连接引擎和会话管理
"""
from sqlmodel import SQLModel, create_engine, Session
import os

# 从环境变量获取数据库连接 URL，默认使用本地 PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://quotawatch:quotawatch_dev@localhost:5432/quotawatch")

# 创建数据库引擎
# echo=True 表示打印所有 SQL 语句（开发环境有用，生产环境应设为 False）
engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    """
    初始化数据库表结构
    根据 SQLModel 模型定义创建所有表
    注意：生产环境应使用 Alembic 进行迁移管理
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    获取数据库会话的依赖项函数
    用于 FastAPI 的 Depends，确保每个请求都有独立的数据库会话
    使用上下文管理器自动处理会话的创建和关闭
    :yield: 数据库会话对象
    """
    with Session(engine) as session:
        yield session
