#!/usr/bin/env python3
"""
Arq 工作进程启动脚本
用于启动后台任务处理进程，执行余额检查和通知发送任务

使用方法：
    python run_worker.py

或者在 Docker 容器中：
    docker-compose exec backend python run_worker.py
"""
import asyncio
from arq import run_worker
from app.worker import WorkerSettings

if __name__ == "__main__":
    # 运行 Arq 工作进程
    # WorkerSettings 定义了 Redis 连接和可执行的任务函数
    asyncio.run(run_worker(WorkerSettings))
