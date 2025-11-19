"""
数据源基类定义
定义了统一的数据接口，方便扩展新的数据源
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Union
from datetime import datetime
import pandas as pd


class DataSource(ABC):
    """数据源抽象基类"""
    
    def __init__(self, config: Dict = None):
        """
        初始化数据源
        
        Args:
            config: 配置信息
        """
        self.config = config or {}
        self.name = self.__class__.__name__
        
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """
        获取支持的交易对列表
        
        Returns:
            交易对列表
        """
        pass
        
    @abstractmethod
    def get_historical_data(
        self, 
        symbol: str, 
        start_date: Union[str, datetime], 
        end_date: Union[str, datetime] = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            symbol: 交易对代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 时间间隔 (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
            
        Returns:
            包含OHLCV数据的DataFrame
        """
        pass
        
    @abstractmethod
    def get_latest_price(self, symbol: str) -> float:
        """
        获取最新价格
        
        Args:
            symbol: 交易对代码
            
        Returns:
            最新价格
        """
        pass
        
    def validate_symbol(self, symbol: str) -> bool:
        """
        验证交易对是否有效
        
        Args:
            symbol: 交易对代码
            
        Returns:
            是否有效
        """
        return symbol in self.get_symbols()
        
    def format_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        统一数据格式
        
        Args:
            data: 原始数据
            
        Returns:
            格式化后的数据
        """
        # 确保包含必要的列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # 统一列名
        column_mapping = {
            'Open': 'open', 'High': 'high', 'Low': 'low', 
            'Close': 'close', 'Volume': 'volume',
            'OPEN': 'open', 'HIGH': 'high', 'LOW': 'low',
            'CLOSE': 'close', 'VOLUME': 'volume'
        }
        
        data = data.rename(columns=column_mapping)
        
        # 检查必要列是否存在
        for col in required_columns:
            if col not in data.columns:
                raise ValueError(f"Missing required column: {col}")
                
        # 确保数据类型正确
        for col in required_columns:
            data[col] = pd.to_numeric(data[col], errors='coerce')
            
        # 移除包含NaN的行
        data = data.dropna()
        
        # 确保索引是时间戳
        if not isinstance(data.index, pd.DatetimeIndex):
            if 'datetime' in data.columns:
                data.index = pd.to_datetime(data['datetime'])
                data = data.drop('datetime', axis=1)
            elif 'timestamp' in data.columns:
                data.index = pd.to_datetime(data['timestamp'])
                data = data.drop('timestamp', axis=1)
                
        return data[required_columns]