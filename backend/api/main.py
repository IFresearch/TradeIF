"""
简化的FastAPI应用
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import yaml
import os
import sys
import pandas as pd
import numpy as np

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.data.manager import DataManager
from backend.strategies.ma_cross_strategy import MovingAverageCrossStrategy
from backend.strategies.rsi_strategy import RSIStrategy
from backend.strategies.bollinger_strategy import BollingerBandsStrategy
from backend.strategies.custom_strategy import CustomStrategy
from backend.database import StockDatabase

# 创建FastAPI应用
app = FastAPI(
    title="股票回测系统 API",
    description="回测平台",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务
frontend_path = os.path.join(project_root, "frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

# 全局变量
data_manager = None
config = {}

# 请求模型
class HistoricalDataRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str

class BacktestRequest(BaseModel):
    symbol: str
    strategy: str
    params: Dict[str, Any]
    data: List[Dict[str, Any]]

# 辅助函数
def getStrategyName(strategy_key):
    """获取策略中文名称"""
    strategy_names = {
        'ma_cross': '双均线交叉策略',
        'rsi': 'RSI超买超卖策略', 
        'bollinger': '布林带策略',
        'kdj': 'KDJ随机指标策略',
        'custom': '自定义策略'
    }
    return strategy_names.get(strategy_key, strategy_key)

# 初始化
def load_config():
    """加载配置文件"""
    global config, data_manager
    config_path = os.path.join(project_root, "config", "config.yaml")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        config = {'data_sources': {'tushare': {'enabled': True, 'token': ''}}}
    
    # 初始化数据管理器
    data_manager = DataManager(config_path)

# API路由
@app.get("/")
async def read_index():
    """返回前端页面"""
    frontend_path = os.path.join(project_root, "frontend", "index.html")
    if os.path.exists(frontend_path):
        return FileResponse(frontend_path)
    return {"message": "股票回测系统 API", "docs": "/docs"}

@app.get("/test")
async def test_chart():
    """返回测试图表页面"""
    test_path = os.path.join(project_root, "frontend", "test-chart.html")
    if os.path.exists(test_path):
        return FileResponse(test_path)
    return {"message": "测试页面不存在"}

@app.get("/api/health")
async def health_check():
    """健康检查"""
    result = {
        "status": "healthy",
        "message": "系统运行正常",
        "data_sources": data_manager.list_sources() if data_manager else []
    }
    
    # 测试Tushare连接
    if data_manager:
        tushare_source = data_manager.get_source('tushare')
        if tushare_source:
            try:
                # 尝试获取一个简单的数据来测试连接
                test_symbols = tushare_source.get_popular_stocks()
                result["tushare_status"] = "连接正常"
                result["test_symbols"] = test_symbols[:5] if test_symbols else []
            except Exception as e:
                result["tushare_status"] = f"连接失败: {str(e)}"
                result["tushare_error"] = str(e)
        else:
            result["tushare_status"] = "未配置"
    
    return result

@app.post("/api/data/historical")
async def get_historical_data(request: HistoricalDataRequest):
    """获取历史数据"""
    try:
        print(f"收到历史数据请求: {request.symbol}, {request.start_date} 到 {request.end_date}")
        
        if not data_manager:
            print("错误: 数据管理器未初始化")
            raise HTTPException(status_code=500, detail="数据管理器未初始化")
        
        print(f"可用数据源: {data_manager.list_sources()}")
        
        # 检查数据源
        if not data_manager.list_sources():
            print("错误: 没有可用的数据源")
            raise HTTPException(status_code=500, detail="没有可用的数据源，请检查Tushare token配置")
        
        data = data_manager.get_historical_data(
            request.symbol,
            request.start_date,
            request.end_date
        )
        
        print(f"获取到 {len(data)} 条数据记录")
        
        if data.empty:
            print("警告: 数据为空")
            return {
                "success": False,
                "error": f"未获取到股票 {request.symbol} 的数据，请检查股票代码和日期范围"
            }
        
        # 转换为API格式
        data_list = []
        for timestamp, row in data.iterrows():
            data_list.append({
                "timestamp": timestamp.isoformat(),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": float(row['volume']) if 'volume' in row and pd.notna(row['volume']) else 0.0
            })
        
        print(f"成功返回 {len(data_list)} 条数据")
        return {
            "success": True,
            "symbol": request.symbol,
            "data": data_list,
            "count": len(data_list)
        }
        
    except Exception as e:
        error_msg = f"获取数据失败: {str(e)}"
        print(f"错误: {error_msg}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=error_msg)

@app.post("/api/backtest/run")
async def run_backtest(request: BacktestRequest):
    """运行回测"""
    try:
        print(f"收到回测请求: strategy={request.strategy}, data count={len(request.data)}")
        print(f"参数: {request.params}")
        
        # 转换数据格式
        data_df = pd.DataFrame(request.data)
        print(f"创建DataFrame: {data_df.shape}")
        print(f"DataFrame列: {list(data_df.columns)}")
        
        data_df['timestamp'] = pd.to_datetime(data_df['timestamp'])
        data_df.set_index('timestamp', inplace=True)
        print(f"设置索引后: {data_df.shape}, index: {data_df.index.name}")
        
        # 创建策略实例
        strategy_map = {
            'ma_cross': MovingAverageCrossStrategy,
            'rsi': RSIStrategy,
            'bollinger': BollingerBandsStrategy,
            'custom': CustomStrategy
        }
        
        if request.strategy not in strategy_map:
            raise ValueError(f"不支持的策略类型: {request.strategy}")
        
        strategy_class = strategy_map[request.strategy]
        params = request.params
        
        if request.strategy == 'ma_cross':
            strategy = strategy_class(
                short_window=params.get('short_window', 20),
                long_window=params.get('long_window', 50)
            )
        elif request.strategy == 'rsi':
            strategy = strategy_class(
                period=params.get('period', 14),
                oversold_threshold=params.get('oversold_threshold', 30),
                overbought_threshold=params.get('overbought_threshold', 70),
                stop_loss=params.get('stop_loss', 0.05),
                take_profit=params.get('take_profit', 0.10)
            )
        elif request.strategy == 'bollinger':
            strategy = strategy_class(
                period=params.get('period', 20),
                std_multiplier=params.get('std_multiplier', 2.0),
                stop_loss=params.get('stop_loss', 0.05),
                take_profit=params.get('take_profit', 0.10)
            )
        elif request.strategy == 'custom':
            strategy = strategy_class(
                custom_code=params.get('custom_code', ''),
                initial_capital=params.get('initial_capital', 100000)
            )
        else:
            # 使用默认参数创建策略
            strategy = strategy_class(**params)
        
        # 运行回测
        print("开始运行回测...")
        results = strategy.backtest(
            data_df,
            initial_capital=request.params.get('initial_capital', 100000)
        )
        print(f"回测完成: {len(results.get('trades', []))} 笔交易")
        
        # 清理NaN值
        def clean_for_json(obj):
            """递归清理对象中的NaN和无穷大值"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif isinstance(obj, float):
                if pd.isna(obj) or not np.isfinite(obj):
                    return 0.0
                return float(obj)
            elif hasattr(obj, 'dtype') and np.issubdtype(obj.dtype, np.floating):
                # 处理numpy浮点数
                if pd.isna(obj) or not np.isfinite(obj):
                    return 0.0
                return float(obj)
            else:
                return obj
        
        # 根据不同策略处理返回结果
        if request.strategy in ['rsi', 'bollinger', 'kdj', 'custom']:
            # 新策略返回格式处理
            metrics = results.get('metrics', {})
            trades = results.get('trades', [])
            portfolio_values = results.get('portfolio_values', [])
            
            # 构建权益曲线 (兼容前端显示)
            equity_curve = []
            for pv in portfolio_values:
                equity_curve.append({
                    'date': pv['date'],
                    'value': pv['portfolio_value']
                })
            
            response_data = {
                "success": True,
                "strategy": getStrategyName(request.strategy),
                "metrics": clean_for_json(metrics),
                "trades": clean_for_json(trades),
                "equity_curve": clean_for_json(equity_curve)
            }
            
            # 为了统一打印格式
            clean_trades = response_data["trades"]
            clean_equity_curve = response_data["equity_curve"]
        else:
            # 原有策略格式
            clean_metrics = clean_for_json(results['metrics'])
            clean_trades = clean_for_json(results['trades'])
            clean_equity_curve = clean_for_json(results['equity_curve'])
            
            response_data = {
                "success": True,
                "strategy": getStrategyName(request.strategy),
                "metrics": clean_metrics,
                "trades": clean_trades,
                "equity_curve": clean_equity_curve
            }
        
        print(f"返回清理后的结果: {len(clean_trades)} 笔交易, {len(clean_equity_curve)} 个权益曲线点")
        return response_data
        
    except Exception as e:
        error_msg = f"回测失败: {str(e)}"
        print(f"回测错误: {error_msg}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=error_msg)

@app.get("/api/stocks/search")
async def search_stocks(q: str = ""):
    """搜索股票"""
    try:
        if not data_manager:
            raise HTTPException(status_code=500, detail="数据管理器未初始化")
        
        if not q:
            # 返回热门股票
            tushare_source = data_manager.get_source('tushare')
            if tushare_source and hasattr(tushare_source, 'get_popular_stocks'):
                stocks = tushare_source.get_popular_stocks()
            else:
                stocks = ['000001.SZ', '600000.SH', '600519.SH', '000858.SZ', '002415.SZ']
        else:
            stocks = data_manager.search_symbols(q)
        
        return {
            "success": True,
            "query": q,
            "stocks": stocks[:20]  # 限制返回数量
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"搜索失败: {str(e)}")

@app.post("/api/data/update")
async def update_stock_data():
    """更新股票数据"""
    try:
        if not data_manager:
            raise HTTPException(status_code=500, detail="数据管理器未初始化")
        
        # 更新所有数据源的股票列表
        data_manager.update_all_stock_lists()
        
        return {
            "success": True,
            "message": "股票数据更新完成"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"更新失败: {str(e)}")

@app.get("/api/cache/status")
async def get_cache_status():
    """获取缓存状态"""
    try:
        if not data_manager:
            raise HTTPException(status_code=500, detail="数据管理器未初始化")
        
        # 添加超时保护，避免长时间等待
        import asyncio
        try:
            # 设置5秒超时
            cache_stats = await asyncio.wait_for(
                asyncio.to_thread(data_manager.get_cache_statistics),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "获取缓存统计信息超时，请稍后重试",
                "cache_statistics": {},
                "source_status": {}
            }
        
        # 获取数据源状态
        try:
            source_status = await asyncio.wait_for(
                asyncio.to_thread(data_manager.get_source_status),
                timeout=3.0
            )
        except asyncio.TimeoutError:
            source_status = {"error": "获取数据源状态超时"}
        
        return {
            "success": True,
            "cache_statistics": cache_stats,
            "source_status": source_status
        }
        
    except Exception as e:
        import traceback
        print(f"获取缓存状态失败: {str(e)}")
        print(f"详细错误: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"获取缓存状态失败: {str(e)}")

@app.post("/api/cache/warmup")
async def warm_up_cache(symbols: List[str] = None, days: int = 365):
    """预热缓存"""
    try:
        if not data_manager:
            raise HTTPException(status_code=500, detail="数据管理器未初始化")
        
        # 预热缓存
        data_manager.warm_up_cache(symbols, days)
        
        return {
            "success": True,
            "message": f"缓存预热完成，股票数量: {len(symbols) if symbols else '默认'}, 天数: {days}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"缓存预热失败: {str(e)}")

@app.post("/api/cache/cleanup")
async def cleanup_cache(days: int = 30):
    """清理缓存"""
    try:
        if not data_manager:
            raise HTTPException(status_code=500, detail="数据管理器未初始化")
        
        # 清理缓存
        data_manager.cleanup_cache(days)
        
        return {
            "success": True,
            "message": f"缓存清理完成，保留 {days} 天内的数据"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"缓存清理失败: {str(e)}")

@app.get("/api/data/quality")
async def get_data_quality_report(symbols: str = None):
    """获取数据质量报告"""
    try:
        if not data_manager:
            raise HTTPException(status_code=500, detail="数据管理器未初始化")
        
        # 解析股票代码
        symbol_list = None
        if symbols:
            symbol_list = symbols.split(',')
        
        # 生成数据质量报告
        reports = data_manager.get_data_quality_report(symbol_list)
        
        return {
            "success": True,
            "reports": reports
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"生成数据质量报告失败: {str(e)}")

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动"""
    load_config()
    print("股票回测系统启动成功!")
    if data_manager:
        print(f"可用数据源: {data_manager.list_sources()}")

if __name__ == "__main__":
    import uvicorn
    
    load_config()
    api_config = config.get('api', {})
    
    uvicorn.run(
        "main:app",
        host=api_config.get('host', '127.0.0.1'),
        port=api_config.get('port', 8000),
        reload=False
    )