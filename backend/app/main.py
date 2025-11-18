"""
FastAPI 应用主入口文件
负责初始化应用、配置中间件、注册路由和启动定时任务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.database import init_db
from app.api.routers import keys, auth
from app.worker import schedule_all_key_checks
import sys
import os

# 将父目录添加到路径中，以便导入种子脚本
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 创建异步调度器实例，用于定时任务
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    在应用启动时初始化数据库、种子数据和调度器
    在应用关闭时关闭调度器
    """
    # 启动时执行
    init_db()  # 初始化数据库表结构
    # 种子平台提供商数据
    try:
        from seed_platforms import seed_platforms
        seed_platforms()
    except Exception as e:
        print(f"警告: 无法种子平台数据: {e}")
    scheduler.start()  # 启动调度器
    # 每 30 分钟执行一次所有密钥的余额检查
    scheduler.add_job(
        schedule_all_key_checks,
        trigger=IntervalTrigger(minutes=30),
        id="check_all_keys",
        replace_existing=True,
    )
    yield
    # 关闭时执行
    scheduler.shutdown()  # 关闭调度器


# 创建 FastAPI 应用实例
app = FastAPI(
    title="QuotaWatch API",
    description="API Key Quota Monitoring Dashboard",
    version="1.0.0",
    lifespan=lifespan,
)

# 配置 CORS 中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 允许的前端地址
    allow_credentials=True,  # 允许携带凭证
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)

# 注册路由
app.include_router(auth.router, prefix="/api", tags=["auth"])  # 认证相关路由
app.include_router(keys.router, prefix="/api", tags=["keys"])  # API 密钥相关路由


@app.get("/")
async def root():
    """根路径，返回 API 基本信息"""
    return {"message": "QuotaWatch API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """健康检查端点，用于监控服务状态"""
    return {"status": "healthy"}
