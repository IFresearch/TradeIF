"""
策略基类
"""
from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, List, Any


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str = None, **kwargs):
        """
        初始化策略
        
        Args:
            name: 策略名称
            **kwargs: 其他参数
        """
        self.name = name or self.__class__.__name__
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
            
        Returns:
            包含信号的DataFrame
        """
        pass
        
    @abstractmethod
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            data: 价格数据
            initial_capital: 初始资金
            
        Returns:
            回测结果字典
        """
        pass
    
    def _calculate_metrics(self, portfolio_values: List[Dict], trades: List[Dict], 
                          initial_capital: float, final_value: float) -> Dict[str, float]:
        """
        计算策略绩效指标（默认实现）
        
        Args:
            portfolio_values: 组合价值序列
            trades: 交易记录
            initial_capital: 初始资金
            final_value: 最终价值
            
        Returns:
            绩效指标字典
        """
        if not portfolio_values:
            return self._get_empty_metrics()
        
        # 基本收益指标
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        # 计算年化收益 (假设交易天数)
        trading_days = len(portfolio_values)
        if trading_days > 0:
            annualized_return = ((final_value / initial_capital) ** (252 / trading_days) - 1) * 100
        else:
            annualized_return = 0
        
        # 计算收益序列用于风险指标
        values = [pv.get('portfolio_value', pv.get('value', initial_capital)) for pv in portfolio_values]
        returns = pd.Series(values).pct_change().dropna()
        
        # 波动率 (年化)
        volatility = returns.std() * (252 ** 0.5) * 100 if len(returns) > 1 else 0
        
        # 夏普比率 (假设无风险收益率3%)
        risk_free_rate = 3.0
        excess_return = annualized_return - risk_free_rate
        sharpe_ratio = excess_return / volatility if volatility > 0 else 0
        
        # 最大回撤
        import numpy as np
        peak = np.maximum.accumulate(values)
        drawdown = (np.array(values) - peak) / peak * 100
        max_drawdown = abs(drawdown.min()) if len(drawdown) > 0 else 0
        
        # 交易指标
        if trades:
            # 分离买卖交易计算盈亏
            buy_trades = [t for t in trades if t.get('action') == '买入']
            sell_trades = [t for t in trades if t.get('action') == '卖出']
            
            # 计算每笔完整交易的盈亏
            trade_returns = []
            for sell_trade in sell_trades:
                sell_date = sell_trade.get('date')
                sell_price = sell_trade.get('price', 0)
                
                # 找到最近的买入交易
                corresponding_buy = None
                for buy_trade in reversed(buy_trades):
                    if buy_trade.get('date', '') < sell_date:
                        corresponding_buy = buy_trade
                        break
                
                if corresponding_buy:
                    buy_price = corresponding_buy.get('price', 0)
                    if buy_price > 0:
                        trade_return = (sell_price - buy_price) / buy_price
                        trade_returns.append(trade_return)
            
            # 胜率计算
            winning_trades = [r for r in trade_returns if r > 0]
            win_rate = len(winning_trades) / len(trade_returns) * 100 if trade_returns else 0
            
            total_trades = len(sell_trades)
        else:
            win_rate = 0
            total_trades = 0
        
        return {
            'total_return': round(total_return, 2),
            'annualized_return': round(annualized_return, 2),
            'volatility': round(volatility, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown, 2),
            'total_trades': total_trades,
            'win_rate': round(win_rate, 1),
            'final_value': round(final_value, 2)
        }
    
    def _get_empty_metrics(self) -> Dict[str, float]:
        """返回空的指标字典"""
        return {
            'total_return': 0.0,
            'annualized_return': 0.0,
            'volatility': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'total_trades': 0,
            'win_rate': 0.0,
            'final_value': 0.0
        }