"""
简化的移动平均线交叉策略
"""
import pandas as pd
import numpy as np
from typing import Dict, List
from .base import BaseStrategy


class MovingAverageCrossStrategy(BaseStrategy):
    """移动平均线交叉策略
    
    当短期移动平均线向上穿越长期移动平均线时买入
    当短期移动平均线向下穿越长期移动平均线时卖出
    """
    
    def __init__(self, short_window: int = 20, long_window: int = 50):
        """
        初始化策略
        
        Args:
            short_window: 短期移动平均线周期
            long_window: 长期移动平均线周期
        """
        super().__init__()
        self.short_window = short_window
        self.long_window = long_window
        self.name = f"MA交叉策略({short_window},{long_window})"
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 股票价格数据，包含close列
            
        Returns:
            包含信号的DataFrame
        """
        df = data.copy()
        
        # 计算移动平均线
        df['ma_short'] = df['close'].rolling(window=self.short_window).mean()
        df['ma_long'] = df['close'].rolling(window=self.long_window).mean()
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['trade_signal'] = 0  # 新增：实际交易信号（只在穿越时触发）
        
        # 计算MA穿越信号
        # 金叉：短期MA从下方穿越到上方
        df['ma_short_prev'] = df['ma_short'].shift(1)
        df['ma_long_prev'] = df['ma_long'].shift(1)
        
        # 金叉条件：前一天短期MA<=长期MA，今天短期MA>长期MA
        golden_cross = (df['ma_short_prev'] <= df['ma_long_prev']) & (df['ma_short'] > df['ma_long'])
        # 死叉条件：前一天短期MA>=长期MA，今天短期MA<长期MA  
        death_cross = (df['ma_short_prev'] >= df['ma_long_prev']) & (df['ma_short'] < df['ma_long'])
        
        # 设置交易信号（只在穿越时触发）
        df.loc[golden_cross, 'trade_signal'] = 1  # 买入信号
        df.loc[death_cross, 'trade_signal'] = -1  # 卖出信号
        
        # 计算持仓状态（基于累积信号）
        current_position = 0
        positions = []
        
        for i in range(len(df)):
            if df.iloc[i]['trade_signal'] == 1:  # 买入信号
                current_position = 1
            elif df.iloc[i]['trade_signal'] == -1:  # 卖出信号
                current_position = 0
            
            positions.append(current_position)
            
        df['position'] = positions
        df['signal'] = df['trade_signal']  # 保持兼容性
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict:
        """
        执行回测
        
        Args:
            data: 价格数据
            initial_capital: 初始资金
            
        Returns:
            回测结果字典
        """
        df = self.generate_signals(data)
        
        # 只填充关键列的NaN,不删除数据行
        df['position'] = df['position'].fillna(0)
        df['signal'] = df['signal'].fillna(0)
        
        if df.empty:
            return self._empty_results(initial_capital)
        
        # 计算收益
        df['returns'] = df['close'].pct_change().fillna(0)
        df['strategy_returns'] = df['position'] * df['returns']
        
        # 计算累计收益和净值
        df['cumulative_returns'] = (1 + df['strategy_returns']).cumprod()
        df['portfolio_value'] = initial_capital * df['cumulative_returns']
        
        # 生成交易记录
        trades = self._generate_trades(df)
        
        # 计算性能指标
        metrics = self._calculate_metrics(df, initial_capital)
        
        return {
            'data': df,
            'trades': trades,
            'metrics': metrics,
            'equity_curve': [
                {
                    'date': idx.strftime('%Y-%m-%d') if hasattr(idx, 'strftime') else str(idx),
                    'value': float(row['portfolio_value']) if pd.notna(row['portfolio_value']) and np.isfinite(row['portfolio_value']) else float(initial_capital)
                }
                for idx, row in df[['portfolio_value']].iterrows()
            ]
        }
    
    def _generate_trades(self, df: pd.DataFrame) -> List[Dict]:
        """生成交易记录"""
        trades = []
        
        for i in range(len(df)):
            if df.iloc[i]['trade_signal'] == 1:  # 买入信号
                trades.append({
                    'date': df.index[i].strftime('%Y-%m-%d'),
                    'action': '买入',
                    'price': float(df.iloc[i]['close']),
                    'quantity': 100,  # 固定数量
                    'reason': 'MA金叉买入信号'
                })
            elif df.iloc[i]['trade_signal'] == -1:  # 卖出信号
                trades.append({
                    'date': df.index[i].strftime('%Y-%m-%d'),
                    'action': '卖出',
                    'price': float(df.iloc[i]['close']),
                    'quantity': 100,  # 固定数量
                    'reason': 'MA死叉卖出信号'
                })
        
        return trades
    
    def _calculate_metrics(self, df: pd.DataFrame, initial_capital: float) -> Dict:
        """计算性能指标"""
        if df.empty or 'strategy_returns' not in df.columns:
            return self._empty_metrics()
        
        strategy_returns = df['strategy_returns'].fillna(0)
        final_value = df['portfolio_value'].iloc[-1]
        
        # 确保final_value不是NaN
        if pd.isna(final_value):
            final_value = initial_capital
        
        # 基本指标
        total_return = (final_value / initial_capital - 1) * 100
        
        # 年化收益率
        days = len(df)
        years = days / 252.0  # 假设一年252个交易日
        annualized_return = ((final_value / initial_capital) ** (1/years) - 1) * 100 if years > 0 else 0
        
        # 夏普比率
        excess_returns = strategy_returns
        sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(252) if excess_returns.std() > 0 else 0
        
        # 确保sharpe_ratio不是NaN或无穷大
        if pd.isna(sharpe_ratio) or not np.isfinite(sharpe_ratio):
            sharpe_ratio = 0
        
        # 最大回撤
        portfolio_values = df['portfolio_value'].fillna(initial_capital)
        rolling_max = portfolio_values.expanding().max()
        drawdown = (portfolio_values - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()
        
        # 确保max_drawdown不是NaN
        if pd.isna(max_drawdown):
            max_drawdown = 0
        
        # 修正交易次数计算：应该计算实际交易信号的数量
        total_trades = len(df[df['trade_signal'] != 0])
        
        # 胜率计算：基于实际的买卖信号对
        # 简化胜率计算：这里暂时基于持仓期间的收益
        winning_trades = len([r for r in strategy_returns if r > 0])
        win_rate = (winning_trades / len(strategy_returns) * 100) if len(strategy_returns) > 0 else 0
        
        # 波动率
        volatility = strategy_returns.std() * np.sqrt(252) * 100
        
        # 确保volatility不是NaN
        if pd.isna(volatility):
            volatility = 0
        
        # 确保所有值都是有限的
        metrics = {
            'total_return': float(total_return) if np.isfinite(total_return) else 0,
            'annualized_return': float(annualized_return) if np.isfinite(annualized_return) else 0,
            'sharpe_ratio': float(sharpe_ratio) if np.isfinite(sharpe_ratio) else 0,
            'max_drawdown': float(max_drawdown) if np.isfinite(max_drawdown) else 0,
            'win_rate': float(win_rate) if np.isfinite(win_rate) else 0,
            'volatility': float(volatility) if np.isfinite(volatility) else 0,
            'total_trades': int(total_trades),
            'final_value': float(final_value) if np.isfinite(final_value) else float(initial_capital)
        }
        
        return metrics
    
    def _empty_results(self, initial_capital: float) -> Dict:
        """返回空结果"""
        return {
            'data': pd.DataFrame(),
            'trades': [],
            'metrics': self._empty_metrics(),
            'equity_curve': []
        }
    
    def _empty_metrics(self) -> Dict:
        """返回空指标"""
        return {
            'total_return': 0,
            'annualized_return': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'win_rate': 0,
            'volatility': 0,
            'total_trades': 0,
            'final_value': 0
        }