"""
策略模块初始化文件
"""

from .base import BaseStrategy
from .ma_cross_strategy import MovingAverageCrossStrategy

__all__ = [
    'BaseStrategy', 
    'MovingAverageCrossStrategy'
]