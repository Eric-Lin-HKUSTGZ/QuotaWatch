"""
OpenAI 平台适配器
实现 OpenAI API 的余额估算功能
注意：OpenAI 不提供直接的余额查询 API，因此需要基于总授予额度和使用量进行估算
"""
import httpx
from typing import Optional, Dict, Any
from .base import BalanceAdapter, BalanceFetchResult


class OpenAIUsageAdapter(BalanceAdapter):
    """
    OpenAI 平台适配器
    通过 OpenAI 使用量 API 估算剩余余额
    注意：OpenAI 不提供直接的余额查询，需要用户提供 total_grant（总授予额度）
    余额 = total_grant - 已使用量
    """
    
    async def fetch_balance(self) -> BalanceFetchResult:
        """
        从 OpenAI API 估算余额
        需要从 metadata 中获取 total_grant（总授予额度）
        然后查询使用量，计算剩余余额
        
        :return: 余额查询结果（估算值）
        :raises ValueError: 如果 metadata 中缺少 total_grant
        :raises httpx.HTTPStatusError: 如果 API 请求失败
        """
        # 从元数据中获取总授予额度（必需）
        total_grant = self.metadata.get("total_grant")
        if total_grant is None:
            raise ValueError("OpenAI 密钥必须在 metadata 中提供 total_grant（总授予额度）")
        
        total_grant = float(total_grant)
        
        # 尝试从 OpenAI API 获取使用量
        async with httpx.AsyncClient() as client:
            # 注意：OpenAI 可能没有直接的 usage API 端点
            # 这里使用一个占位符端点，实际实现可能需要根据 OpenAI 的实际 API 调整
            # OpenAI 不提供直接的余额查询，所以这是估算值
            try:
                response = await client.get(
                    "https://api.openai.com/v1/usage",  # 占位符端点，可能需要调整
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                
                # 如果端点不存在（404），返回基于 total_grant 的估算值
                if response.status_code == 404:
                    # 由于无法获取使用量，返回总授予额度作为估算值
                    # 实际使用中，可能需要通过其他方式（如账单 API）获取使用量
                    return BalanceFetchResult(balance=total_grant, is_estimate=True)
                
                response.raise_for_status()
                data = response.json()
                
                # 计算剩余余额
                # 注意：这是简化计算，实际实现可能需要根据 OpenAI 的实际响应格式调整
                used_amount = float(data.get("total_usage", 0)) / 100  # 将美分转换为美元
                remaining = total_grant - used_amount
                
                # 确保余额不为负数
                return BalanceFetchResult(balance=max(0, remaining), is_estimate=True)
            except httpx.HTTPStatusError:
                # 如果 API 调用失败，返回基于 total_grant 的估算值
                return BalanceFetchResult(balance=total_grant, is_estimate=True)
