/**
 * TradeIF - Lightweight Charts 工具函数
 * 专业的K线图表渲染 - 基于 TradingView Lightweight Charts
 */

// 全局图表实例
let priceChart = null;
let equityChart = null;

// 图表控件状态
let chartControls = {
    showVolume: true,
    chartType: 'candlestick', // candlestick, line, area
    timeframe: '1D'
};

/**
 * 工具函数: 将ISO字符串转换为Unix时间（秒）
 */
function toUnixTimestamp(value) {
    if (!value) {
        return null;
    }
    return Math.floor(new Date(value).getTime() / 1000);
}

/**
 * 工具函数: 统一格式化时间 (Lightweight Charts 可能传入对象或秒时间戳)
 */
function formatDateLabel(time) {
    if (!time) {
        return '';
    }
    if (typeof time === 'object' && 'year' in time) {
        const { year, month, day } = time;
        return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    }
    const date = new Date(time * 1000);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    return `${year}-${month}-${day}` + (hours !== '00' ? ` ${hours}:00` : '');
}

/**
 * 创建提示浮层
 */
function createTooltip(container) {
    const tooltip = document.createElement('div');
    tooltip.className = 'chart-tooltip';
    tooltip.style.display = 'none';
    tooltip.innerHTML = '';
    container.appendChild(tooltip);
    return tooltip;
}

/**
 * 创建图表工具栏
 */
function createChartToolbar(container, onControlChange) {
    const toolbar = document.createElement('div');
    toolbar.className = 'chart-toolbar';
    toolbar.innerHTML = `
        <div class="chart-toolbar-left">
            <button class="chart-btn chart-btn-active" data-type="candlestick" title="蜡烛图">
                <svg width="16" height="16" viewBox="0 0 16 16"><path fill="currentColor" d="M8 2v2M8 12v2M5 5h6v6H5z"/></svg>
            </button>
            <button class="chart-btn" data-type="line" title="折线图">
                <svg width="16" height="16" viewBox="0 0 16 16"><path fill="currentColor" d="M2 12l4-6 3 3 5-7"/></svg>
            </button>
            <button class="chart-btn" data-type="area" title="面积图">
                <svg width="16" height="16" viewBox="0 0 16 16"><path fill="currentColor" d="M2 12l4-6 3 3 5-7v8H2z"/></svg>
            </button>
            <div class="chart-divider"></div>
            <button class="chart-btn chart-btn-active" data-action="volume" title="成交量">
                <svg width="16" height="16" viewBox="0 0 16 16"><rect fill="currentColor" x="2" y="8" width="2" height="6"/><rect fill="currentColor" x="6" y="5" width="2" height="9"/><rect fill="currentColor" x="10" y="10" width="2" height="4"/></svg>
            </button>
        </div>
        <div class="chart-toolbar-right">
            <button class="chart-btn" data-action="fullscreen" title="全屏">
                <svg width="16" height="16" viewBox="0 0 16 16"><path fill="currentColor" d="M2 2h4v2H4v2H2V2zm10 0h4v4h-2V4h-2V2zM2 12v-2h2v2h2v2H2v-4zm12 0v2h-2v-2h-2v-2h4v2z"/></svg>
            </button>
            <button class="chart-btn" data-action="snapshot" title="截图">
                <svg width="16" height="16" viewBox="0 0 16 16"><circle fill="currentColor" cx="8" cy="8" r="3"/><path fill="currentColor" d="M14 4h-3l-1-2H6L5 4H2v10h12V4z"/></svg>
            </button>
        </div>
    `;
    
    // 事件监听
    toolbar.addEventListener('click', (e) => {
        const btn = e.target.closest('.chart-btn');
        if (!btn) return;
        
        const type = btn.dataset.type;
        const action = btn.dataset.action;
        
        if (type) {
            // 切换图表类型
            toolbar.querySelectorAll('[data-type]').forEach(b => b.classList.remove('chart-btn-active'));
            btn.classList.add('chart-btn-active');
            onControlChange({ chartType: type });
        } else if (action === 'volume') {
            // 切换成交量显示
            btn.classList.toggle('chart-btn-active');
            onControlChange({ showVolume: btn.classList.contains('chart-btn-active') });
        } else if (action === 'fullscreen') {
            // 全屏
            if (container.requestFullscreen) {
                if (!document.fullscreenElement) {
                    container.requestFullscreen();
                } else {
                    document.exitFullscreen();
                }
            }
        } else if (action === 'snapshot') {
            // 截图功能
            takeSnapshot(container);
        }
    });
    
    container.insertBefore(toolbar, container.firstChild);
    return toolbar;
}

/**
 * 截图功能
 */
function takeSnapshot(container) {
    try {
        // 简单提示 - 实际需要 html2canvas 等库
        alert('截图功能需要集成 html2canvas 库，当前为演示版本');
    } catch (e) {
        console.error('截图失败:', e);
    }
}

/**
 * 创建TradingView风格的价格图表
 */
function createPriceChart(containerId, data, trades = null) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // 清除旧图表 - 使用安全的销毁方法
    if (priceChart) {
        try {
            priceChart.remove();
        } catch (e) {
            console.warn('清除旧图表时出错:', e);
        }
        priceChart = null;
    }
    
    container.innerHTML = '';
    
    // 存储原始数据供重绘使用
    let chartData = data;
    let chartTrades = trades;
    let mainSeries = null;
    let volumeSeries = null;
    
    // 创建工具栏
    createChartToolbar(container, (controls) => {
        Object.assign(chartControls, controls);
        updateChart();
    });
    
    // 创建图表容器
    const chartWrapper = document.createElement('div');
    chartWrapper.className = 'chart-wrapper';
    chartWrapper.style.cssText = 'width: 100%; height: calc(100% - 45px); position: relative; padding-bottom: 5px;';
    container.appendChild(chartWrapper);
    
    // 创建图表
    priceChart = LightweightCharts.createChart(chartWrapper, {
        width: chartWrapper.clientWidth,
        height: chartWrapper.clientHeight,
        layout: {
            background: { color: '#0F0F0F' },
            textColor: '#D1D4DC',
            fontSize: 12,
        },
        grid: {
            vertLines: { 
                color: 'rgba(242, 242, 242, 0.06)',
                style: LightweightCharts.LineStyle.Solid,
            },
            horzLines: { 
                color: 'rgba(242, 242, 242, 0.06)',
                style: LightweightCharts.LineStyle.Solid,
            },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                color: 'rgba(224, 227, 235, 0.1)',
                width: 1,
                style: LightweightCharts.LineStyle.Solid,
                labelBackgroundColor: '#2962FF',
            },
            horzLine: {
                color: 'rgba(224, 227, 235, 0.1)',
                width: 1,
                style: LightweightCharts.LineStyle.Solid,
                labelBackgroundColor: '#2962FF',
            },
        },
        localization: {
            locale: 'zh-CN',
            dateFormat: 'yyyy-MM-dd',
        },
        rightPriceScale: {
            borderColor: 'rgba(197, 203, 206, 0.4)',
            scaleMargins: {
                top: 0.05,
                bottom: 0.05,
            },
        },
        leftPriceScale: {
            visible: true,
            borderColor: 'rgba(197, 203, 206, 0.4)',
            scaleMargins: {
                top: 0.75,  // 成交量占据下方25%空间
                bottom: 0,
            },
        },
        timeScale: {
            borderColor: 'rgba(197, 203, 206, 0.4)',
            timeVisible: true,
            secondsVisible: false,
            fixLeftEdge: true,
            fixRightEdge: true,
            tickMarkFormatter: (time) => formatDateLabel(time),
            visible: true,
            minimumHeight: 40,
        },
        handleScale: {
            axisPressedMouseMove: {
                time: true,
                price: true,
            },
        },
    });
    
    // 为提示信息准备Dom
    const tooltip = createTooltip(chartWrapper);
    
    // 更新图表函数
    function updateChart() {
        console.log('=== Chart Update Debug ===');
        console.log('Chart Data Count:', chartData ? chartData.length : 0);
        console.log('Chart Trades:', chartTrades);
        console.log('Chart Type:', chartControls.chartType);
        console.log('Show Volume:', chartControls.showVolume);
        
        // 清除现有系列
        if (mainSeries) {
            priceChart.removeSeries(mainSeries);
            mainSeries = null;
        }
        if (volumeSeries && !chartControls.showVolume) {
            priceChart.removeSeries(volumeSeries);
            volumeSeries = null;
        }
        
        // 排序并转换数据格式
        const sortedData = (chartData || []).slice().sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        // 根据图表类型创建系列
        if (chartControls.chartType === 'candlestick') {
            mainSeries = priceChart.addCandlestickSeries({
                upColor: '#26A69A',
                downColor: '#EF5350',
                borderVisible: false,
                wickUpColor: '#26A69A',
                wickDownColor: '#EF5350',
            });
            
            const candleData = sortedData.map(d => ({
                time: toUnixTimestamp(d.timestamp),
                open: Number(d.open),
                high: Number(d.high),
                low: Number(d.low),
                close: Number(d.close),
            }));
            
            mainSeries.setData(candleData);
            
        } else if (chartControls.chartType === 'line') {
            mainSeries = priceChart.addLineSeries({
                color: '#2962FF',
                lineWidth: 2,
                crosshairMarkerVisible: true,
                crosshairMarkerRadius: 4,
            });
            
            const lineData = sortedData.map(d => ({
                time: toUnixTimestamp(d.timestamp),
                value: Number(d.close),
            }));
            
            mainSeries.setData(lineData);
            
        } else if (chartControls.chartType === 'area') {
            mainSeries = priceChart.addAreaSeries({
                topColor: 'rgba(41, 98, 255, 0.4)',
                bottomColor: 'rgba(41, 98, 255, 0.0)',
                lineColor: '#2962FF',
                lineWidth: 2,
                crosshairMarkerVisible: true,
            });
            
            const areaData = sortedData.map(d => ({
                time: toUnixTimestamp(d.timestamp),
                value: Number(d.close),
            }));
            
            mainSeries.setData(areaData);
        }
        
        // 添加成交量 - 使用左侧Y轴,显示在底部
        if (chartControls.showVolume && !volumeSeries) {
            volumeSeries = priceChart.addHistogramSeries({
                color: '#26A69A',
                priceFormat: {
                    type: 'volume',
                },
                priceScaleId: 'left',  // 使用左侧Y轴
                scaleMargins: {
                    top: 0.75,  // 占据底部25%空间
                    bottom: 0,
                },
            });
            
            const volumeData = sortedData.map(d => ({
                time: toUnixTimestamp(d.timestamp),
                value: Number(d.volume || 0),
                color: d.close >= d.open ? 'rgba(38, 166, 154, 0.5)' : 'rgba(239, 83, 80, 0.5)',
            }));
            
            volumeSeries.setData(volumeData);
        }
        
        // 添加交易信号标记（仅蜡烛图支持）
        if (chartControls.chartType === 'candlestick' && chartTrades && chartTrades.length > 0) {
            const markers = chartTrades.map(trade => {
                const isBuy = (trade.action && trade.action.includes('买')) || 
                             trade.type === 'buy' || 
                             trade.action === '买入';
                return {
                    time: toUnixTimestamp(trade.date),
                    position: isBuy ? 'belowBar' : 'aboveBar',
                    color: isBuy ? '#26A69A' : '#EF5350',
                    shape: isBuy ? 'arrowUp' : 'arrowDown',
                    text: isBuy ? '买' : '卖',
                };
            });
            
            mainSeries.setMarkers(markers);
        }
        
        priceChart.timeScale().fitContent();
    }
    
    // 初始化图表
    updateChart();
    
    // 自适应大小
    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== chartWrapper) return;
        const { width, height } = entries[0].contentRect;
        priceChart.applyOptions({ width, height });
        priceChart.timeScale().fitContent();
    });
    
    resizeObserver.observe(chartWrapper);
    
    // 初始化时自适应内容
    priceChart.timeScale().fitContent();

    // 鼠标悬停显示详细信息
    priceChart.subscribeCrosshairMove((param) => {
        // 如果光标不在图表区域内,隐藏tooltip
        if (
            !param.time ||
            !param.point ||
            param.point.x < 0 ||
            param.point.x > chartWrapper.clientWidth ||
            param.point.y < 0 ||
            param.point.y > chartWrapper.clientHeight
        ) {
            tooltip.style.display = 'none';
            return;
        }

        // 检查seriesPrices是否存在
        if (!param.seriesPrices || !mainSeries) {
            tooltip.style.display = 'none';
            return;
        }

        // 获取主序列的价格数据
        const priceData = param.seriesPrices.get(mainSeries);
        if (!priceData) {
            tooltip.style.display = 'none';
            return;
        }

        // 获取成交量数据
        let volumeValue = 0;
        if (volumeSeries) {
            const volumeData = param.seriesPrices.get(volumeSeries);
            if (volumeData !== undefined && volumeData !== null) {
                volumeValue = typeof volumeData === 'object' ? volumeData.value : volumeData;
            }
        }

        // 获取当前日期字符串
        const currentDateStr = formatDateLabel(param.time);
        
        // 检查当前时间点是否有交易信号
        let tradeInfo = null;
        if (chartTrades && chartTrades.length > 0) {
            tradeInfo = chartTrades.find(trade => {
                if (!trade.date) return false;
                // 支持多种日期匹配方式
                return trade.date === currentDateStr || 
                       trade.date.startsWith(currentDateStr) ||
                       currentDateStr.startsWith(trade.date);
            });
            
            // 调试信息(首次查找时输出)
            if (!window._tooltipDebugShown) {
                console.log('Tooltip Debug Info:', {
                    currentDate: currentDateStr,
                    trades: chartTrades,
                    foundTrade: tradeInfo
                });
                window._tooltipDebugShown = true;
            }
        }

        // 构建tooltip HTML
        let tooltipHTML = `<div class="tooltip-date">${currentDateStr}</div>`;
        
        // 根据图表类型显示不同的价格信息
        if (chartControls.chartType === 'candlestick' && typeof priceData === 'object' && priceData.open !== undefined) {
            // K线图模式 - 显示OHLC
            const open = Number(priceData.open) || 0;
            const high = Number(priceData.high) || 0;
            const low = Number(priceData.low) || 0;
            const close = Number(priceData.close) || 0;
            
            tooltipHTML += `
                <div class="tooltip-values">
                    <span>开: <strong>${open.toFixed(2)}</strong></span>
                    <span>高: <strong>${high.toFixed(2)}</strong></span>
                    <span>低: <strong>${low.toFixed(2)}</strong></span>
                    <span>收: <strong>${close.toFixed(2)}</strong></span>
                    <span colspan="2">量: <strong>${volumeValue.toLocaleString('zh-CN')}</strong></span>
                </div>
            `;
        } else {
            // 折线图或面积图模式 - 显示单一价格
            const price = typeof priceData === 'object' ? (priceData.value || priceData.close || 0) : priceData;
            tooltipHTML += `
                <div class="tooltip-values">
                    <span>价格: <strong>${Number(price).toFixed(2)}</strong></span>
                    <span>量: <strong>${volumeValue.toLocaleString('zh-CN')}</strong></span>
                </div>
            `;
        }
        
        // 如果有交易信号,添加交易信息
        if (tradeInfo) {
            const isBuy = (tradeInfo.action && (tradeInfo.action.includes('买') || tradeInfo.action === '买入')) || 
                         tradeInfo.type === 'buy';
            const actionText = isBuy ? '买入' : '卖出';
            const actionColor = isBuy ? '#26A69A' : '#EF5350';
            
            // 获取交易价格
            let tradePrice = 0;
            if (tradeInfo.price !== undefined && tradeInfo.price !== null) {
                tradePrice = Number(tradeInfo.price);
            } else if (typeof priceData === 'object') {
                tradePrice = priceData.close || priceData.value || 0;
            } else {
                tradePrice = priceData;
            }
            
            // 获取交易数量
            const tradeQuantity = Number(tradeInfo.quantity) || Number(tradeInfo.shares) || Number(tradeInfo.amount) || 0;
            
            tooltipHTML += `
                <div class="tooltip-trade" style="margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px solid rgba(197, 203, 206, 0.2);">
                    <div style="color: ${actionColor}; font-weight: 600; margin-bottom: 0.25rem;">
                        ${actionText} @ ${tradePrice.toFixed(2)}
                    </div>
                    ${tradeQuantity > 0 ? `<div style="font-size: 0.75rem; color: #9B9B9B;">数量: ${tradeQuantity.toLocaleString('zh-CN')}</div>` : ''}
                </div>
            `;
        }
        
        // 设置tooltip内容和显示
        tooltip.innerHTML = tooltipHTML;
        tooltip.style.display = 'block';

        // 计算tooltip位置,避免溢出
        const tooltipWidth = tooltip.offsetWidth;
        const tooltipHeight = tooltip.offsetHeight;
        let tooltipX = param.point.x + 15;
        let tooltipY = param.point.y + 15;

        // 右边溢出时显示在左边
        if (tooltipX + tooltipWidth > chartWrapper.clientWidth) {
            tooltipX = param.point.x - tooltipWidth - 15;
        }
        // 下边溢出时显示在上边
        if (tooltipY + tooltipHeight > chartWrapper.clientHeight) {
            tooltipY = param.point.y - tooltipHeight - 15;
        }

        // 确保不超出左上边界
        tooltipX = Math.max(5, tooltipX);
        tooltipY = Math.max(5, tooltipY);

        tooltip.style.left = `${tooltipX}px`;
        tooltip.style.top = `${tooltipY}px`;
    });
    
    return priceChart;
}

/**
 * 创建权益曲线图表
 */
function createEquityChart(containerId, equityData) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // 清除旧图表 - 使用安全的销毁方法
    if (equityChart) {
        try {
            equityChart.remove();
        } catch (e) {
            console.warn('清除旧权益图表时出错:', e);
        }
        equityChart = null;
    }
    
    container.innerHTML = '';
    
    // 创建图表
    equityChart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        layout: {
            background: { color: '#131722' },
            textColor: '#D1D4DC',
        },
        grid: {
            vertLines: { color: '#2A2E39' },
            horzLines: { color: '#2A2E39' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#2A2E39',
            scaleMargins: {
                top: 0.05,
                bottom: 0.30,
            },
        },
        timeScale: {
            borderColor: '#2A2E39',
            timeVisible: true,
            secondsVisible: false,
            visible: true,
            minimumHeight: 40,
            tickMarkFormatter: (time) => formatDateLabel(time),
        },
    });
    
    // 添加权益曲线
    const lineSeries = equityChart.addAreaSeries({
        topColor: 'rgba(41, 98, 255, 0.4)',
        bottomColor: 'rgba(41, 98, 255, 0.0)',
        lineColor: '#2962FF',
        lineWidth: 2,
        priceLineVisible: false,
    });
    
    // 转换数据格式
    const lineData = equityData.map(d => ({
        time: new Date(d.date).getTime() / 1000,
        value: d.value,
    }));
    
    lineSeries.setData(lineData);
    
    // 自适应大小
    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) return;
        const { width, height } = entries[0].contentRect;
        equityChart.applyOptions({ width, height });
        equityChart.timeScale().fitContent();
    });
    
    resizeObserver.observe(container);
    
    // 初始化时自适应内容
    equityChart.timeScale().fitContent();
    
    return equityChart;
}

/**
 * 格式化数字为货币
 */
function formatCurrency(value) {
    return '¥' + value.toLocaleString('zh-CN', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * 格式化百分比
 */
function formatPercentage(value) {
    return value.toFixed(2) + '%';
}

/**
 * 销毁图表实例
 */
function destroyChart(chart) {
    if (chart && typeof chart.remove === 'function') {
        try {
            chart.remove();
        } catch (e) {
            console.warn('销毁图表时出错:', e);
        }
    }
}
