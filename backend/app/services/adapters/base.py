"""
适配器基类模块
定义余额适配器的抽象接口和通用数据结构
所有平台适配器都必须继承此基类并实现 fetch_balance 方法
"""
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Optional, Dict, Any


class BalanceFetchResult(BaseModel):
    """
    余额查询结果模型
    所有适配器的 fetch_balance 方法都应返回此类型的结果
    """
    balance: float  # 余额值
    is_estimate: bool = False  # 是否为估算值（某些平台可能无法获取精确余额）


class BalanceAdapter(ABC):
    """
    余额适配器抽象基类
    定义统一的接口，所有平台适配器都必须实现 fetch_balance 方法
    
    适配器模式的优势：
    - 统一接口：不同平台使用相同的调用方式
    - 易于扩展：添加新平台只需实现新的适配器类
    - 解耦合：业务逻辑与具体平台 API 实现分离
    """
    
    def __init__(self, api_key: str, metadata: Optional[Dict[str, Any]] = None):
        """
        初始化适配器
        :param api_key: API 密钥（明文）
        :param metadata: 可选的元数据字典（如 OpenAI 的 total_grant）
        """
        self.api_key = api_key
        self.metadata = metadata or {}
    
    @abstractmethod
    async def fetch_balance(self) -> BalanceFetchResult:
        """
        获取当前余额（抽象方法，必须由子类实现）
        每个平台适配器需要实现自己的余额获取逻辑
        
        :return: 余额查询结果
        :raises Exception: 如果 API 调用失败或数据解析错误
        """
        pass
