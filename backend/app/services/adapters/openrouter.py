"""
OpenRouter 平台适配器
实现 OpenRouter API 的余额查询功能
OpenRouter 提供直接的余额查询 API，返回精确的余额值
"""
import httpx
from typing import Optional, Dict, Any
from .base import BalanceAdapter, BalanceFetchResult


class OpenRouterAdapter(BalanceAdapter):
    """
    OpenRouter 平台适配器
    通过 OpenRouter API 获取账户余额
    API 文档: https://openrouter.ai/docs
    """
    
    async def fetch_balance(self) -> BalanceFetchResult:
        """
        从 OpenRouter API 获取余额
        OpenRouter 提供精确的余额查询，因此 is_estimate=False
        
        :return: 余额查询结果（精确值）
        :raises httpx.HTTPStatusError: 如果 API 请求失败
        """
        async with httpx.AsyncClient() as client:
            # 调用 OpenRouter 余额查询 API
            response = await client.get(
                "https://openrouter.ai/api/v1/credits",
                headers={
                    "Authorization": f"Bearer {self.api_key}",  # 使用 Bearer token 认证
                    "Content-Type": "application/json",
                },
                timeout=30.0,  # 30 秒超时
            )
            response.raise_for_status()  # 如果状态码不是 2xx，抛出异常
            data = response.json()
            # 从响应中提取余额（OpenRouter 返回 credits 字段）
            balance = float(data.get("credits", 0))
            # 返回精确余额（非估算值）
            return BalanceFetchResult(balance=balance, is_estimate=False)
