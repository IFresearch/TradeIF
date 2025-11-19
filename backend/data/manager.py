"""
数据管理器 - 支持智能缓存
"""
import yaml
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import pandas as pd

from .base import DataSource
from .tushare_source import TushareDataSource
from .cache_manager import DataCacheManager


class DataManager:
    """数据管理器 - 统一的数据访问接口，支持智能缓存"""
    
    def __init__(self, config_path: str = None):
        """
        初始化数据管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.sources: Dict[str, DataSource] = {}
        self.config = {}
        self.cache_manager = DataCacheManager()
        
        if config_path:
            self.load_config(config_path)
        
        self._init_sources()
    
    def load_config(self, config_path: str):
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Could not load config file {config_path}: {e}")
            self.config = {}
    
    def _init_sources(self):
        """初始化数据源"""
        data_sources_config = self.config.get('data_sources', {})
        
        # 初始化Tushare数据源
        if data_sources_config.get('tushare', {}).get('enabled', True):
            tushare_config = data_sources_config.get('tushare', {})
            try:
                tushare_source = TushareDataSource(tushare_config)
                self.sources['tushare'] = tushare_source
                
                # 注册到缓存管理器
                self.cache_manager.register_data_source(
                    source_name='tushare',
                    source_type='tushare',
                    data_source_instance=tushare_source,
                    config=tushare_config
                )
                
                print("Tushare数据源初始化成功")
                
            except Exception as e:
                print(f"Warning: Could not initialize Tushare data source: {e}")
    
    def get_historical_data(
        self, 
        symbol: str, 
        start_date: Union[str, datetime], 
        end_date: Union[str, datetime] = None,
        interval: str = "1d",
        source: str = None,
        use_cache: bool = True
    ) -> pd.DataFrame:
        """
        获取历史数据 - 支持缓存优先策略
        
        Args:
            symbol: 交易对代码
            start_date: 开始日期
            end_date: 结束日期
            interval: 时间间隔
            source: 指定数据源，如果为None则自动选择
            use_cache: 是否使用缓存
            
        Returns:
            历史数据DataFrame
        """
        # 标准化日期格式
        if isinstance(start_date, datetime):
            start_date_str = start_date.strftime('%Y%m%d')
        else:
            start_date_str = start_date.replace('-', '')
            
        if end_date:
            if isinstance(end_date, datetime):
                end_date_str = end_date.strftime('%Y%m%d')
            else:
                end_date_str = end_date.replace('-', '')
        else:
            end_date_str = datetime.now().strftime('%Y%m%d')
        
        # 选择数据源
        source_name = source or 'tushare'
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = self.cache_manager.get_cached_data(
                symbol, start_date_str, end_date_str, source_name
            )
            if cached_data is not None:
                return cached_data
        
        # 从数据源获取数据
        if source_name in self.sources:
            try:
                data = self.sources[source_name].get_historical_data(
                    symbol, start_date, end_date, interval
                )
                
                # 缓存数据
                if use_cache and not data.empty:
                    self.cache_manager.set_cache_data(
                        symbol, data, source_name, start_date_str, end_date_str
                    )
                
                return data
                
            except Exception as e:
                print(f"从数据源 {source_name} 获取数据失败: {e}")
                raise
        
        # 自动选择数据源
        for source_name, data_source in self.sources.items():
            try:
                if data_source.validate_symbol(symbol):
                    data = data_source.get_historical_data(symbol, start_date, end_date, interval)
                    
                    # 缓存数据
                    if use_cache and not data.empty:
                        self.cache_manager.set_cache_data(
                            symbol, data, source_name, start_date_str, end_date_str
                        )
                    
                    return data
            except:
                continue
        
        raise ValueError(f"Symbol {symbol} not found in any available data source")
    
    def get_latest_price(self, symbol: str, source: str = None) -> float:
        """
        获取最新价格
        
        Args:
            symbol: 交易对代码
            source: 指定数据源
            
        Returns:
            最新价格
        """
        if source and source in self.sources:
            return self.sources[source].get_latest_price(symbol)
        
        # 自动选择数据源
        for source_name, data_source in self.sources.items():
            try:
                if data_source.validate_symbol(symbol):
                    return data_source.get_latest_price(symbol)
            except:
                continue
        
        raise ValueError(f"Symbol {symbol} not found in any available data source")
    
    def list_sources(self) -> List[str]:
        """
        列出所有可用的数据源
        
        Returns:
            数据源名称列表
        """
        return list(self.sources.keys())
    
    def get_source(self, name: str) -> Optional[DataSource]:
        """
        获取数据源
        
        Args:
            name: 数据源名称
            
        Returns:
            数据源实例
        """
        return self.sources.get(name)
    
    def search_symbols(self, query: str, source: str = None) -> List[str]:
        """
        搜索股票代码
        
        Args:
            query: 搜索关键词
            source: 指定数据源
            
        Returns:
            匹配的股票代码列表
        """
        results = []
        
        sources_to_search = [source] if source else self.sources.keys()
        
        for source_name in sources_to_search:
            if source_name in self.sources:
                try:
                    matches = self.sources[source_name].search_symbols(query)
                    results.extend(matches)
                except:
                    continue
        
        return results[:50]  # 限制返回数量
    
    def update_all_stock_lists(self):
        """更新所有数据源的股票列表"""
        print("开始更新所有数据源的股票列表...")
        
        for source_name, data_source in self.sources.items():
            try:
                if hasattr(data_source, 'update_stock_list'):
                    print(f"更新 {source_name} 股票列表...")
                    data_source.update_stock_list()
                    print(f"{source_name} 股票列表更新完成")
            except Exception as e:
                print(f"更新 {source_name} 股票列表失败: {e}")
        
        print("股票列表更新完成")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息
        """
        return self.cache_manager.get_cache_statistics()
    
    def warm_up_cache(self, symbols: List[str] = None, days: int = 365):
        """
        预热缓存
        
        Args:
            symbols: 股票代码列表，如果为None则使用热门股票
            days: 预热天数
        """
        if symbols is None:
            # 使用热门股票
            for source_name, data_source in self.sources.items():
                if hasattr(data_source, 'get_popular_stocks'):
                    try:
                        symbols = data_source.get_popular_stocks()
                        break
                    except:
                        continue
            
            if symbols is None:
                symbols = ['000001.SZ', '000002.SZ', '600000.SH', '600036.SH', '600519.SH']
        
        print(f"开始预热缓存: {len(symbols)} 只股票")
        self.cache_manager.warm_up_cache(symbols, days)
    
    def cleanup_cache(self, days: int = 30):
        """
        清理缓存
        
        Args:
            days: 保留天数
        """
        print(f"开始清理 {days} 天前的缓存数据...")
        self.cache_manager.cleanup_old_data(days)
    
    def get_data_quality_report(self, symbols: List[str] = None) -> List[Dict[str, Any]]:
        """
        生成数据质量报告
        
        Args:
            symbols: 要检查的股票代码列表
            
        Returns:
            数据质量报告列表
        """
        if symbols is None:
            # 使用一些示例股票
            symbols = ['000001.SZ', '000002.SZ', '600000.SH']
        
        reports = []
        for symbol in symbols:
            try:
                report = self.cache_manager.get_data_quality_report(symbol)
                reports.append(report)
            except Exception as e:
                reports.append({
                    'symbol': symbol,
                    'status': 'error',
                    'message': str(e)
                })
        
        return reports
    
    def get_source_status(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有数据源状态
        
        Returns:
            数据源状态信息
        """
        status = {}
        
        for source_name, data_source in self.sources.items():
            try:
                if hasattr(data_source, 'get_cache_stats'):
                    stats = data_source.get_cache_stats()
                else:
                    stats = {'source_name': source_name, 'status': 'active'}
                
                status[source_name] = stats
                
            except Exception as e:
                status[source_name] = {
                    'source_name': source_name,
                    'status': 'error',
                    'error_message': str(e)
                }
        
        return status