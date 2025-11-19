# 📈 TradeIF

> **Trade with Intelligence & Flexibility**  
> 一个轻量级本地部署的量化交易回测平台，支持自定义策略开发、多种技术指标分析和可视化图表展示

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 核心功能

### 📊 数据管理
- **实时数据获取**: 集成Tushare API，支持A股日线数据获取
- **智能缓存系统**: SQLite本地缓存，减少API调用，提升访问速度
- **多股票支持**: 支持沪深两市所有股票（格式：000001.SZ、600000.SH，参考Tushare股票列表）

### 💹 策略回测
- **预设策略库**: 
  - 双均线交叉策略（MA Cross）
  - RSI超买超卖策略
  - 布林带策略（Bollinger Bands）
- **自定义策略**: 
  - 内置Monaco编辑器，支持Python语法
  - 147+ 预计算技术指标
  - 友好的API设计，易于开发
- **性能指标**: 
  - 总收益率、年化收益率
  - 夏普比率、最大回撤
  - 胜率、盈亏比
  - 详细交易记录

### 📉 可视化图表
- **TradingView专业图表**: 
  - K线图、折线图、面积图自由切换
  - 双Y轴设计（价格/成交量分离）
  - 交易信号标注
  - 实时鼠标提示（OHLC、成交量、交易信息）
- **权益曲线**: 直观展示策略表现
- **交易记录表**: 完整的买卖操作历史

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- pip 包管理器

### 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd TradeIF

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置Tushare Token
# 编辑 config/config.yaml，填入您的token
```

### 配置Tushare

1. 访问 [Tushare官网](https://tushare.pro/register) 注册账号
2. 获取API Token
3. 编辑 `config/config.yaml`：

```yaml
data_sources:
  tushare:
    enabled: true
    token: "YOUR_TUSHARE_TOKEN_HERE"  # 替换为您的token
```

### 启动服务

```bash
# Windows
python backend\api\main.py

# Linux/Mac
python backend/api/main.py
```

### 访问系统

打开浏览器访问：**http://127.0.0.1:8000**

详细使用说明请参阅 [快速开始指南](QUICK_START.md)

---

## 📁 项目结构

```
TradeIF/
├── backend/              # 后端服务
│   ├── api/                   # FastAPI应用
│   │   └── main.py           # 主应用入口
│   ├── data/                 # 数据管理
│   │   ├── base.py          # 数据源基类
│   │   ├── manager.py       # 数据管理器
│   │   ├── cache_manager.py # 缓存管理
│   │   └── tushare_source.py # Tushare数据源
│   ├── strategies/           # 策略模块
│   │   ├── base.py          # 策略基类
│   │   ├── ma_cross_strategy.py      # 双均线策略
│   │   ├── rsi_strategy.py           # RSI策略
│   │   ├── bollinger_strategy.py     # 布林带策略
│   │   └── custom_strategy.py        # 自定义策略执行器
│   └── database.py          # 数据库操作
├── frontend/                 # 前端界面
│   ├── index.html           # 主页面
│   └── chart_utils.js       # 图表工具
├── config/                   # 配置文件
│   └── config.yaml          # 系统配置
├── data/                     # 数据存储
│   └── stocks.db            # SQLite数据库
├── docs/                     # 文档目录
│   └── CUSTOM_STRATEGY_GUIDE.md  # 自定义策略指南
├── requirements.txt          # Python依赖
├── README.md                # 项目说明（本文件）
├── QUICK_START.md           # 快速开始指南
└── start.bat                # Windows启动脚本
```

---

## 📚 文档导航

- **[快速开始指南](QUICK_START.md)**: 新手入门、策略介绍、使用教程
- **[自定义策略开发](docs/CUSTOM_STRATEGY_GUIDE.md)**: 策略开发、技术指标、最佳实践

---

## 🔌 API接口

### 获取历史数据
```http
POST /api/data/historical
Content-Type: application/json

{
  "symbol": "000001.SZ",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31"
}
```

### 运行回测
```http
POST /api/backtest/run
Content-Type: application/json

{
  "symbol": "000001.SZ",
  "strategy": "ma_cross",
  "params": {
    "short_window": 20,
    "long_window": 50,
    "initial_capital": 100000
  },
  "data": [...]
}
```

### 搜索股票
```http
GET /api/stocks/search?q=平安银行
```

---

## ⚙️ 系统配置

### config/config.yaml

```yaml
# 数据源配置
data_sources:
  tushare:
    enabled: true
    token: ""  # Tushare API Token

# 数据库配置
database:
  path: "data/stocks.db"

# API服务配置
api:
  host: "127.0.0.1"
  port: 8000
  debug: true

# 回测配置
backtest:
  initial_capital: 100000  # 初始资金（元）
  commission: 0.001        # 手续费率（0.1%）
```

---

## 🛠️ 技术栈

### 后端
- **FastAPI**: 高性能Web框架
- **Pandas**: 数据处理和分析
- **NumPy**: 数值计算
- **Tushare**: 金融数据接口
- **SQLite**: 本地数据缓存

### 前端
- **Vanilla JavaScript**: 无框架依赖
- **TradingView Lightweight Charts**: 专业K线图表
- **Monaco Editor**: VSCode级别的代码编辑器

---

## 🔧 常见问题

### Q: Tushare Token在哪里获取？
A: 访问 https://tushare.pro/register 注册后，在用户中心可以看到您的Token

### Q: 为什么数据获取失败？
A: 请检查：
1. Token是否正确配置
2. 网络连接是否正常
3. 股票代码格式是否正确（如：000001.SZ）
4. 是否达到Tushare API调用限制

### Q: 如何添加新的技术指标？
A: 编辑 `backend/strategies/custom_strategy.py`，在 `_calculate_all_indicators` 方法中添加指标计算逻辑

### Q: 回测结果不准确？
A: 请注意：
1. 本系统未考虑滑点、冲击成本
2. 默认手续费率为0.1%，可在配置中调整
3. 回测基于日线数据，不支持分钟级
4. 历史数据不能完全预测未来表现

---

## 📄 开源协议

本项目采用 MIT 许可证

---

## ⚠️ 免责声明

**重要提示**：
- 本系统仅用于学习、研究和技术交流目的
- 历史回测结果不代表未来表现
- 不构成任何投资建议
- 实际交易需谨慎决策，风险自担

---

<div align="center">
  <sub>Built with ❤️ by developers for traders</sub>
</div>
