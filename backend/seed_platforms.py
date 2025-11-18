#!/usr/bin/env python3
"""
平台数据初始化脚本
在数据库初始化时自动运行，将支持的平台提供商数据插入数据库
"""
from sqlmodel import Session, select
from app.core.database import engine
from app.models import PlatformProvider

# 预定义的平台提供商列表
# 添加新平台时，需要：
# 1. 在此列表中添加平台信息
# 2. 在 adapter_factory.py 中注册对应的适配器类
PLATFORMS = [
    {
        "name": "OpenRouter",  # 平台显示名称
        "slug": "openrouter",  # 平台标识符（URL 友好）
        "adapter_identifier": "openrouter",  # 适配器标识符（用于查找适配器类）
    },
    {
        "name": "OpenAI",
        "slug": "openai",
        "adapter_identifier": "openai",
    },
]


def seed_platforms():
    """
    种子平台提供商数据
    检查每个平台是否已存在，如果不存在则创建
    如果已存在则跳过（幂等操作）
    """
    with Session(engine) as session:
        for platform_data in PLATFORMS:
            # 检查平台是否已存在（通过 slug 判断）
            existing = session.exec(
                select(PlatformProvider).where(PlatformProvider.slug == platform_data["slug"])
            ).first()
            
            if not existing:
                # 创建新平台记录
                platform = PlatformProvider(**platform_data)
                session.add(platform)
                print(f"已添加平台: {platform_data['name']}")
            else:
                print(f"平台已存在: {platform_data['name']}")
        
        session.commit()
        print("平台数据初始化完成！")


if __name__ == "__main__":
    # 直接运行此脚本时执行初始化
    seed_platforms()
