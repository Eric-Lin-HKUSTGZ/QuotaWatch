"""
适配器工厂模块
根据平台标识符创建对应的余额适配器实例
使用工厂模式实现适配器的统一创建和管理
"""
from typing import Dict, Any, Optional
from app.services.adapters.base import BalanceAdapter
from app.services.adapters.openrouter import OpenRouterAdapter
from app.services.adapters.openai import OpenAIUsageAdapter


class AdapterFactory:
    """
    适配器工厂类
    维护适配器标识符到适配器类的映射关系
    """
    
    # 适配器注册表：将平台标识符映射到对应的适配器类
    _adapters: Dict[str, type[BalanceAdapter]] = {
        "openrouter": OpenRouterAdapter,  # OpenRouter 平台适配器
        "openai": OpenAIUsageAdapter,  # OpenAI 平台适配器
    }
    
    @classmethod
    def create_adapter(
        cls,
        adapter_identifier: str,
        api_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BalanceAdapter:
        """
        根据适配器标识符创建适配器实例
        
        :param adapter_identifier: 适配器标识符（如 "openrouter", "openai"）
        :param api_key: API 密钥（明文）
        :param metadata: 可选的元数据（如 OpenAI 的 total_grant）
        :return: 适配器实例
        :raises ValueError: 如果适配器标识符未知
        """
        # 从注册表中获取对应的适配器类
        adapter_class = cls._adapters.get(adapter_identifier)
        if adapter_class is None:
            raise ValueError(f"未知的适配器标识符: {adapter_identifier}")
        # 创建并返回适配器实例
        return adapter_class(api_key=api_key, metadata=metadata or {})
