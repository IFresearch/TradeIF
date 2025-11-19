"""
自定义策略执行器
支持用户自定义交易逻辑，包含丰富的技术指标库和talib支持
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import traceback
import ast
import textwrap
from .base import BaseStrategy

# 尝试导入talib，如果没有安装则使用内置实现
try:
    import talib
    TALIB_AVAILABLE = True
    print("TA-Lib库已加载")
except ImportError:
    TALIB_AVAILABLE = False
    print("TA-Lib库未安装，使用内置技术指标实现")


class CustomStrategy(BaseStrategy):
    """
    自定义策略类
    允许用户输入自定义的交易逻辑代码
    """
    
    def __init__(self, 
                 custom_code: str = "",
                 initial_capital: float = 100000,
                 **kwargs):
        """
        初始化自定义策略
        
        Args:
            custom_code: 用户自定义的交易逻辑代码
            initial_capital: 初始资金
        """
        super().__init__(**kwargs)
        self.custom_code = custom_code
        self.initial_capital = initial_capital
        
        # 策略状态变量
        self.position = 0  # 当前持仓：0=空仓, 1=持仓
        self.entry_price = 0  # 买入价格
        self.entry_date = None  # 买入日期
        
        # 验证自定义代码
        self.validate_code()
        
    def validate_code(self):
        """验证用户代码的语法"""
        if not self.custom_code.strip():
            return
            
        try:
            # 检查语法
            ast.parse(self.custom_code)
        except SyntaxError as e:
            raise ValueError(f"自定义代码语法错误: {e}")
    
    def create_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        创建技术指标
        包含大量技术指标和自定义因子构建功能
        """
        df = data.copy()
        
        # =============================================================================
        # 基础移动平均线系列
        # =============================================================================
        # 简单移动平均线
        for period in [3, 5, 7, 10, 12, 15, 20, 25, 30, 50, 60, 100, 200]:
            df[f'ma{period}'] = df['close'].rolling(window=period).mean()
            
        # 指数移动平均线
        for period in [5, 10, 12, 20, 26, 50]:
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            
        # 加权移动平均线
        def weighted_ma(series, period):
            weights = np.arange(1, period + 1)
            return series.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=False)
        
        for period in [5, 10, 20]:
            df[f'wma{period}'] = weighted_ma(df['close'], period)
            
        # Hull移动平均线
        def hull_ma(series, period):
            wma1 = weighted_ma(series, period // 2) * 2
            wma2 = weighted_ma(series, period)
            raw_hma = wma1 - wma2
            return weighted_ma(raw_hma, int(np.sqrt(period)))
        
        df['hma9'] = hull_ma(df['close'], 9)
        df['hma21'] = hull_ma(df['close'], 21)
        
        # =============================================================================
        # 趋势指标
        # =============================================================================
        if TALIB_AVAILABLE:
            # 使用TA-Lib计算
            df['adx'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=14)
            df['adxr'] = talib.ADXR(df['high'], df['low'], df['close'], timeperiod=14)
            df['cci'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14)
            df['dx'] = talib.DX(df['high'], df['low'], df['close'], timeperiod=14)
            df['aroon_up'], df['aroon_down'] = talib.AROON(df['high'], df['low'], timeperiod=14)
            df['aroonosc'] = talib.AROONOSC(df['high'], df['low'], timeperiod=14)
            df['ppo'] = talib.PPO(df['close'], fastperiod=12, slowperiod=26, matype=0)
            df['roc'] = talib.ROC(df['close'], timeperiod=10)
            df['rocr'] = talib.ROCR(df['close'], timeperiod=10)
            df['trix'] = talib.TRIX(df['close'], timeperiod=30)
        else:
            # 自定义实现
            # ADX (平均趋向指数)
            df['tr'] = np.maximum(df['high'] - df['low'], 
                                np.maximum(abs(df['high'] - df['close'].shift(1)),
                                         abs(df['low'] - df['close'].shift(1))))
            df['atr14'] = df['tr'].rolling(14).mean()
            
            # CCI (商品通道指数)
            tp = (df['high'] + df['low'] + df['close']) / 3
            df['cci'] = (tp - tp.rolling(14).mean()) / (0.015 * tp.rolling(14).std())
            
            # ROC (变化率)
            df['roc'] = (df['close'] / df['close'].shift(10) - 1) * 100
            
        # =============================================================================
        # 动量指标
        # =============================================================================
        # RSI指标 (多周期)
        for period in [7, 14, 21]:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df[f'rsi{period}'] = 100 - (100 / (1 + rs))
        
        # Stochastic指标
        if TALIB_AVAILABLE:
            df['stoch_k'], df['stoch_d'] = talib.STOCH(df['high'], df['low'], df['close'])
            df['stochrsi_k'], df['stochrsi_d'] = talib.STOCHRSI(df['close'])
            df['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'], timeperiod=14)
            df['mfi'] = talib.MFI(df['high'], df['low'], df['close'], df['volume'], timeperiod=14)
        else:
            # Stochastic %K和%D
            low_min = df['low'].rolling(14).min()
            high_max = df['high'].rolling(14).max()
            df['stoch_k'] = 100 * (df['close'] - low_min) / (high_max - low_min)
            df['stoch_d'] = df['stoch_k'].rolling(3).mean()
            
            # Williams %R
            df['williams_r'] = -100 * (high_max - df['close']) / (high_max - low_min)
        
        # MACD指标族
        for fast, slow in [(5, 10), (12, 26), (8, 21)]:
            exp1 = df['close'].ewm(span=fast, adjust=False).mean()
            exp2 = df['close'].ewm(span=slow, adjust=False).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=9, adjust=False).mean()
            histogram = macd_line - signal_line
            
            df[f'macd_{fast}_{slow}'] = macd_line
            df[f'macd_signal_{fast}_{slow}'] = signal_line
            df[f'macd_hist_{fast}_{slow}'] = histogram
            
        # 传统MACD (保持向后兼容)
        df['macd'] = df['macd_12_26']
        df['macd_signal'] = df['macd_signal_12_26']
        df['macd_hist'] = df['macd_hist_12_26']
        
        # =============================================================================
        # 波动率指标
        # =============================================================================
        # 布林带 (多周期、多倍数)
        for period in [10, 20, 50]:
            for multiplier in [1.5, 2.0, 2.5]:
                bb_middle = df['close'].rolling(window=period).mean()
                bb_std = df['close'].rolling(window=period).std()
                df[f'bb{period}_upper_{int(multiplier*10)}'] = bb_middle + (bb_std * multiplier)
                df[f'bb{period}_middle'] = bb_middle
                df[f'bb{period}_lower_{int(multiplier*10)}'] = bb_middle - (bb_std * multiplier)
                df[f'bb{period}_width_{int(multiplier*10)}'] = (df[f'bb{period}_upper_{int(multiplier*10)}'] - df[f'bb{period}_lower_{int(multiplier*10)}']) / bb_middle
                df[f'bb{period}_percent_{int(multiplier*10)}'] = (df['close'] - df[f'bb{period}_lower_{int(multiplier*10)}']) / (df[f'bb{period}_upper_{int(multiplier*10)}'] - df[f'bb{period}_lower_{int(multiplier*10)}'])
        
        # 传统布林带 (保持向后兼容)
        df['bb_upper'] = df['bb20_upper_20']
        df['bb_middle'] = df['bb20_middle']
        df['bb_lower'] = df['bb20_lower_20']
        
        # ATR (真实波动幅度)
        df['atr'] = df['tr'].rolling(14).mean() if 'tr' in df.columns else self._calculate_atr(df, 14)
        for period in [7, 14, 21]:
            df[f'atr{period}'] = self._calculate_atr(df, period)
            
        # Donchian Channels
        for period in [10, 20, 55]:
            df[f'dc{period}_upper'] = df['high'].rolling(period).max()
            df[f'dc{period}_lower'] = df['low'].rolling(period).min()
            df[f'dc{period}_middle'] = (df[f'dc{period}_upper'] + df[f'dc{period}_lower']) / 2
            
        # Keltner Channels
        for period in [10, 20]:
            kc_middle = df['close'].ewm(span=period).mean()
            atr_col = f'atr{period}' if f'atr{period}' in df.columns else 'atr'
            kc_range = df[atr_col] * 2
            df[f'kc{period}_upper'] = kc_middle + kc_range
            df[f'kc{period}_middle'] = kc_middle
            df[f'kc{period}_lower'] = kc_middle - kc_range
            
        # =============================================================================
        # 成交量指标
        # =============================================================================
        # 成交量移动平均
        for period in [5, 10, 20, 50]:
            df[f'volume_ma{period}'] = df['volume'].rolling(window=period).mean()
            
        # 成交量比率
        df['volume_ratio'] = df['volume'] / df['volume_ma20']
        
        # 价量趋势指标 (PVT)
        df['pvt'] = (df['close'].pct_change() * df['volume']).cumsum()
        
        # 能量潮指标 (OBV)
        df['obv'] = (df['volume'] * np.sign(df['close'].diff())).cumsum()
        
        # 成交量加权平均价 (VWAP)
        df['vwap'] = (df['close'] * df['volume']).cumsum() / df['volume'].cumsum()
        
        # 资金流量指标
        if TALIB_AVAILABLE:
            df['ad'] = talib.AD(df['high'], df['low'], df['close'], df['volume'])
            df['adosc'] = talib.ADOSC(df['high'], df['low'], df['close'], df['volume'])
        else:
            # A/D Line
            mfm = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
            mfm = mfm.fillna(0)
            df['ad'] = (mfm * df['volume']).cumsum()
            
        # =============================================================================
        # 价格模式指标
        # =============================================================================
        # 支撑阻力位
        df['resistance'] = df['high'].rolling(20).max()
        df['support'] = df['low'].rolling(20).min()
        
        # 枢轴点
        df['pivot'] = (df['high'].shift(1) + df['low'].shift(1) + df['close'].shift(1)) / 3
        df['r1'] = 2 * df['pivot'] - df['low'].shift(1)
        df['s1'] = 2 * df['pivot'] - df['high'].shift(1)
        df['r2'] = df['pivot'] + (df['high'].shift(1) - df['low'].shift(1))
        df['s2'] = df['pivot'] - (df['high'].shift(1) - df['low'].shift(1))
        
        # =============================================================================
        # 自定义因子
        # =============================================================================
        
        # 价格强度因子
        df['price_strength'] = df['close'] / df['close'].rolling(20).mean()
        
        # 相对强弱因子
        df['relative_strength'] = df['close'].pct_change(20) / df['close'].pct_change(20).rolling(60).std()
        
        # 趋势强度因子
        df['trend_strength'] = (df['close'] - df['close'].rolling(50).mean()) / df['atr']
        
        # 动量因子
        df['momentum_factor'] = df['close'] / df['close'].shift(20) - 1
        
        # 反转因子
        df['reversal_factor'] = -df['close'].pct_change(5).rolling(20).mean()
        
        # 波动率因子
        df['volatility_factor'] = df['close'].pct_change().rolling(20).std()
        
        # 价量因子
        df['price_volume_factor'] = df['close'].pct_change() * df['volume_ratio']
        
        # 技术面综合评分
        df['tech_score'] = (
            (df['rsi14'] - 50) / 50 * 0.2 +  # RSI标准化
            (df['stoch_k'] - 50) / 50 * 0.2 +  # Stochastic标准化
            np.tanh(df['macd'] / df['atr']) * 0.3 +  # MACD标准化
            np.sign(df['close'] - df['ma20']) * 0.3  # 均线位置
        ).fillna(0)
        
        # =============================================================================
        # 高级组合因子
        # =============================================================================
        
        # 多周期强度因子
        short_strength = df['close'] / df['ma5'] - 1
        medium_strength = df['close'] / df['ma20'] - 1  
        long_strength = df['close'] / df['ma50'] - 1
        df['multi_period_strength'] = (short_strength * 0.5 + 
                                     medium_strength * 0.3 + 
                                     long_strength * 0.2)
        
        # 突破因子
        df['breakout_factor'] = np.where(
            df['close'] > df['resistance'].shift(1),
            (df['close'] - df['resistance'].shift(1)) / df['atr'],
            np.where(
                df['close'] < df['support'].shift(1),
                (df['close'] - df['support'].shift(1)) / df['atr'],
                0
            )
        )
        
        # 背离因子
        price_slope = df['close'].rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
        rsi_slope = df['rsi14'].rolling(10).apply(lambda x: np.polyfit(range(len(x)), x, 1)[0])
        df['divergence_factor'] = np.sign(price_slope) * np.sign(rsi_slope) * -1  # 负相关表示背离
        
        # 季节性因子（基于历史同期表现）
        df['day_of_year'] = df.index.dayofyear if hasattr(df.index, 'dayofyear') else 1
        df['seasonality_factor'] = np.sin(2 * np.pi * df['day_of_year'] / 365)
        
        # =============================================================================
        # 清理和填充缺失值
        # =============================================================================
        # 向前填充缺失值
        df = df.fillna(method='ffill').fillna(method='bfill').fillna(0)
        
        return df
        
    def _calculate_atr(self, data: pd.DataFrame, period: int) -> pd.Series:
        """计算ATR (平均真实波动范围)"""
        high_low = data['high'] - data['low']
        high_close_prev = abs(data['high'] - data['close'].shift(1))
        low_close_prev = abs(data['low'] - data['close'].shift(1))
        
        true_range = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
        return true_range.rolling(period).mean()
    
    def execute_custom_logic(self, data: pd.DataFrame, i: int) -> tuple:
        """
        执行用户自定义的交易逻辑
        
        Args:
            data: 包含所有技术指标的数据
            i: 当前行索引
            
        Returns:
            (signal, reason): signal为1买入, -1卖出, 0无操作; reason为交易理由
        """
        if not self.custom_code.strip():
            return 0, ""
        
        # 创建安全的执行环境
        current_row = data.iloc[i]
        prev_row = data.iloc[i-1] if i > 0 else current_row
        
        # 获取历史数据切片
        history_5 = data.iloc[max(0, i-4):i+1] if i >= 4 else data.iloc[:i+1]
        history_10 = data.iloc[max(0, i-9):i+1] if i >= 9 else data.iloc[:i+1]
        history_20 = data.iloc[max(0, i-19):i+1] if i >= 19 else data.iloc[:i+1]
        
        # 自定义因子构建函数
        def custom_ma(series, period):
            """自定义移动平均"""
            return series.rolling(period).mean()
        
        def custom_ema(series, period):
            """自定义指数移动平均"""
            return series.ewm(span=period, adjust=False).mean()
            
        def custom_std(series, period):
            """自定义标准差"""
            return series.rolling(period).std()
            
        def custom_corr(series1, series2, period):
            """自定义相关系数"""
            return series1.rolling(period).corr(series2)
            
        def custom_rank(series, period):
            """自定义排名（分位数）"""
            return series.rolling(period).rank(pct=True)
            
        def custom_zscore(series, period):
            """自定义Z-Score标准化"""
            mean = series.rolling(period).mean()
            std = series.rolling(period).std()
            return (series - mean) / std
            
        def custom_rsi(series, period=14):
            """自定义RSI计算"""
            delta = series.diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
            
        def custom_bollinger(series, period=20, std_dev=2):
            """自定义布林带"""
            ma = series.rolling(period).mean()
            std = series.rolling(period).std()
            return {
                'upper': ma + (std * std_dev),
                'middle': ma,
                'lower': ma - (std * std_dev),
                'width': (ma + std * std_dev - ma + std * std_dev) / ma,
                'percent': (series - (ma - std * std_dev)) / (2 * std * std_dev)
            }
            
        def custom_macd(series, fast=12, slow=26, signal=9):
            """自定义MACD"""
            exp1 = series.ewm(span=fast).mean()
            exp2 = series.ewm(span=slow).mean()
            macd_line = exp1 - exp2
            signal_line = macd_line.ewm(span=signal).mean()
            return {
                'macd': macd_line,
                'signal': signal_line,
                'histogram': macd_line - signal_line
            }
            
        def custom_stochastic(high, low, close, k_period=14, d_period=3):
            """自定义KDJ指标"""
            lowest_low = low.rolling(k_period).min()
            highest_high = high.rolling(k_period).max()
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(d_period).mean()
            j_percent = 3 * k_percent - 2 * d_percent
            return {
                'k': k_percent,
                'd': d_percent,
                'j': j_percent
            }
            
        def support_resistance(high, low, period=20):
            """动态支撑阻力位"""
            return {
                'resistance': high.rolling(period).max(),
                'support': low.rolling(period).min()
            }
            
        def fibonacci_retracements(high_price, low_price):
            """斐波那契回撤位"""
            diff = high_price - low_price
            return {
                'level_236': high_price - diff * 0.236,
                'level_382': high_price - diff * 0.382,
                'level_500': high_price - diff * 0.500,
                'level_618': high_price - diff * 0.618,
                'level_786': high_price - diff * 0.786
            }
            
        def volume_profile(price, volume, bins=20):
            """成交量分布"""
            try:
                hist, edges = np.histogram(price, bins=bins, weights=volume)
                return {
                    'volume_dist': hist,
                    'price_levels': edges,
                    'poc': edges[np.argmax(hist)]  # Point of Control
                }
            except:
                return {'volume_dist': [], 'price_levels': [], 'poc': 0}
            
        def wave_analysis(series, period=20):
            """波浪分析"""
            peaks = []
            troughs = []
            for j in range(1, len(series) - 1):
                if series.iloc[j] > series.iloc[j-1] and series.iloc[j] > series.iloc[j+1]:
                    peaks.append((j, series.iloc[j]))
                elif series.iloc[j] < series.iloc[j-1] and series.iloc[j] < series.iloc[j+1]:
                    troughs.append((j, series.iloc[j]))
            return {'peaks': peaks, 'troughs': troughs}
            
        # 提供给用户代码的变量和函数
        local_vars = {
            # =============================================================================
            # 基础数据
            # =============================================================================
            'current': current_row,
            'prev': prev_row,
            'data': data,
            'index': i,
            'history_5': history_5,
            'history_10': history_10,
            'history_20': history_20,
            
            # =============================================================================
            # 策略状态
            # =============================================================================
            'position': self.position,
            'entry_price': self.entry_price,
            'entry_date': self.entry_date,
            
            # =============================================================================
            # 基础函数
            # =============================================================================
            'len': len,
            'max': max,
            'min': min,
            'abs': abs,
            'round': round,
            'sum': sum,
            'mean': np.mean,
            'std': np.std,
            'sqrt': np.sqrt,
            'log': np.log,
            'exp': np.exp,
            'sin': np.sin,
            'cos': np.cos,
            'tan': np.tan,
            
            # =============================================================================
            # 数学和数据处理库
            # =============================================================================
            'np': np,
            'pd': pd,
            
            # =============================================================================
            # 自定义因子构建函数
            # =============================================================================
            'custom_ma': custom_ma,
            'custom_ema': custom_ema,
            'custom_std': custom_std,
            'custom_corr': custom_corr,
            'custom_rank': custom_rank,
            'custom_zscore': custom_zscore,
            'custom_rsi': custom_rsi,
            'custom_bollinger': custom_bollinger,
            'custom_macd': custom_macd,
            'custom_stochastic': custom_stochastic,
            'support_resistance': support_resistance,
            'fibonacci_retracements': fibonacci_retracements,
            'volume_profile': volume_profile,
            'wave_analysis': wave_analysis,
            
            # =============================================================================
            # 条件检查函数
            # =============================================================================
            'is_golden_cross': lambda fast_ma, slow_ma, prev_fast, prev_slow: (
                fast_ma > slow_ma and prev_fast <= prev_slow
            ),
            'is_death_cross': lambda fast_ma, slow_ma, prev_fast, prev_slow: (
                fast_ma < slow_ma and prev_fast >= prev_slow
            ),
            'is_oversold': lambda rsi, threshold=30: rsi < threshold,
            'is_overbought': lambda rsi, threshold=70: rsi > threshold,
            'is_breakout': lambda price, resistance, volume_ratio=1.5: (
                price > resistance and volume_ratio > 1.5
            ),
            'is_breakdown': lambda price, support, volume_ratio=1.5: (
                price < support and volume_ratio > 1.5
            ),
            'is_divergence': lambda price_trend, indicator_trend: (
                np.sign(price_trend) != np.sign(indicator_trend)
            ),
            
            # =============================================================================
            # TA-Lib函数 (如果可用)
            # =============================================================================
            'TALIB_AVAILABLE': TALIB_AVAILABLE,
        }
        
        # 如果TA-Lib可用，添加常用函数
        if TALIB_AVAILABLE:
            import talib as ta
            local_vars.update({
                'ta': ta,
                # 趋势指标
                'ta_sma': ta.SMA,
                'ta_ema': ta.EMA,
                'ta_wma': ta.WMA,
                'ta_dema': ta.DEMA,
                'ta_tema': ta.TEMA,
                'ta_trima': ta.TRIMA,
                'ta_kama': ta.KAMA,
                'ta_mama': ta.MAMA,
                'ta_t3': ta.T3,
                # 动量指标  
                'ta_rsi': ta.RSI,
                'ta_stoch': ta.STOCH,
                'ta_stochf': ta.STOCHF,
                'ta_stochrsi': ta.STOCHRSI,
                'ta_willr': ta.WILLR,
                'ta_cci': ta.CCI,
                'ta_cmo': ta.CMO,
                'ta_roc': ta.ROC,
                'ta_rocp': ta.ROCP,
                'ta_rocr': ta.ROCR,
                'ta_mfi': ta.MFI,
                # 波动率指标
                'ta_atr': ta.ATR,
                'ta_natr': ta.NATR,
                'ta_trange': ta.TRANGE,
                # 成交量指标
                'ta_ad': ta.AD,
                'ta_adosc': ta.ADOSC,
                'ta_obv': ta.OBV,
            })
            
        # 输出变量（用户需要设置）
        local_vars.update({
            'signal': 0,
            'reason': "",
        })
        
        # 添加必要的内置函数到全局命名空间
        safe_builtins = {
            '__builtins__': {
                'Exception': Exception,
                'ValueError': ValueError,
                'TypeError': TypeError,
                'hasattr': hasattr,
                'float': float,
                'int': int,
                'str': str,
                'bool': bool,
                'list': list,
                'dict': dict,
                'tuple': tuple,
                'set': set,
                'range': range,
                'enumerate': enumerate,
                'zip': zip,
                'isinstance': isinstance,
                'print': print,
            }
        }
        
        try:
            # 执行用户代码
            exec(self.custom_code, safe_builtins, local_vars)
            
            # 获取结果
            signal = local_vars.get('signal', 0)
            reason = local_vars.get('reason', "")
            
            # 验证信号值
            if signal not in [-1, 0, 1]:
                signal = 0
                reason = f"无效信号值: {signal}"
            
            return signal, reason
            
        except Exception as e:
            # 代码执行出错
            error_msg = f"代码执行错误: {str(e)}"
            print(error_msg)
            return 0, error_msg
    
    def generate_signals(self, data: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        print("开始执行自定义策略...")
        
        # 创建技术指标
        df = self.create_indicators(data)
        
        # 初始化信号列
        df['signal'] = 0
        df['position'] = 0
        df['reason'] = ''
        
        # 重置策略状态
        self.position = 0
        self.entry_price = 0
        self.entry_date = None
        
        signal_count = 0
        
        # 从足够的行数开始（确保技术指标有效，但不要太晚）
        # 使用max(20, len(df)//20)确保至少从第20行开始，但对长数据不会开始太晚
        start_index = max(20, min(50, len(df) // 10))
        
        for i in range(start_index, len(df)):
            try:
                # 执行用户自定义逻辑
                signal, reason = self.execute_custom_logic(df, i)
                
                current_price = df.iloc[i]['close']
                current_date = df.index[i]
                
                # 处理买入信号
                if signal == 1 and self.position == 0:
                    df.iloc[i, df.columns.get_loc('signal')] = 1
                    df.iloc[i, df.columns.get_loc('reason')] = reason
                    self.position = 1
                    self.entry_price = current_price
                    self.entry_date = current_date
                    signal_count += 1
                    
                # 处理卖出信号
                elif signal == -1 and self.position == 1:
                    df.iloc[i, df.columns.get_loc('signal')] = -1
                    df.iloc[i, df.columns.get_loc('reason')] = reason
                    self.position = 0
                    self.entry_price = 0
                    self.entry_date = None
                    signal_count += 1
                
                # 记录持仓状态
                df.iloc[i, df.columns.get_loc('position')] = self.position
                
            except Exception as e:
                print(f"第{i}行执行错误: {e}")
                continue
        
        print(f"自定义策略生成 {signal_count} 个交易信号")
        return df
    
    def backtest(self, data: pd.DataFrame, initial_capital: float = None) -> Dict[str, Any]:
        """执行回测"""
        if initial_capital is None:
            initial_capital = self.initial_capital
            
        print(f"开始自定义策略回测，初始资金: {initial_capital:,.0f}")
        
        try:
            # 生成信号
            df = self.generate_signals(data)
        except Exception as e:
            print(f"信号生成失败: {e}")
            return self._get_empty_result()
        
        # 执行回测交易逻辑
        capital = initial_capital
        shares = 0
        trades = []
        portfolio_values = []
        
        for i, (date, row) in enumerate(df.iterrows()):
            price = row['close']
            signal = int(row['signal'])  # 确保是Python整数
            reason = row['reason']
            
            # 计算当前组合价值
            current_value = capital + shares * price
            portfolio_values.append({
                'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                'portfolio_value': current_value,
                'capital': capital,
                'shares': shares,
                'price': price
            })
            
            # 执行交易
            if signal == 1 and capital > price:  # 买入
                # 计算可买数量（考虑手续费）
                shares_to_buy = int(capital / (price * 1.001))  # 包含手续费的每股成本
                if shares_to_buy > 0:
                    cost = shares_to_buy * price * 1.001  # 包含手续费
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
            
            elif signal == -1 and shares > 0:  # 卖出
                revenue = shares * price * 0.999  # 扣除手续费
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
        
        # 计算最终价值和指标
        final_value = capital + shares * df.iloc[-1]['close']
        metrics = self._calculate_metrics(portfolio_values, trades, initial_capital, final_value)
        
        print(f"自定义策略回测完成: {len(trades)} 笔交易, 最终价值: {final_value:,.0f}")
        
        return {
            'trades': trades,
            'portfolio_values': portfolio_values,
            'equity_curve': portfolio_values,
            'metrics': metrics,
            'signals_data': df[['signal', 'position', 'reason']].to_dict('records'),
            'strategy_params': {
                'custom_code': self.custom_code,
                'initial_capital': initial_capital
            }
        }
    
    def _get_empty_result(self) -> Dict[str, Any]:
        """返回空的回测结果"""
        return {
            'trades': [],
            'portfolio_values': [],
            'equity_curve': [],
            'metrics': self._get_empty_metrics(),
            'signals_data': [],
            'strategy_params': {
                'custom_code': self.custom_code,
                'initial_capital': self.initial_capital
            }
        }