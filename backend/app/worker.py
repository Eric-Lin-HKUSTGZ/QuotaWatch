"""
Arq 后台任务工作进程
处理 API 密钥余额检查和通知发送的异步任务
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any
import httpx
from arq import create_pool
from arq.connections import RedisSettings
from sqlmodel import Session, select
from app.core.database import engine
from app.core.security import encryption_service
from app.models import ManagedApiKey, BalanceLog, NotificationRule, PlatformProvider
from app.services.adapter_factory import AdapterFactory

# Arq 的 Redis 配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_settings = RedisSettings.from_dsn(REDIS_URL)


async def check_single_key(ctx, key_id: int):
    """
    检查单个 API 密钥的余额
    这是一个 Arq 后台任务，会被调度器或手动触发执行
    
    流程：
    1. 从数据库获取 API 密钥记录
    2. 解密 API 密钥
    3. 使用适配器获取余额
    4. 更新数据库中的余额和检查时间
    5. 记录余额日志
    6. 如果余额低于阈值，触发通知任务
    
    :param ctx: Arq 任务上下文
    :param key_id: 要检查的 API 密钥 ID
    """
    with Session(engine) as session:
        # 从数据库获取 API 密钥记录
        api_key_record = session.exec(
            select(ManagedApiKey).where(ManagedApiKey.id == key_id)
        ).first()
        
        if not api_key_record:
            print(f"API 密钥 {key_id} 未找到")
            return
        
        # 获取平台信息
        platform = session.exec(
            select(PlatformProvider).where(PlatformProvider.id == api_key_record.platform_id)
        ).first()
        
        if not platform:
            print(f"平台 {api_key_record.platform_id} 未找到，密钥 ID: {key_id}")
            return
        
        try:
            # 解密 API 密钥
            decrypted_key = encryption_service.decrypt(api_key_record.api_key_encrypted)
            
            # 使用适配器工厂创建对应的适配器实例
            adapter = AdapterFactory.create_adapter(
                adapter_identifier=platform.adapter_identifier,
                api_key=decrypted_key,
                metadata=api_key_record.metadata
            )
            
            # 调用适配器获取余额
            result = await adapter.fetch_balance()
            
            # 更新 API 密钥记录中的余额和检查时间
            api_key_record.last_known_balance = result.balance
            api_key_record.last_checked = datetime.utcnow()
            session.add(api_key_record)
            
            # 创建余额日志记录
            balance_log = BalanceLog(
                key_id=key_id,
                balance=result.balance,
                timestamp=datetime.utcnow()
            )
            session.add(balance_log)
            
            session.commit()
            
            # 检查是否有通知规则，如果余额低于阈值则触发通知
            notification_rule = session.exec(
                select(NotificationRule).where(NotificationRule.key_id == key_id)
            ).first()
            
            if notification_rule and result.balance <= notification_rule.threshold_amount:
                # 将通知任务加入队列
                await ctx.enqueue_job(
                    "send_notification",
                    key_id=key_id,
                    balance=result.balance,
                    threshold=notification_rule.threshold_amount,
                    channel=notification_rule.notification_channel,
                    address=notification_rule.channel_address
                )
            
            print(f"成功检查密钥 {key_id}: 余额={result.balance}")
            
        except Exception as e:
            print(f"检查密钥 {key_id} 时出错: {e}")
            session.rollback()  # 回滚事务
            raise


async def send_notification(
    ctx,
    key_id: int,
    balance: float,
    threshold: float,
    channel: str,
    address: str
):
    """
    发送通知（当余额低于阈值时）
    支持两种通知渠道：邮件和 Webhook
    
    :param ctx: Arq 任务上下文
    :param key_id: API 密钥 ID
    :param balance: 当前余额
    :param threshold: 阈值金额
    :param channel: 通知渠道（"email" 或 "webhook"）
    :param address: 渠道地址（邮箱地址或 Webhook URL）
    """
    with Session(engine) as session:
        # 获取 API 密钥记录以获取密钥名称
        api_key_record = session.exec(
            select(ManagedApiKey).where(ManagedApiKey.id == key_id)
        ).first()
        
        if not api_key_record:
            print(f"API 密钥 {key_id} 未找到，无法发送通知")
            return
        
        # 构建通知消息
        message = f"""
        警报: API 密钥余额过低
        
        密钥名称: {api_key_record.name}
        当前余额: ${balance:.2f}
        阈值: ${threshold:.2f}
        
        请及时充值。
        """
        
        if channel == "email":
            # 邮件通知
            try:
                # 从环境变量获取 SMTP 配置
                smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
                smtp_port = int(os.getenv("SMTP_PORT", "587"))
                smtp_user = os.getenv("SMTP_USER", "")
                smtp_password = os.getenv("SMTP_PASSWORD", "")
                from_email = os.getenv("SMTP_FROM", smtp_user)
                
                # 构建邮件消息
                msg = MIMEMultipart()
                msg["From"] = from_email
                msg["To"] = address
                msg["Subject"] = "QuotaWatch: API 密钥余额过低"
                msg.attach(MIMEText(message, "plain"))
                
                # 发送邮件
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()  # 启用 TLS 加密
                    if smtp_user and smtp_password:
                        server.login(smtp_user, smtp_password)
                    server.send_message(msg)
                
                print(f"邮件通知已发送到 {address}，密钥 ID: {key_id}")
            except Exception as e:
                print(f"发送邮件通知时出错: {e}")
                raise
        
        elif channel == "webhook":
            # Webhook 通知
            try:
                async with httpx.AsyncClient() as client:
                    # 发送 POST 请求到 Webhook URL
                    response = await client.post(
                        address,
                        json={
                            "key_id": key_id,
                            "key_name": api_key_record.name,
                            "balance": balance,
                            "threshold": threshold,
                            "message": message,
                        },
                        timeout=30.0,
                    )
                    response.raise_for_status()  # 如果状态码不是 2xx，抛出异常
                    print(f"Webhook 通知已发送到 {address}，密钥 ID: {key_id}")
            except Exception as e:
                print(f"发送 Webhook 通知时出错: {e}")
                raise
        
        else:
            print(f"未知的通知渠道: {channel}")


class WorkerSettings:
    """
    Arq 工作进程配置类
    定义 Redis 连接设置和可执行的任务函数列表
    """
    redis_settings = redis_settings
    functions = [check_single_key, send_notification]  # 注册的任务函数


async def schedule_all_key_checks():
    """
    为所有 API 密钥安排余额检查任务
    此函数会被 APScheduler 定时调用（默认每 30 分钟）
    将所有密钥的检查任务加入 Redis 队列
    """
    with Session(engine) as session:
        # 获取所有 API 密钥
        all_keys = session.exec(select(ManagedApiKey)).all()
        
        # 创建 Redis 连接池
        redis_pool = await create_pool(redis_settings)
        
        # 为每个密钥创建检查任务
        for key in all_keys:
            await redis_pool.enqueue_job("check_single_key", key_id=key.id)
        
        await redis_pool.close()
        print(f"已为 {len(all_keys)} 个 API 密钥安排检查任务")
