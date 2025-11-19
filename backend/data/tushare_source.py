"""
Tushare数据源
获取中国股票市场数据
"""
import tushare as ts
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from .base import DataSource
from ..database import StockDatabase


class TushareDataSource(DataSource):
    """Tushare数据源类"""
    
    def __init__(self, config: dict = None):
        """
        初始化Tushare数据源
        
        Args:
            config: 配置字典，应包含token字段
        """
        super().__init__()
        self.config = config or {}
        self.source_name = 'tushare'
        
        # 设置tushare token
        token = self.config.get('token', '')
        if not token:
            raise ValueError("Tushare token is required. Please set it in config.yaml")
        
        ts.set_token(token)
        self.pro = ts.pro_api()
        self.db = StockDatabase()
        
        # 注册数据源
        self.db.register_data_source(
            source_name=self.source_name,
            source_type='tushare',
            config=self.config
        )
        
    def validate_symbol(self, symbol: str) -> bool:
        """
        验证股票代码是否有效
        
        Args:
            symbol: 股票代码 (如 '000001.SZ')
            
        Returns:
            是否有效
        """
        try:
            # 尝试获取少量数据来验证股票代码是否有效
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
            
            df = self.pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
            return not df.empty
        except Exception:
            return False
    
    def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str = None,
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        获取历史数据 - 支持智能缓存
        
        Args:
            symbol: 股票代码 (如 '000001.SZ')
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            interval: 时间间隔 (目前只支持1d)
            
        Returns:
            历史数据DataFrame
        """
        import time
        start_time = time.time()
        
        # 转换日期格式为YYYYMMDD
        start_date_str = start_date.replace('-', '') if isinstance(start_date, str) else start_date.strftime('%Y%m%d')
        end_date_str = end_date.replace('-', '') if end_date and isinstance(end_date, str) else (end_date.strftime('%Y%m%d') if end_date else datetime.now().strftime('%Y%m%d'))
        
        # 生成缓存键
        cache_key = f"{self.source_name}:daily:{symbol}:{start_date_str}:{end_date_str}"
        
        # 从数据库获取已存在的数据（只查询一次）
        db_data = self.db.get_daily_data(symbol, start_date_str, end_date_str, self.source_name)
        
        # 首先检查缓存是否有效
        if self.db.is_cache_valid(cache_key) and not db_data.empty:
            print(f"从缓存获取数据: {symbol} ({len(db_data)} 条记录)")
            return self._format_dataframe(db_data)
        
        # 检查数据完整性
        need_fetch = True
        if not db_data.empty:
            # 检查数据覆盖范围
            db_start = db_data.index.min().strftime('%Y%m%d')
            db_end = db_data.index.max().strftime('%Y%m%d')
            
            if db_start <= start_date_str and db_end >= end_date_str:
                # 数据完整，检查是否需要更新
                latest_date = self.db.get_latest_date(symbol, self.source_name)
                if latest_date and latest_date >= (datetime.now() - timedelta(days=1)).strftime('%Y%m%d'):
                    need_fetch = False
        
        if need_fetch:
            # 从API获取数据
            try:
                print(f"从API获取数据: {symbol} ({start_date_str} - {end_date_str})")
                
                df = self.pro.daily(
                    ts_code=symbol,
                    start_date=start_date_str,
                    end_date=end_date_str
                )
                
                if df.empty:
                    # 记录API调用
                    duration_ms = int((time.time() - start_time) * 1000)
                    self.db.log_api_call(
                        source_name=self.source_name,
                        endpoint='daily',
                        ts_code=symbol,
                        success=False,
                        error_message="No data returned",
                        duration_ms=duration_ms
                    )
                    
                    if not db_data.empty:
                        return self._format_dataframe(db_data)
                    raise ValueError(f"No data found for symbol {symbol}")
                
                # 保存到数据库
                self._save_to_database(symbol, df)
                
                # 设置缓存元数据
                self.db.set_cache_metadata(
                    cache_key=cache_key,
                    ts_code=symbol,
                    source_name=self.source_name,
                    data_type='daily',
                    start_date=start_date_str,
                    end_date=end_date_str,
                    record_count=len(df),
                    expiry_hours=6  # 6小时后过期
                )
                
                # 记录成功的API调用
                duration_ms = int((time.time() - start_time) * 1000)
                self.db.log_api_call(
                    source_name=self.source_name,
                    endpoint='daily',
                    ts_code=symbol,
                    success=True,
                    response_size=len(df),
                    duration_ms=duration_ms
                )
                
                # 格式化返回数据
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
                df.set_index('trade_date', inplace=True)
                df.sort_index(inplace=True)
                
                return self._format_dataframe(df)
                
            except Exception as e:
                # 记录失败的API调用
                duration_ms = int((time.time() - start_time) * 1000)
                self.db.log_api_call(
                    source_name=self.source_name,
                    endpoint='daily',
                    ts_code=symbol,
                    success=False,
                    error_message=str(e),
                    duration_ms=duration_ms
                )
                
                # 如果API失败，返回数据库中的数据（如果有的话）
                if not db_data.empty:
                    print(f"API失败，使用缓存数据: {symbol}")
                    return self._format_dataframe(db_data)
                raise ValueError(f"Failed to fetch data for {symbol}: {str(e)}")
        else:
            # 使用数据库中的完整数据
            print(f"使用数据库完整数据: {symbol} ({len(db_data)} 条记录)")
            return self._format_dataframe(db_data)
    
    def get_latest_price(self, symbol: str) -> float:
        """
        获取最新价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            最新价格
        """
        try:
            # 获取最近的日线数据
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=5)).strftime('%Y%m%d')
            
            df = self.pro.daily(
                ts_code=symbol,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                raise ValueError(f"No recent data found for {symbol}")
            
            return float(df.iloc[0]['close'])
            
        except Exception as e:
            raise ValueError(f"Failed to get latest price for {symbol}: {str(e)}")
    
    def get_symbols(self) -> List[str]:
        """
        获取所有可用的股票代码
        
        Returns:
            股票代码列表
        """
        try:
            # 获取股票基本信息
            df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
            return df['ts_code'].tolist()
            
        except Exception as e:
            print(f"Failed to fetch symbols: {e}")
            return []
    
    def search_symbols(self, query: str) -> List[str]:
        """
        搜索股票代码
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的股票代码列表
        """
        try:
            # 获取股票基本信息
            df = self.pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name')
            
            # 搜索匹配的股票
            mask = (
                df['ts_code'].str.contains(query, case=False, na=False) |
                df['symbol'].str.contains(query, case=False, na=False) |
                df['name'].str.contains(query, case=False, na=False)
            )
            
            return df[mask]['ts_code'].tolist()[:50]  # 限制返回数量
            
        except Exception as e:
            print(f"Failed to search symbols: {e}")
            return []
    
    def _format_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        格式化DataFrame为统一格式
        
        Args:
            df: 原始DataFrame
            
        Returns:
            格式化后的DataFrame
        """
        # 确保包含必要的列
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        
        # 重命名列
        column_mapping = {
            'vol': 'volume',
            'amount': 'amount'
        }
        
        df = df.rename(columns=column_mapping)
        
        # 确保所有必要列存在
        for col in required_columns:
            if col not in df.columns:
                if col == 'volume':
                    df[col] = 0
                else:
                    df[col] = df['close'] if 'close' in df.columns else 0
        
        # 只返回需要的列
        return df[required_columns + ['amount'] if 'amount' in df.columns else required_columns]
    
    def _save_to_database(self, symbol: str, df: pd.DataFrame):
        """
        保存数据到数据库
        
        Args:
            symbol: 股票代码
            df: 数据DataFrame
        """
        try:
            # 准备数据
            data_df = df.copy()
            data_df['ts_code'] = symbol
            
            # 重命名列以匹配数据库结构
            column_mapping = {
                'vol': 'volume'
            }
            data_df = data_df.rename(columns=column_mapping)
            
            # 确保volume列存在
            if 'volume' not in data_df.columns:
                data_df['volume'] = 0
            
            # 选择需要的列
            columns = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'volume']
            if 'amount' in data_df.columns:
                columns.append('amount')
            
            data_df = data_df[columns]
            
            # 使用新的数据库方法保存数据
            self.db.insert_daily_data(data_df, self.source_name)
            print(f"保存数据到数据库: {symbol} ({len(data_df)} 条记录)")
                
        except Exception as e:
            print(f"Warning: Failed to save data to database: {e}")
    
    def update_stock_list(self):
        """更新股票列表"""
        try:
            print("正在更新股票列表...")
            # 获取股票基本信息
            df = self.pro.stock_basic(
                exchange='', 
                list_status='L', 
                fields='ts_code,symbol,name,area,industry,market,list_date'
            )
            
            # 保存到数据库
            self.db.insert_stocks(df, self.source_name)
            print(f"更新股票信息完成: {len(df)} 支股票")
            
            # 记录API调用
            self.db.log_api_call(
                source_name=self.source_name,
                endpoint='stock_basic',
                success=True,
                response_size=len(df)
            )
            
        except Exception as e:
            print(f"Failed to update stock list: {e}")
            # 记录失败的API调用
            self.db.log_api_call(
                source_name=self.source_name,
                endpoint='stock_basic',
                success=False,
                error_message=str(e)
            )
    
    def get_popular_stocks(self) -> List[str]:
        """
        获取热门股票代码
        
        Returns:
            热门股票代码列表
        """
        # 首先尝试从数据库获取已存储的股票
        try:
            stocks_df = self.db.get_stocks(self.source_name)
            if not stocks_df.empty:
                return stocks_df['ts_code'].head(10).tolist()
        except:
            pass
        
        # 如果数据库没有数据，返回一些知名的股票代码
        popular_stocks = [
            '000001.SZ',  # 平安银行
            '000002.SZ',  # 万科A
            '600000.SH',  # 浦发银行
            '600036.SH',  # 招商银行
            '600519.SH',  # 贵州茅台
            '000858.SZ',  # 五粮液
            '002415.SZ',  # 海康威视
            '300750.SZ'   # 宁德时代
        ]
        
        # 验证这些股票代码是否有效（取前5个有效的）
        valid_stocks = []
        for stock in popular_stocks:
            try:
                if len(valid_stocks) >= 5:
                    break
                # 简单验证：检查股票代码格式是否正确
                if ('.' in stock and 
                    (stock.endswith('.SZ') or stock.endswith('.SH')) and 
                    len(stock.split('.')[0]) == 6):
                    valid_stocks.append(stock)
            except:
                continue
                
        return valid_stocks
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        api_stats = self.db.get_api_call_stats(self.source_name, 24)
        
        # 获取数据源信息
        source_info = self.db.get_data_source_info(self.source_name)
        
        # 获取股票数量
        stocks_df = self.db.get_stocks(self.source_name)
        stock_count = len(stocks_df) if not stocks_df.empty else 0
        
        return {
            'source_name': self.source_name,
            'source_type': 'tushare',
            'stock_count': stock_count,
            'api_calls_24h': api_stats.get('total_calls', 0),
            'successful_calls_24h': api_stats.get('successful_calls', 0),
            'avg_response_time_ms': api_stats.get('avg_duration', 0),
            'last_api_call': api_stats.get('last_call_time'),
            'last_update': source_info.iloc[0]['last_update'] if not source_info.empty else None
        }
    
    def cleanup_cache(self, days: int = 7):
        """
        清理缓存
        
        Args:
            days: 保留天数
        """
        print(f"清理 {days} 天前的缓存数据...")
        self.db.clean_expired_cache()
        print("缓存清理完成")