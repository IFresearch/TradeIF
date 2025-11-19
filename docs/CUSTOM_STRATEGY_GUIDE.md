# TradeIF - 自定义策略开发指南

## 📚 简介

TradeIF 支持用户使用Python编写自定义交易策略。通过简洁友好的API，您可以专注于交易逻辑的开发，而无需关心底层技术细节。

## 🎯 核心特性

- **友好的数据访问语法**：使用 `current.ma5` 而不是 `df.iloc[i]['ma5']`
- **147+ 预计算技术指标**：包括均线、RSI、MACD、布林带等
- **Monaco Editor代码编辑器**：支持语法高亮、代码折叠、自动补全
- **实时代码验证**：即时检查代码语法错误
- **策略模板库**：提供多个预设策略模板快速上手

## 📖 快速入门

### 基本结构

每个自定义策略必须设置两个变量：

```python
signal = 1   # 交易信号：1=买入, -1=卖出, 0=无操作
reason = "买入理由"  # 交易理由说明
```

### 可用变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `current` | 当前数据行 | `current.ma5`, `current.close` |
| `prev` | 前一行数据 | `prev.ma5`, `prev.close` |
| `position` | 当前持仓状态 | `0`=空仓, `>0`=持仓 |
| `entry_price` | 买入价格 | 用于计算收益率 |
| `data` | 完整历史数据 | pandas DataFrame |
| `pd` | Pandas库 | 用于数据处理 |
| `np` | NumPy库 | 用于数值计算 |

### 常用技术指标

#### 移动平均线系列
- `current.ma5` - 5日简单移动平均
- `current.ma10` - 10日简单移动平均  
- `current.ma20` - 20日简单移动平均
- `current.ma50` - 50日简单移动平均
- `current.ma200` - 200日简单移动平均
- `current.ema12` - 12日指数移动平均
- `current.ema26` - 26日指数移动平均

#### 动量指标
- `current.rsi` / `current.rsi14` - 相对强弱指标
- `current.macd` - MACD线
- `current.macd_signal` - MACD信号线
- `current.macd_hist` - MACD柱状图
- `current.kdj_k`, `current.kdj_d`, `current.kdj_j` - KDJ指标

#### 波动率指标
- `current.bb_upper` - 布林带上轨
- `current.bb_middle` - 布林带中轨
- `current.bb_lower` - 布林带下轨
- `current.atr` - 平均真实波幅

#### 成交量指标
- `current.volume` - 成交量
- `current.volume_ma5` - 5日成交量均线
- `current.volume_ratio` - 量比
- `current.obv` - 能量潮

#### 价格数据
- `current.open` - 开盘价
- `current.high` - 最高价
- `current.low` - 最低价
- `current.close` - 收盘价

## 💡 策略示例

### 1. 双均线交叉策略（推荐）

```python
# 双均线交叉策略 - 用户友好版本
if not pd.isna(current.ma5) and not pd.isna(current.ma20):
    if not pd.isna(prev.ma5) and not pd.isna(prev.ma20):
        # 金叉买入
        if current.ma5 > current.ma20 and prev.ma5 <= prev.ma20 and position == 0:
            signal = 1
            reason = f'MA金叉买入: MA5={current.ma5:.2f} > MA20={current.ma20:.2f}'
        # 死叉卖出
        elif current.ma5 < current.ma20 and prev.ma5 >= prev.ma20 and position > 0:
            signal = -1
            reason = f'MA死叉卖出: MA5={current.ma5:.2f} < MA20={current.ma20:.2f}'
        else:
            signal = 0
            reason = ''
```

### 2. RSI超买超卖策略

```python
# RSI策略
if not pd.isna(current.rsi14):
    # 超卖买入
    if current.rsi14 < 30 and position == 0:
        signal = 1
        reason = f'RSI超卖买入: RSI={current.rsi14:.1f}'
    # 超买卖出
    elif current.rsi14 > 70 and position > 0:
        signal = -1
        reason = f'RSI超买卖出: RSI={current.rsi14:.1f}'
    else:
        signal = 0
        reason = ''
```

### 3. 布林带反弹策略

```python
# 布林带反弹策略
if not pd.isna(current.bb_lower) and not pd.isna(current.bb_upper):
    # 触及下轨反弹买入
    if current.close <= current.bb_lower * 1.01 and position == 0:
        signal = 1
        reason = f'触及布林带下轨({current.bb_lower:.2f})买入'
    # 触及上轨卖出
    elif current.close >= current.bb_upper * 0.99 and position > 0:
        signal = -1
        reason = f'触及布林带上轨({current.bb_upper:.2f})卖出'
    else:
        signal = 0
        reason = ''
```

### 4. 多因子综合策略

```python
# 多因子综合策略
# 计算综合评分
tech_score = current.tech_score if not pd.isna(current.tech_score) else 0
momentum = current.momentum_factor if not pd.isna(current.momentum_factor) else 0
trend = current.trend_strength if not pd.isna(current.trend_strength) else 0

# 综合评分
composite_score = tech_score * 0.4 + momentum * 0.3 + trend * 0.3

# 根据评分交易
if composite_score > 0.6 and position == 0:
    signal = 1
    reason = f'综合评分买入: {composite_score:.2f}'
elif composite_score < -0.6 and position > 0:
    signal = -1
    reason = f'综合评分卖出: {composite_score:.2f}'
else:
    signal = 0
    reason = ''
```

### 5. MACD金叉死叉策略

```python
# MACD策略
if not pd.isna(current.macd) and not pd.isna(current.macd_signal):
    if not pd.isna(prev.macd) and not pd.isna(prev.macd_signal):
        # MACD金叉
        if (current.macd > current.macd_signal and 
            prev.macd <= prev.macd_signal and 
            position == 0):
            signal = 1
            reason = 'MACD金叉买入'
        # MACD死叉
        elif (current.macd < current.macd_signal and 
              prev.macd >= prev.macd_signal and 
              position > 0):
            signal = -1
            reason = 'MACD死叉卖出'
        else:
            signal = 0
            reason = ''
```

## ✅ 最佳实践

### 1. 数据有效性检查

始终检查数据是否有效：

```python
# ✅ 推荐
if not pd.isna(current.ma5) and not pd.isna(current.ma20):
    # 您的策略逻辑
    pass

# ❌ 不推荐
if current.ma5 > current.ma20:  # 可能产生NaN错误
    pass
```

### 2. 持仓状态检查

确保买入时无持仓，卖出时有持仓：

```python
# ✅ 推荐
if condition and position == 0:  # 买入
    signal = 1
elif condition and position > 0:  # 卖出
    signal = -1

# ❌ 不推荐  
if condition:  # 没有检查持仓状态
    signal = 1
```

### 3. 清晰的交易理由

提供详细的交易理由，包含关键数据：

```python
# ✅ 推荐
reason = f'MA金叉买入: MA5={current.ma5:.2f} > MA20={current.ma20:.2f}'

# ❌ 不推荐
reason = '买入'  # 信息不足
```

### 4. 使用前后数据对比

检测交叉、突破等需要对比前后数据：

```python
# ✅ 推荐 - 检测金叉
if current.ma5 > current.ma20 and prev.ma5 <= prev.ma20:
    # 确实发生了交叉
    pass

# ❌ 不推荐 - 只检查当前状态
if current.ma5 > current.ma20:
    # 可能已经交叉很久了
    pass
```

## ⚠️ 常见错误

### 错误1：忘记检查NaN值

```python
# ❌ 错误
if current.ma5 > current.ma20:  # 如果ma5或ma20是NaN会出错
    signal = 1

# ✅ 正确
if not pd.isna(current.ma5) and not pd.isna(current.ma20):
    if current.ma5 > current.ma20:
        signal = 1
```

### 错误2：没有初始化signal和reason

```python
# ❌ 错误 - 某些情况下signal和reason可能未定义
if condition:
    signal = 1
    reason = '买入'

# ✅ 正确 - 始终确保有默认值
signal = 0
reason = ''
if condition:
    signal = 1
    reason = '买入'
```

### 错误3：使用了危险操作

```python
# ❌ 禁止使用
import os  # 不允许import
exec(code)  # 不允许exec
eval(expr)  # 不允许eval
open('file.txt')  # 不允许文件操作
```

## 🔧 调试技巧

### 1. 使用代码验证功能

在提交策略前，点击"验证代码"按钮检查：
- 是否包含必需的变量（signal和reason）
- 是否使用了禁止的操作

### 2. 从模板开始

使用预设模板快速开始：
1. 选择策略模板下拉框
2. 选择合适的模板
3. 根据需要修改参数和逻辑

### 3. 逐步测试

建议从简单策略开始：
1. 先测试单一指标策略（如纯RSI）
2. 确认逻辑正确后再添加复杂条件
3. 逐步优化参数

## 📊 性能优化建议

1. **避免复杂计算**：使用系统预计算的指标而不是自己计算
2. **合理使用条件**：先检查简单条件，再检查复杂条件
3. **缓存中间结果**：如果某个值会多次使用，先保存到变量

```python
# ✅ 推荐 - 缓存结果
ma_diff = current.ma5 - current.ma20
if ma_diff > 0 and abs(ma_diff) < 0.5:
    # 使用 ma_diff
    pass

# ❌ 不推荐 - 重复计算
if (current.ma5 - current.ma20) > 0 and abs(current.ma5 - current.ma20) < 0.5:
    pass
```

## 📞 获取帮助

- 查看系统提供的预设模板
- 参考本文档的示例代码
- 使用Monaco Editor的代码补全功能（输入`current.`查看可用指标）

## 🎉 总结

自定义策略开发的核心要点：

1. ✅ 使用友好的 `current.指标名` 语法访问数据
2. ✅ 始终检查数据有效性（NaN检查）
3. ✅ 检查持仓状态避免重复买卖
4. ✅ 提供清晰的交易理由
5. ✅ 使用prev对比检测交叉和突破
6. ✅ 利用Monaco Editor的智能提示功能

Happy Trading! 📈
