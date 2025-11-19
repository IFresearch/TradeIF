"""
数据缓存管理器
负责统一管理多数据源的缓存策略
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from ..database import StockDatabase


class DataCacheManager:
    """数据缓存管理器"""
    
    def __init__(self):
        """初始化缓存管理器"""
        self.db = StockDatabase()
        self.executor = ThreadPoolExecutor(max_workers=3)
        # 保留已注册的数据源实例，便于在预热/批量更新时调用
        self.registered_sources: Dict[str, Any] = {}
    
    def register_data_source(self, source_name: str, source_type: str, 
                           data_source_instance: Any, config: Dict[str, Any] = None):
        """
        注册数据源
        
        Args:
            source_name: 数据源名称
            source_type: 数据源类型
            data_source_instance: 数据源实例
            config: 配置信息
        """
        # 保存元信息到数据库
        self.db.register_data_source(source_name, source_type, config)
        # 保存实例引用，后续可以用来实际拉取或更新数据
        if data_source_instance is not None:
            self.registered_sources[source_name] = data_source_instance
        print(f"数据源已注册: {source_name} ({source_type})")
    
    def get_cached_data(self, symbol: str, start_date: str, end_date: str, 
                       source_name: str = 'tushare') -> Optional[pd.DataFrame]:
        """
        获取缓存的数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            source_name: 数据源名称
            
        Returns:
            缓存的数据或None
        """
        cache_key = f"{source_name}:daily:{symbol}:{start_date}:{end_date}"
        
        # 优先使用缓存元信息判断
        if self.db.is_cache_valid(cache_key):
            data = self.db.get_daily_data(symbol, start_date, end_date, source_name)
            if not data.empty:
                print(f"缓存命中: {symbol} ({len(data)} 条记录)")
                return data

        # 如果元信息不可用，也尝试从数据库中读取已有数据（降级返回）
        data = self.db.get_daily_data(symbol, start_date, end_date, source_name)
        if not data.empty:
            print(f"数据库存在历史数据（缓存元信息缺失或过期）: {symbol} ({len(data)} 条记录)")
            return data

        return None
    
    def set_cache_data(self, symbol: str, data: pd.DataFrame, source_name: str,
                      start_date: str, end_date: str, expiry_hours: int = 6):
        """
        设置缓存数据
        
        Args:
            symbol: 股票代码
            data: 数据
            source_name: 数据源名称
            start_date: 开始日期
            end_date: 结束日期
            expiry_hours: 过期小时数
        """
        # 保存数据到数据库（转换为适配数据库的结构）
        data_copy = data.copy()

        # 如果索引为 DatetimeIndex，则生成 trade_date 列
        if isinstance(data_copy.index, pd.DatetimeIndex):
            data_copy['trade_date'] = data_copy.index.strftime('%Y%m%d')
        elif 'trade_date' not in data_copy.columns:
            # 尝试保留已有的日期列或索引
            data_copy['trade_date'] = pd.to_datetime(data_copy.get('trade_date', pd.Series())).dt.strftime('%Y%m%d')

        data_copy['ts_code'] = symbol

        # 将列名按数据库表结构规范化
        # 保证至少有 open, high, low, close, volume, trade_date, ts_code
        # 其余列将被忽略
        expected_cols = ['ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'volume']
        cols_present = [c for c in expected_cols if c in data_copy.columns]
        data_to_insert = data_copy[cols_present].copy()

        # 对于缺失的数值列，用0或close填充，避免插入失败
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in data_to_insert.columns:
                if col == 'volume':
                    data_to_insert[col] = 0
                else:
                    data_to_insert[col] = data_copy.get('close', 0)

        # 最后写入数据库
        self.db.insert_daily_data(data_to_insert, source_name)
        
        # 设置缓存元数据
        cache_key = f"{source_name}:daily:{symbol}:{start_date}:{end_date}"
        self.db.set_cache_metadata(
            cache_key=cache_key,
            ts_code=symbol,
            source_name=source_name,
            data_type='daily',
            start_date=start_date,
            end_date=end_date,
            record_count=len(data),
            expiry_hours=expiry_hours
        )
        
        print(f"数据已缓存: {symbol} ({len(data)} 条记录)")
    
    def batch_update_stocks(self, source_names: List[str] = None):
        """
        批量更新股票列表
        
        Args:
            source_names: 要更新的数据源名称列表，如果为None则更新所有
        """
        if source_names is None:
            source_info = self.db.get_data_source_info()
            source_names = source_info['source_name'].tolist()

        print(f"批量更新股票列表: {source_names}")

        for source_name in source_names:
            try:
                instance = self.registered_sources.get(source_name)
                if instance and hasattr(instance, 'update_stock_list'):
                    print(f"调用 {source_name}.update_stock_list() 更新股票列表")
                    instance.update_stock_list()
                else:
                    print(f"跳过 {source_name}，未注册实例或不支持 update_stock_list")
            except Exception as e:
                print(f"更新 {source_name} 股票列表失败: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        stats = {}
        
        try:
            # 获取所有数据源信息
            sources = self.db.get_data_source_info()
            
            if sources.empty:
                return stats
            
            for _, source in sources.iterrows():
                source_name = source['source_name']
                
                try:
                    # 获取API调用统计
                    api_stats = self.db.get_api_call_stats(source_name, 24)
                    
                    # 使用COUNT查询代替加载所有数据（性能优化）
                    stock_count = self._get_stock_count_fast(source_name)
                    
                    stats[source_name] = {
                        'source_type': source['source_type'],
                        'stock_count': stock_count,
                        'api_calls_24h': api_stats.get('total_calls', 0),
                        'successful_calls_24h': api_stats.get('successful_calls', 0),
                        'avg_response_time_ms': api_stats.get('avg_duration', 0),
                        'last_api_call': api_stats.get('last_call_time'),
                        'last_update': source['last_update'],
                        'is_active': bool(source['is_active'])
                    }
                except Exception as e:
                    print(f"获取 {source_name} 统计信息失败: {e}")
                    stats[source_name] = {
                        'source_type': source.get('source_type', 'unknown'),
                        'error': str(e)
                    }
        except Exception as e:
            print(f"获取缓存统计信息失败: {e}")
            return {'error': str(e)}
        
        return stats
    
    def _get_stock_count_fast(self, source_name: str) -> int:
        """
        快速获取股票数量（使用COUNT查询）
        
        Args:
            source_name: 数据源名称
            
        Returns:
            股票数量
        """
        import sqlite3
        try:
            conn = sqlite3.connect(self.db.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM stocks WHERE source_name = ?",
                (source_name,)
            )
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            print(f"快速获取股票数量失败: {e}")
            return 0
    
    def cleanup_old_data(self, days: int = 30):
        """
        清理旧数据
        
        Args:
            days: 保留天数
        """
        print(f"开始清理 {days} 天前的数据...")
        
        # 清理过期缓存
        self.db.clean_expired_cache()
        
        print("数据清理完成")
    
    def warm_up_cache(self, symbols: List[str], days: int = 365, 
                     source_name: str = 'tushare'):
        """
        预热缓存 - 预先加载常用股票的历史数据
        
        Args:
            symbols: 股票代码列表
            days: 历史数据天数
            source_name: 数据源名称
        """
        print(f"开始预热缓存: {len(symbols)} 只股票, {days} 天数据, 数据源={source_name}")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        instance = self.registered_sources.get(source_name)
        if instance is None:
            print(f"未找到已注册的数据源实例: {source_name}，跳过预热")
            return

        for symbol in symbols:
            try:
                # 检查是否已有足够的数据
                cached_data = self.get_cached_data(
                    symbol,
                    start_date.strftime('%Y%m%d'),
                    end_date.strftime('%Y%m%d'),
                    source_name
                )

                if cached_data is not None and len(cached_data) >= days * 0.7:
                    print(f"跳过 {symbol}，已存在足够缓存 ({len(cached_data)} 条)")
                    continue

                print(f"预热缓存: {symbol} -> 从数据源拉取 {start_date.strftime('%Y%m%d')} - {end_date.strftime('%Y%m%d')}")
                # 从数据源拉取数据并写入数据库/缓存
                try:
                    df = instance.get_historical_data(symbol, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                    if df is None or df.empty:
                        print(f"数据源返回空: {symbol}")
                        continue

                    # 将数据写入缓存/数据库
                    self.set_cache_data(symbol, df, source_name, start_date.strftime('%Y%m%d'), end_date.strftime('%Y%m%d'))
                except Exception as e:
                    print(f"从数据源拉取或写入缓存失败 {symbol}: {e}")

            except Exception as e:
                print(f"预热缓存失败 {symbol}: {e}")

        print("缓存预热完成")
    
    def get_data_quality_report(self, symbol: str, source_name: str = 'tushare') -> Dict[str, Any]:
        """
        生成数据质量报告
        
        Args:
            symbol: 股票代码
            source_name: 数据源名称
            
        Returns:
            数据质量报告
        """
        # 获取该股票的所有数据
        data = self.db.get_daily_data(symbol, source_name=source_name)
        
        if data.empty:
            return {
                'symbol': symbol,
                'source_name': source_name,
                'status': 'no_data',
                'message': '无数据'
            }
        
        # 计算数据质量指标
        total_records = len(data)
        date_range = (data.index.max() - data.index.min()).days
        expected_records = date_range * 5 // 7  # 大约工作日数量
        completeness = total_records / expected_records if expected_records > 0 else 0
        
        # 检查数据完整性
        missing_dates = []
        if total_records > 0:
            full_range = pd.date_range(data.index.min(), data.index.max(), freq='B')
            missing_dates = full_range.difference(data.index).tolist()
        
        # 检查异常值
        anomalies = []
        if total_records > 0:
            # 检查价格异常（涨跌幅超过20%）
            price_changes = data['close'].pct_change()
            extreme_changes = price_changes[abs(price_changes) > 0.2]
            if len(extreme_changes) > 0:
                anomalies.append(f"发现 {len(extreme_changes)} 个极端价格变动")
            
            # 检查零交易量
            zero_volume = data[data['volume'] == 0]
            if len(zero_volume) > 0:
                anomalies.append(f"发现 {len(zero_volume)} 个零交易量记录")
        
        return {
            'symbol': symbol,
            'source_name': source_name,
            'status': 'ok' if completeness > 0.8 and len(anomalies) == 0 else 'warning',
            'total_records': total_records,
            'date_range_days': date_range,
            'completeness': round(completeness, 3),
            'missing_dates_count': len(missing_dates),
            'anomalies': anomalies,
            'first_date': data.index.min().strftime('%Y-%m-%d') if total_records > 0 else None,
            'last_date': data.index.max().strftime('%Y-%m-%d') if total_records > 0 else None
        }
    
    def __del__(self):
        """析构函数"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)