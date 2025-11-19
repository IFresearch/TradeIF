"""
SQLite数据库操作模块
"""
import sqlite3
import pandas as pd
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import json


class StockDatabase:
    """股票数据库管理类 - 支持多数据源缓存"""
    
    def __init__(self, db_path: str = "data/stocks.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        # 创建data目录
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        self.db_path = db_path
        self._create_tables()
    
    def _create_tables(self):
        """创建数据表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 数据源配置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT UNIQUE NOT NULL,
                source_type TEXT NOT NULL,
                config_json TEXT,
                is_active BOOLEAN DEFAULT 1,
                last_update TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 股票基本信息表 (增加数据源字段)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stocks (
                ts_code TEXT NOT NULL,
                source_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                name TEXT NOT NULL,
                area TEXT,
                industry TEXT,
                market TEXT,
                list_date TEXT,
                last_update TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (ts_code, source_name),
                FOREIGN KEY (source_name) REFERENCES data_sources (source_name)
            )
        ''')
        
        # 股票日线数据表 (增加数据源字段)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_code TEXT NOT NULL,
                source_name TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL,
                amount REAL,
                adj_close REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(ts_code, source_name, trade_date),
                FOREIGN KEY (source_name) REFERENCES data_sources (source_name)
            )
        ''')
        
        # 数据缓存元信息表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT UNIQUE NOT NULL,
                ts_code TEXT,
                source_name TEXT,
                data_type TEXT NOT NULL,
                start_date TEXT,
                end_date TEXT,
                last_update TEXT DEFAULT CURRENT_TIMESTAMP,
                expiry_time TEXT,
                record_count INTEGER DEFAULT 0,
                is_valid BOOLEAN DEFAULT 1
            )
        ''')
        
        # API调用记录表 (用于限流和监控)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                ts_code TEXT,
                call_time TEXT DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN DEFAULT 1,
                error_message TEXT,
                response_size INTEGER,
                duration_ms INTEGER
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_daily_data_date 
            ON daily_data (trade_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_daily_data_code_source_date 
            ON daily_data (ts_code, source_name, trade_date)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_stocks_source 
            ON stocks (source_name)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_cache_key 
            ON cache_metadata (cache_key)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_api_calls_time 
            ON api_calls (call_time)
        ''')
        
        conn.commit()
        conn.close()
    
    def register_data_source(self, source_name: str, source_type: str, config: Dict[str, Any] = None):
        """
        注册数据源
        
        Args:
            source_name: 数据源名称
            source_type: 数据源类型 (tushare, yahoo, binance等)
            config: 数据源配置
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        config_json = json.dumps(config) if config else None
        
        cursor.execute('''
            INSERT OR REPLACE INTO data_sources 
            (source_name, source_type, config_json, last_update)
            VALUES (?, ?, ?, ?)
        ''', (source_name, source_type, config_json, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def insert_stocks(self, stocks_df: pd.DataFrame, source_name: str):
        """
        插入股票基本信息
        
        Args:
            stocks_df: 股票信息DataFrame
            source_name: 数据源名称
        """
        conn = sqlite3.connect(self.db_path)
        
        # 添加数据源字段
        stocks_df_copy = stocks_df.copy()
        stocks_df_copy['source_name'] = source_name
        stocks_df_copy['last_update'] = datetime.now().isoformat()
        
        # 删除该数据源的旧数据
        cursor = conn.cursor()
        cursor.execute('DELETE FROM stocks WHERE source_name = ?', (source_name,))
        
        # 插入新数据
        stocks_df_copy.to_sql('stocks', conn, if_exists='append', index=False)
        
        conn.close()
    
    def insert_daily_data(self, data_df: pd.DataFrame, source_name: str):
        """
        插入股票日线数据
        
        Args:
            data_df: 日线数据DataFrame
            source_name: 数据源名称
        """
        conn = sqlite3.connect(self.db_path)
        
        # 添加数据源字段
        data_df_copy = data_df.copy()
        data_df_copy['source_name'] = source_name
        data_df_copy['created_at'] = datetime.now().isoformat()
        
        try:
            data_df_copy.to_sql('daily_data', conn, if_exists='append', index=False)
        except sqlite3.IntegrityError:
            # 如果有重复数据，逐行插入并跳过重复项
            for _, row in data_df_copy.iterrows():
                try:
                    row_df = pd.DataFrame([row])
                    row_df.to_sql('daily_data', conn, if_exists='append', index=False)
                except sqlite3.IntegrityError:
                    continue  # 跳过重复数据
        
        conn.close()
    
    def get_stocks(self, source_name: str = None) -> pd.DataFrame:
        """
        获取股票列表
        
        Args:
            source_name: 数据源名称，如果为None则获取所有数据源的股票
            
        Returns:
            股票信息DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        if source_name:
            query = 'SELECT * FROM stocks WHERE source_name = ?'
            df = pd.read_sql(query, conn, params=[source_name])
        else:
            query = 'SELECT * FROM stocks'
            df = pd.read_sql(query, conn)
        
        conn.close()
        return df
    
    def get_daily_data(self, ts_code: str, start_date: str = None, end_date: str = None, 
                      source_name: str = 'tushare') -> pd.DataFrame:
        """
        获取股票日线数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期 (YYYYMMDD)
            end_date: 结束日期 (YYYYMMDD)
            source_name: 数据源名称
            
        Returns:
            日线数据DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        query = "SELECT * FROM daily_data WHERE ts_code = ? AND source_name = ?"
        params = [ts_code, source_name]
        
        if start_date:
            query += " AND trade_date >= ?"
            params.append(start_date)
            
        if end_date:
            query += " AND trade_date <= ?"
            params.append(end_date)
            
        query += " ORDER BY trade_date"
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        
        # 转换日期格式和数据类型
        if not df.empty:
            df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')
            df.set_index('trade_date', inplace=True)
            df = df.astype({
                'open': float,
                'high': float, 
                'low': float,
                'close': float,
                'volume': float,
                'amount': float
            })
        
        return df
    
    def check_data_exists(self, ts_code: str, trade_date: str, source_name: str = 'tushare') -> bool:
        """
        检查数据是否已存在
        
        Args:
            ts_code: 股票代码
            trade_date: 交易日期
            source_name: 数据源名称
            
        Returns:
            是否存在
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM daily_data WHERE ts_code = ? AND trade_date = ? AND source_name = ?",
            (ts_code, trade_date, source_name)
        )
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 0
    
    def get_latest_date(self, ts_code: str, source_name: str = 'tushare') -> Optional[str]:
        """
        获取股票最新数据日期
        
        Args:
            ts_code: 股票代码
            source_name: 数据源名称
            
        Returns:
            最新日期字符串 (YYYYMMDD)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT MAX(trade_date) FROM daily_data WHERE ts_code = ? AND source_name = ?",
            (ts_code, source_name)
        )
        result = cursor.fetchone()[0]
        
        conn.close()
        return result
    
    def delete_stock_data(self, ts_code: str, source_name: str = None):
        """
        删除指定股票的所有数据
        
        Args:
            ts_code: 股票代码
            source_name: 数据源名称，如果为None则删除所有数据源的数据
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if source_name:
            cursor.execute("DELETE FROM daily_data WHERE ts_code = ? AND source_name = ?", 
                          (ts_code, source_name))
            cursor.execute("DELETE FROM stocks WHERE ts_code = ? AND source_name = ?", 
                          (ts_code, source_name))
        else:
            cursor.execute("DELETE FROM daily_data WHERE ts_code = ?", (ts_code,))
            cursor.execute("DELETE FROM stocks WHERE ts_code = ?", (ts_code,))
        
        conn.commit()
        conn.close()
    
    def set_cache_metadata(self, cache_key: str, ts_code: str, source_name: str, 
                          data_type: str, start_date: str = None, end_date: str = None,
                          record_count: int = 0, expiry_hours: int = 24):
        """
        设置缓存元数据
        
        Args:
            cache_key: 缓存键
            ts_code: 股票代码
            source_name: 数据源名称
            data_type: 数据类型
            start_date: 开始日期
            end_date: 结束日期
            record_count: 记录数量
            expiry_hours: 过期小时数
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expiry_time = (datetime.now() + timedelta(hours=expiry_hours)).isoformat()
        
        cursor.execute('''
            INSERT OR REPLACE INTO cache_metadata 
            (cache_key, ts_code, source_name, data_type, start_date, end_date, 
             last_update, expiry_time, record_count, is_valid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (cache_key, ts_code, source_name, data_type, start_date, end_date,
              datetime.now().isoformat(), expiry_time, record_count, True))
        
        conn.commit()
        conn.close()
    
    def is_cache_valid(self, cache_key: str) -> bool:
        """
        检查缓存是否有效
        
        Args:
            cache_key: 缓存键
            
        Returns:
            是否有效
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT expiry_time, is_valid FROM cache_metadata 
            WHERE cache_key = ?
        ''', (cache_key,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False
        
        expiry_time_str, is_valid = result
        if not is_valid:
            return False
        
        expiry_time = datetime.fromisoformat(expiry_time_str)
        return datetime.now() < expiry_time
    
    def log_api_call(self, source_name: str, endpoint: str, ts_code: str = None,
                     success: bool = True, error_message: str = None, 
                     response_size: int = None, duration_ms: int = None):
        """
        记录API调用
        
        Args:
            source_name: 数据源名称
            endpoint: 接口名称
            ts_code: 股票代码
            success: 是否成功
            error_message: 错误消息
            response_size: 响应大小
            duration_ms: 持续时间(毫秒)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO api_calls 
            (source_name, endpoint, ts_code, success, error_message, response_size, duration_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (source_name, endpoint, ts_code, success, error_message, response_size, duration_ms))
        
        conn.commit()
        conn.close()
    
    def get_api_call_stats(self, source_name: str, hours: int = 24) -> Dict[str, Any]:
        """
        获取API调用统计
        
        Args:
            source_name: 数据源名称
            hours: 统计时间范围(小时)
            
        Returns:
            统计信息
        """
        conn = sqlite3.connect(self.db_path)
        
        since_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        query = '''
            SELECT 
                COUNT(*) as total_calls,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_calls,
                AVG(duration_ms) as avg_duration,
                MAX(call_time) as last_call_time
            FROM api_calls 
            WHERE source_name = ? AND call_time >= ?
        '''
        
        df = pd.read_sql(query, conn, params=[source_name, since_time])
        conn.close()
        
        if df.empty:
            return {'total_calls': 0, 'successful_calls': 0, 'avg_duration': 0, 'last_call_time': None}
        
        return df.iloc[0].to_dict()
    
    def clean_expired_cache(self):
        """清理过期的缓存数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        # 标记过期的缓存为无效
        cursor.execute('''
            UPDATE cache_metadata 
            SET is_valid = 0 
            WHERE expiry_time < ?
        ''', (now,))
        
        # 删除超过30天的API调用记录
        old_time = (datetime.now() - timedelta(days=30)).isoformat()
        cursor.execute('DELETE FROM api_calls WHERE call_time < ?', (old_time,))
        
        conn.commit()
        conn.close()
    
    def get_data_source_info(self, source_name: str = None) -> pd.DataFrame:
        """
        获取数据源信息
        
        Args:
            source_name: 数据源名称，如果为None则获取所有数据源
            
        Returns:
            数据源信息DataFrame
        """
        conn = sqlite3.connect(self.db_path)
        
        if source_name:
            query = 'SELECT * FROM data_sources WHERE source_name = ?'
            df = pd.read_sql(query, conn, params=[source_name])
        else:
            query = 'SELECT * FROM data_sources'
            df = pd.read_sql(query, conn)
        
        conn.close()
        return df