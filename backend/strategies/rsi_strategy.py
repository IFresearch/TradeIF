"""
RSI超买超卖交易策略
基于相对强弱指数(RSI)的经典交易策略
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from .base import BaseStrategy


class RSIStrategy(BaseStrategy):
    """
    RSI超买超卖策略
    
    策略逻辑:
    1. 当RSI < 30时，认为超卖，产生买入信号
    2. 当RSI > 70时，认为超买，产生卖出信号
    3. 支持自定义RSI参数和超买超卖阈值
    
    参数说明:
    - rsi_period: RSI计算周期，默认14
    - oversold_threshold: 超卖阈值，默认30
    - overbought_threshold: 超买阈值，默认70
    - stop_loss: 止损百分比，默认0.05 (5%)
    - take_profit: 止盈百分比，默认0.10 (10%)
    """
    
    def __init__(self, 
                 rsi_period: int = 14,
                 oversold_threshold: float = 30,
                 overbought_threshold: float = 70,
                 stop_loss: float = 0.05,
                 take_profit: float = 0.10,
                 **kwargs):
        """
        初始化RSI策略
        
        Args:
            rsi_period: RSI计算周期
            oversold_threshold: 超卖阈值
            overbought_threshold: 超买阈值
            stop_loss: 止损百分比
            take_profit: 止盈百分比
        """
        super().__init__(**kwargs)
        self.rsi_period = rsi_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        
        self.position = 0  # 当前持仓: 0=空仓, 1=持有
        self.entry_price = 0  # 进入价格
        self.entry_date = None  # 进入日期
        
        print(f"RSI策略初始化: RSI周期={rsi_period}, 超卖阈值={oversold_threshold}, 超买阈值={overbought_threshold}")
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            prices: 价格序列
            period: 计算周期
            
        Returns:
            RSI值序列
        """
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            data: 包含OHLCV数据的DataFrame
            
        Returns:
            包含信号的DataFrame
        """
        df = data.copy()
        
        # 计算RSI
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_period)
        
        # 初始化信号
        df['signal'] = 0
        df['position'] = 0
        df['reason'] = ''
        
        # 生成交易信号
        for i in range(self.rsi_period, len(df)):
            current_rsi = df.iloc[i]['rsi']
            current_price = df.iloc[i]['close']
            current_date = df.index[i]
            
            # 检查止损和止盈
            if self.position == 1:
                price_change = (current_price - self.entry_price) / self.entry_price
                
                # 止损
                if price_change <= -self.stop_loss:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('reason')] = f'止损卖出(亏损{price_change:.2%})'
                    self.position = 0
                    continue
                
                # 止盈
                elif price_change >= self.take_profit:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('reason')] = f'止盈卖出(盈利{price_change:.2%})'
                    self.position = 0
                    continue
            
            # RSI信号
            if current_rsi < self.oversold_threshold and self.position == 0:
                # 超卖买入信号
                df.iloc[i, df.columns.get_loc('signal')] = 1
                df.iloc[i, df.columns.get_loc('reason')] = f'RSI超卖买入(RSI={current_rsi:.1f})'
                self.position = 1
                self.entry_price = current_price
                self.entry_date = current_date
                
            elif current_rsi > self.overbought_threshold and self.position == 1:
                # 超买卖出信号
                price_change = (current_price - self.entry_price) / self.entry_price
                df.iloc[i, df.columns.get_loc('signal')] = -1
                df.iloc[i, df.columns.get_loc('reason')] = f'RSI超买卖出(RSI={current_rsi:.1f}, 收益{price_change:.2%})'
                self.position = 0
            
            # 记录当前持仓状态
            df.iloc[i, df.columns.get_loc('position')] = self.position
        
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = 100000) -> Dict[str, Any]:
        """
        执行回测
        
        Args:
            data: 历史数据
            initial_capital: 初始资金
            
        Returns:
            回测结果
        """
        print(f"开始RSI策略回测，初始资金: ¥{initial_capital:,.0f}")
        
        # 重置状态
        self.position = 0
        self.entry_price = 0
        self.entry_date = None
        
        # 生成信号
        df = self.generate_signals(data)
        
        # 回测逻辑
        capital = initial_capital
        shares = 0
        trades = []
        portfolio_values = []
        
        for i, (date, row) in enumerate(df.iterrows()):
            price = row['close']
            signal = row['signal']
            reason = row['reason']
            
            current_value = capital + shares * price
            portfolio_values.append({
                'date': date,
                'portfolio_value': current_value,
                'capital': capital,
                'shares': shares,
                'price': price,
                'rsi': row['rsi'] if 'rsi' in row else None
            })
            
            if signal == 1 and capital > 0:  # 买入信号
                shares_to_buy = int(capital / price)
                if shares_to_buy > 0:
                    cost = shares_to_buy * price
                    shares += shares_to_buy
                    capital -= cost
                    
                    trades.append({
                        'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                        'action': '买入',
                        'price': price,
                        'quantity': shares_to_buy,
                        'amount': cost,
                        'reason': reason,
                        'portfolio_value': capital + shares * price
                    })
                    
            elif signal == -1 and shares > 0:  # 卖出信号
                revenue = shares * price
                capital += revenue
                
                trades.append({
                    'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'action': '卖出',
                    'price': price,
                    'quantity': shares,
                    'amount': revenue,
                    'reason': reason,
                    'portfolio_value': capital
                })
                
                shares = 0
        
        # 计算最终价值
        final_value = capital + shares * df.iloc[-1]['close']
        
        # 计算指标
        metrics = self._calculate_metrics(
            portfolio_values, trades, initial_capital, final_value
        )
        
        print(f"RSI策略回测完成: {len(trades)} 笔交易, 最终价值: ¥{final_value:,.0f}")
        
        return {
            'trades': trades,
            'portfolio_values': portfolio_values,
            'metrics': metrics,
            'signals_data': df,
            'strategy_params': {
                'rsi_period': self.rsi_period,
                'oversold_threshold': self.oversold_threshold,
                'overbought_threshold': self.overbought_threshold,
                'stop_loss': self.stop_loss,
                'take_profit': self.take_profit
            }
        }
    
    def _calculate_metrics(self, portfolio_values: List[Dict], trades: List[Dict], 
                          initial_capital: float, final_value: float) -> Dict[str, float]:
        """计算策略指标"""
        if not portfolio_values:
            return self._get_empty_metrics()
        
        # 转换为DataFrame便于计算
        pv_df = pd.DataFrame(portfolio_values)
        
        # 基本指标
        total_return = (final_value - initial_capital) / initial_capital * 100
        
        # 计算日收益率
        pv_df['daily_return'] = pv_df['portfolio_value'].pct_change()
        daily_returns = pv_df['daily_return'].dropna()
        
        # 年化收益率 (假设252个交易日)
        trading_days = len(pv_df)
        if trading_days > 0:
            annualized_return = (final_value / initial_capital) ** (252 / trading_days) - 1
            annualized_return *= 100
        else:
            annualized_return = 0
        
        # 波动率
        volatility = daily_returns.std() * np.sqrt(252) * 100 if len(daily_returns) > 1 else 0
        
        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        if volatility > 0:
            sharpe_ratio = (annualized_return / 100 - risk_free_rate) / (volatility / 100)
        else:
            sharpe_ratio = 0
        
        # 最大回撤
        peak = pv_df['portfolio_value'].expanding().max()
        drawdown = (pv_df['portfolio_value'] - peak) / peak
        max_drawdown = drawdown.min() * 100
        
        # 交易统计
        total_trades = len(trades)
        if total_trades > 0:
            # 计算盈利交易
            buy_trades = [t for t in trades if t['action'] == '买入']
            sell_trades = [t for t in trades if t['action'] == '卖出']
            
            profitable_trades = 0
            if len(buy_trades) > 0 and len(sell_trades) > 0:
                for i in range(min(len(buy_trades), len(sell_trades))):
                    if sell_trades[i]['amount'] > buy_trades[i]['amount']:
                        profitable_trades += 1
            
            win_rate = (profitable_trades / (total_trades // 2)) * 100 if total_trades >= 2 else 0
        else:
            win_rate = 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'final_value': final_value
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