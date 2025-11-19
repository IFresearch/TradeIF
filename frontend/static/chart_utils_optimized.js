/**
 * TradingView Lightweight Charts 完全优化版本
 * 解决横轴显示、交易标记、自适应大小等所有问题
 */

/**
 * 创建价格图表 (K线图 + 成交量 + 技术指标 + 交易标记)
 */
function createPriceChart(containerId, data, trades = []) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`容器 ${containerId} 不存在`);
        return null;
    }
    
    container.innerHTML = '';
    
    // 创建悬浮工具提示
    const toolTip = document.createElement('div');
    toolTip.className = 'chart-tooltip';
    toolTip.style.cssText = `
        position: absolute;
        display: none;
        padding: 12px;
        background: rgba(19, 23, 34, 0.95);
        border: 1px solid #2962FF;
        border-radius: 4px;
        color: #D1D4DC;
        font-size: 12px;
        z-index: 1000;
        pointer-events: none;
        font-family: 'Trebuchet MS', Arial, sans-serif;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
        min-width: 180px;
    `;
    container.appendChild(toolTip);
    
    // 图表配置 - 完全优化
    const chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        layout: {
            background: { color: '#131722' },
            textColor: '#D1D4DC',
            fontSize: 12,
            fontFamily: "'Trebuchet MS', Arial, sans-serif",
        },
        grid: {
            vertLines: { 
                color: 'rgba(42, 46, 57, 0.5)',
                style: LightweightCharts.LineStyle.Solid,
                visible: true 
            },
            horzLines: { 
                color: 'rgba(42, 46, 57, 0.5)',
                style: LightweightCharts.LineStyle.Solid,
                visible: true 
            },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                width: 1,
                color: 'rgba(117, 134, 150, 0.8)',
                style: LightweightCharts.LineStyle.Dashed,
                labelBackgroundColor: '#2962FF',
            },
            horzLine: {
                width: 1,
                color: 'rgba(117, 134, 150, 0.8)',
                style: LightweightCharts.LineStyle.Dashed,
                labelBackgroundColor: '#2962FF',
            },
        },
        // 右侧价格轴配置
        rightPriceScale: {
            borderColor: '#2A2E39',
            scaleMargins: {
                top: 0.1,    // 顶部留10%
                bottom: 0.15, // 底部留15% (为横轴留空间)
            },
            mode: LightweightCharts.PriceScaleMode.Normal,
            autoScale: true,
            invertScale: false,
            alignLabels: true,
            borderVisible: true,
            drawTicks: true,
            scaleMargins: {
                top: 0.1,
                bottom: 0.15,
            },
        },
        // 时间轴配置 - 关键优化
        timeScale: {
            borderColor: '#2A2E39',
            timeVisible: true,
            secondsVisible: false,
            borderVisible: true,
            visible: true,
            fixLeftEdge: false,
            fixRightEdge: false,
            lockVisibleTimeRangeOnResize: false,
            rightBarStaysOnScroll: true,
            shiftVisibleRangeOnNewBar: true,
            rightOffset: 10,
            barSpacing: 6,
            minBarSpacing: 0.5,
        },
        // 交互配置
        handleScroll: {
            mouseWheel: true,
            pressedMouseMove: true,
            horzTouchDrag: true,
            vertTouchDrag: true,
        },
        handleScale: {
            axisPressedMouseMove: {
                time: true,
                price: true,
            },
            mouseWheel: true,
            pinch: true,
        },
        kineticScroll: {
            mouse: true,
            touch: true,
        },
    });
    
    // 添加K线系列
    const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26A69A',
        downColor: '#EF5350',
        borderVisible: false,
        wickUpColor: '#26A69A',
        wickDownColor: '#EF5350',
        priceFormat: {
            type: 'price',
            precision: 2,
            minMove: 0.01,
        },
    });
    
    // 转换K线数据
    const candleData = data.map(item => {
        const timeStr = item.date || item.time || item.timestamp;
        let time;
        
        // 智能时间转换
        if (typeof timeStr === 'string') {
            if (timeStr.includes('T')) {
                time = new Date(timeStr).getTime() / 1000;
            } else {
                time = timeStr; // YYYY-MM-DD格式
            }
        } else if (typeof timeStr === 'number') {
            time = timeStr > 10000000000 ? timeStr / 1000 : timeStr;
        } else {
            time = timeStr;
        }
        
        return {
            time: time,
            open: parseFloat(item.open),
            high: parseFloat(item.high),
            low: parseFloat(item.low),
            close: parseFloat(item.close),
        };
    });
    
    candlestickSeries.setData(candleData);
    
    // 添加移动平均线
    const ma5Series = chart.addLineSeries({
        color: '#FF6D00',
        lineWidth: 1.5,
        title: 'MA5',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });
    
    const ma10Series = chart.addLineSeries({
        color: '#2962FF',
        lineWidth: 1.5,
        title: 'MA10',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });
    
    const ma20Series = chart.addLineSeries({
        color: '#9C27B0',
        lineWidth: 1.5,
        title: 'MA20',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
    });
    
    // 计算并设置MA数据
    const ma5Data = calculateMA(candleData, 5);
    const ma10Data = calculateMA(candleData, 10);
    const ma20Data = calculateMA(candleData, 20);
    
    if (ma5Data.length > 0) ma5Series.setData(ma5Data);
    if (ma10Data.length > 0) ma10Series.setData(ma10Data);
    if (ma20Data.length > 0) ma20Series.setData(ma20Data);
    
    // 添加交易标记 - 完全修复
    if (trades && trades.length > 0) {
        console.log(`准备添加 ${trades.length} 个交易标记`);
        console.log('交易数据示例:', trades[0]);
        
        const markers = [];
        
        trades.forEach((trade, index) => {
            // 多种方式判断买卖
            let isBuy = false;
            
            if (trade.action) {
                isBuy = trade.action === '买入' || trade.action === 'buy' || trade.action === 'BUY';
            } else if (trade.type) {
                isBuy = trade.type === 'buy' || trade.type === 'BUY';
            } else if (trade.signal !== undefined) {
                isBuy = trade.signal > 0;
            }
            
            // 时间转换
            const tradeTimeStr = trade.date || trade.time || trade.timestamp;
            let tradeTime;
            
            if (typeof tradeTimeStr === 'string') {
                if (tradeTimeStr.includes('T')) {
                    tradeTime = new Date(tradeTimeStr).getTime() / 1000;
                } else {
                    tradeTime = tradeTimeStr;
                }
            } else if (typeof tradeTimeStr === 'number') {
                tradeTime = tradeTimeStr > 10000000000 ? tradeTimeStr / 1000 : tradeTimeStr;
            } else {
                tradeTime = tradeTimeStr;
            }
            
            markers.push({
                time: tradeTime,
                position: isBuy ? 'belowBar' : 'aboveBar',
                color: isBuy ? '#26A69A' : '#EF5350',
                shape: isBuy ? 'arrowUp' : 'arrowDown',
                text: isBuy ? '买' : '卖',
                size: 1,
            });
            
            if (index < 5) {
                console.log(`标记${index}: 时间=${tradeTime}, 类型=${isBuy ? '买入' : '卖出'}`);
            }
        });
        
        if (markers.length > 0) {
            candlestickSeries.setMarkers(markers);
            console.log(`✓ 成功添加 ${markers.length} 个交易标记`);
        }
    }
    
    // 交互式工具提示
    chart.subscribeCrosshairMove((param) => {
        if (!param.time || !param.point) {
            toolTip.style.display = 'none';
            return;
        }
        
        const price = param.seriesData.get(candlestickSeries);
        if (!price) {
            toolTip.style.display = 'none';
            return;
        }
        
        // 获取MA值
        const ma5 = param.seriesData.get(ma5Series);
        const ma10 = param.seriesData.get(ma10Series);
        const ma20 = param.seriesData.get(ma20Series);
        
        // 查找对应的成交量和交易信号
        const dateStr = typeof param.time === 'string' ? param.time : new Date(param.time * 1000).toISOString().split('T')[0];
        const dataPoint = data.find(d => {
            const dStr = d.date || d.time || d.timestamp;
            return dStr.startsWith(dateStr);
        });
        
        const volume = dataPoint ? dataPoint.volume : 0;
        
        // 查找交易信号
        const trade = trades.find(t => {
            const tStr = t.date || t.time || t.timestamp;
            return tStr.startsWith(dateStr);
        });
        
        // 构建提示内容
        let tooltipHTML = `
            <div style="margin-bottom: 6px; font-weight: bold; color: #2962FF;">${dateStr}</div>
            <div style="line-height: 1.6;">
                <div>开: <span style="color: #D1D4DC; float: right;">${price.open.toFixed(2)}</span></div>
                <div>高: <span style="color: #26A69A; float: right;">${price.high.toFixed(2)}</span></div>
                <div>低: <span style="color: #EF5350; float: right;">${price.low.toFixed(2)}</span></div>
                <div>收: <span style="color: ${price.close >= price.open ? '#26A69A' : '#EF5350'}; float: right;">${price.close.toFixed(2)}</span></div>
        `;
        
        if (volume) {
            tooltipHTML += `<div>量: <span style="color: #848E9C; float: right;">${formatVolume(volume)}</span></div>`;
        }
        
        if (ma5) {
            tooltipHTML += `<div style="margin-top: 4px;">MA5: <span style="color: #FF6D00; float: right;">${ma5.value.toFixed(2)}</span></div>`;
        }
        if (ma10) {
            tooltipHTML += `<div>MA10: <span style="color: #2962FF; float: right;">${ma10.value.toFixed(2)}</span></div>`;
        }
        if (ma20) {
            tooltipHTML += `<div>MA20: <span style="color: #9C27B0; float: right;">${ma20.value.toFixed(2)}</span></div>`;
        }
        
        if (trade) {
            const tradeAction = trade.action || (trade.signal > 0 ? '买入' : '卖出');
            const tradeColor = tradeAction === '买入' ? '#26A69A' : '#EF5350';
            tooltipHTML += `<div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #2A2E39;">
                <span style="color: ${tradeColor}; font-weight: bold;">【${tradeAction}】</span>
                <div style="font-size: 11px; color: #848E9C; margin-top: 2px;">${trade.reason || ''}</div>
            </div>`;
        }
        
        tooltipHTML += '</div>';
        toolTip.innerHTML = tooltipHTML;
        toolTip.style.display = 'block';
        
        // 定位工具提示
        const toolTipWidth = 200;
        const toolTipHeight = 180;
        const padding = 10;
        
        let left = param.point.x + padding;
        let top = param.point.y + padding;
        
        if (left > container.clientWidth - toolTipWidth) {
            left = param.point.x - toolTipWidth - padding;
        }
        if (top > container.clientHeight - toolTipHeight) {
            top = param.point.y - toolTipHeight - padding;
        }
        
        toolTip.style.left = left + 'px';
        toolTip.style.top = top + 'px';
    });
    
    // 响应式调整
    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) {
            return;
        }
        const newRect = entries[0].contentRect;
        chart.applyOptions({ 
            width: newRect.width, 
            height: newRect.height 
        });
        chart.timeScale().fitContent();
    });
    
    resizeObserver.observe(container);
    
    // 初始时适配内容
    setTimeout(() => {
        chart.timeScale().fitContent();
    }, 100);
    
    return chart;
}

/**
 * 创建权益曲线图表
 */
function createEquityChart(containerId, equityData) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`容器 ${containerId} 不存在`);
        return null;
    }
    
    container.innerHTML = '';
    
    const chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        layout: {
            background: { color: '#131722' },
            textColor: '#D1D4DC',
            fontSize: 12,
        },
        grid: {
            vertLines: { color: 'rgba(42, 46, 57, 0.5)' },
            horzLines: { color: 'rgba(42, 46, 57, 0.5)' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        rightPriceScale: {
            borderColor: '#2A2E39',
            scaleMargins: {
                top: 0.1,
                bottom: 0.15,
            },
        },
        timeScale: {
            borderColor: '#2A2E39',
            timeVisible: true,
            borderVisible: true,
            fixLeftEdge: false,
            fixRightEdge: false,
            rightOffset: 10,
            barSpacing: 6,
        },
        handleScroll: {
            mouseWheel: true,
            pressedMouseMove: true,
        },
        handleScale: {
            mouseWheel: true,
            pinch: true,
        },
    });
    
    const areaSeries = chart.addAreaSeries({
        topColor: 'rgba(41, 98, 255, 0.4)',
        bottomColor: 'rgba(41, 98, 255, 0.0)',
        lineColor: '#2962FF',
        lineWidth: 2,
        priceFormat: {
            type: 'price',
            precision: 2,
            minMove: 0.01,
        },
    });
    
    // 转换权益数据
    const formattedData = equityData.map(item => {
        const timeStr = item.date || item.time || item.timestamp;
        let time;
        
        if (typeof timeStr === 'string') {
            if (timeStr.includes('T')) {
                time = new Date(timeStr).getTime() / 1000;
            } else {
                time = timeStr;
            }
        } else if (typeof timeStr === 'number') {
            time = timeStr > 10000000000 ? timeStr / 1000 : timeStr;
        } else {
            time = timeStr;
        }
        
        return {
            time: time,
            value: parseFloat(item.equity || item.value || item.total_value || item.portfolio_value || 0),
        };
    });
    
    areaSeries.setData(formattedData);
    
    // 添加基准线
    if (formattedData.length > 0) {
        const initialValue = formattedData[0].value;
        const baselineSeries = chart.addLineSeries({
            color: 'rgba(255, 255, 255, 0.3)',
            lineWidth: 1,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            priceLineVisible: false,
            lastValueVisible: false,
        });
        
        const baselineData = formattedData.map(item => ({
            time: item.time,
            value: initialValue,
        }));
        
        baselineSeries.setData(baselineData);
    }
    
    // 响应式
    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) {
            return;
        }
        const newRect = entries[0].contentRect;
        chart.applyOptions({ 
            width: newRect.width, 
            height: newRect.height 
        });
    });
    
    resizeObserver.observe(container);
    
    setTimeout(() => {
        chart.timeScale().fitContent();
    }, 100);
    
    return chart;
}

/**
 * 计算移动平均线
 */
function calculateMA(data, period) {
    if (!data || data.length < period) {
        return [];
    }
    
    const result = [];
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        result.push({
            time: data[i].time,
            value: sum / period,
        });
    }
    
    return result;
}

/**
 * 格式化成交量
 */
function formatVolume(volume) {
    if (volume >= 100000000) {
        return (volume / 100000000).toFixed(2) + '亿';
    } else if (volume >= 10000) {
        return (volume / 10000).toFixed(2) + '万';
    } else {
        return volume.toFixed(0);
    }
}

/**
 * 格式化日期
 */
function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}
