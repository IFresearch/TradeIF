/**
 * TradingView Lightweight Charts - 完全符合官方文档规范
 * 参考: https://tradingview.github.io/lightweight-charts/docs/
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
    toolTip.style.cssText = `
        position: absolute; display: none; padding: 12px;
        background: rgba(19, 23, 34, 0.95); border: 1px solid #2962FF;
        border-radius: 4px; color: #D1D4DC; font-size: 12px;
        z-index: 1000; pointer-events: none; min-width: 200px;
        font-family: 'Trebuchet MS', Arial, sans-serif;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    `;
    container.appendChild(toolTip);
    
    // 图表配置 - 完全符合官方文档
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
                color: 'rgba(42, 46, 57, 0.6)',
                style: LightweightCharts.LineStyle.Solid,
            },
            horzLines: { 
                color: 'rgba(42, 46, 57, 0.6)',
                style: LightweightCharts.LineStyle.Solid,
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
            visible: true,
            borderVisible: true,
            borderColor: '#2A2E39',
            scaleMargins: {
                top: 0.1,
                bottom: 0.2,
            },
            mode: LightweightCharts.PriceScaleMode.Normal,
            autoScale: true,
        },
        // 左侧价格轴隐藏
        leftPriceScale: {
            visible: false,
        },
        // 时间轴配置 - 关键修复
        timeScale: {
            visible: true,
            borderVisible: true,
            borderColor: '#2A2E39',
            timeVisible: true,
            secondsVisible: false,
            rightOffset: 10,
            barSpacing: 6,
            minBarSpacing: 0.5,
            fixLeftEdge: false,
            fixRightEdge: false,
            lockVisibleTimeRangeOnResize: false,
            rightBarStaysOnScroll: true,
            shiftVisibleRangeOnNewBar: true,
        },
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
    
    console.log('原始数据条数:', data.length);
    console.log('第一条数据:', data[0]);
    
    // 数据转换 - 严格按照官方文档格式
    const candleData = [];
    data.forEach((item, index) => {
        const dateStr = item.date || item.time || item.timestamp;
        
        // 处理时间格式
        let time;
        if (typeof dateStr === 'string') {
            // 提取YYYY-MM-DD部分
            time = dateStr.split('T')[0].split(' ')[0];
        } else {
            console.warn(`数据${index}时间格式异常:`, dateStr);
            return;
        }
        
        candleData.push({
            time: time,
            open: parseFloat(item.open),
            high: parseFloat(item.high),
            low: parseFloat(item.low),
            close: parseFloat(item.close),
        });
    });
    
    console.log('转换后K线数据条数:', candleData.length);
    console.log('第一条K线数据:', candleData[0]);
    console.log('最后一条K线数据:', candleData[candleData.length - 1]);
    
    candlestickSeries.setData(candleData);
    
    // 添加移动平均线
    const ma5Series = chart.addLineSeries({
        color: '#FF6D00',
        lineWidth: 1.5,
        title: 'MA5',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
    });
    
    const ma10Series = chart.addLineSeries({
        color: '#2962FF',
        lineWidth: 1.5,
        title: 'MA10',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
    });
    
    const ma20Series = chart.addLineSeries({
        color: '#9C27B0',
        lineWidth: 1.5,
        title: 'MA20',
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
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
        console.log('========== 交易标记调试信息 ==========');
        console.log('交易记录总数:', trades.length);
        console.log('前3条交易记录:', trades.slice(0, 3));
        
        const markers = [];
        
        trades.forEach((trade, index) => {
            // 判断买卖类型
            let isBuy = false;
            if (trade.action) {
                isBuy = trade.action === '买入' || trade.action.toLowerCase() === 'buy';
            } else if (trade.type) {
                isBuy = trade.type === 'buy' || trade.type === 'BUY';
            } else if (trade.signal !== undefined) {
                isBuy = trade.signal > 0;
            }
            
            // 处理时间格式
            const tradeTimeStr = trade.date || trade.time || trade.timestamp;
            let time;
            if (typeof tradeTimeStr === 'string') {
                time = tradeTimeStr.split('T')[0].split(' ')[0];
            } else {
                console.warn(`交易${index}时间格式异常:`, tradeTimeStr);
                return;
            }
            
            const marker = {
                time: time,
                position: isBuy ? 'belowBar' : 'aboveBar',
                color: isBuy ? '#26A69A' : '#EF5350',
                shape: isBuy ? 'arrowUp' : 'arrowDown',
                text: isBuy ? '买' : '卖',
                size: 1,
            };
            
            markers.push(marker);
            
            // 调试输出前5个标记
            if (index < 5) {
                console.log(`标记${index}:`, {
                    原始时间: tradeTimeStr,
                    转换后时间: time,
                    类型: isBuy ? '买入' : '卖出',
                    action: trade.action,
                    signal: trade.signal,
                });
            }
        });
        
        console.log('生成的标记数量:', markers.length);
        console.log('前3个标记:', markers.slice(0, 3));
        
        if (markers.length > 0) {
            candlestickSeries.setMarkers(markers);
            console.log('✓ 成功设置', markers.length, '个交易标记');
        } else {
            console.error('❌ 未生成任何标记!');
        }
        
        console.log('=====================================');
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
        
        const ma5 = param.seriesData.get(ma5Series);
        const ma10 = param.seriesData.get(ma10Series);
        const ma20 = param.seriesData.get(ma20Series);
        
        // 查找对应的原始数据和交易
        const dateStr = param.time;
        const dataPoint = data.find(d => {
            const ds = d.date || d.time || d.timestamp;
            return ds.startsWith(dateStr);
        });
        const trade = trades.find(t => {
            const ts = t.date || t.time || t.timestamp;
            return ts.startsWith(dateStr);
        });
        
        // 构建提示内容
        let html = `
            <div style="margin-bottom: 8px; font-weight: bold; color: #2962FF; border-bottom: 1px solid #2A2E39; padding-bottom: 4px;">
                ${dateStr}
            </div>
            <div style="line-height: 1.8;">
                <div>开: <span style="float: right; color: #D1D4DC;">${price.open.toFixed(2)}</span></div>
                <div>高: <span style="float: right; color: #26A69A;">${price.high.toFixed(2)}</span></div>
                <div>低: <span style="float: right; color: #EF5350;">${price.low.toFixed(2)}</span></div>
                <div>收: <span style="float: right; color: ${price.close >= price.open ? '#26A69A' : '#EF5350'};">${price.close.toFixed(2)}</span></div>
        `;
        
        if (dataPoint && dataPoint.volume) {
            html += `<div style="margin-top: 4px; border-top: 1px solid #2A2E39; padding-top: 4px;">量: <span style="float: right; color: #848E9C;">${formatVolume(dataPoint.volume)}</span></div>`;
        }
        
        if (ma5 || ma10 || ma20) {
            html += `<div style="margin-top: 4px; border-top: 1px solid #2A2E39; padding-top: 4px;">`;
            if (ma5) html += `<div>MA5: <span style="float: right; color: #FF6D00;">${ma5.value.toFixed(2)}</span></div>`;
            if (ma10) html += `<div>MA10: <span style="float: right; color: #2962FF;">${ma10.value.toFixed(2)}</span></div>`;
            if (ma20) html += `<div>MA20: <span style="float: right; color: #9C27B0;">${ma20.value.toFixed(2)}</span></div>`;
            html += `</div>`;
        }
        
        if (trade) {
            const action = trade.action || (trade.signal > 0 ? '买入' : '卖出');
            const tradeColor = action === '买入' ? '#26A69A' : '#EF5350';
            html += `
                <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #2A2E39;">
                    <div style="color: ${tradeColor}; font-weight: bold;">【${action}】</div>
                    ${trade.reason ? `<div style="font-size: 11px; color: #848E9C; margin-top: 4px;">${trade.reason}</div>` : ''}
                </div>
            `;
        }
        
        html += '</div>';
        toolTip.innerHTML = html;
        toolTip.style.display = 'block';
        
        // 智能定位
        const tooltipWidth = 220;
        const tooltipHeight = 200;
        let left = param.point.x + 15;
        let top = param.point.y + 15;
        
        if (left + tooltipWidth > container.clientWidth) {
            left = param.point.x - tooltipWidth - 15;
        }
        if (top + tooltipHeight > container.clientHeight) {
            top = param.point.y - tooltipHeight - 15;
        }
        
        toolTip.style.left = Math.max(10, left) + 'px';
        toolTip.style.top = Math.max(10, top) + 'px';
    });
    
    // 响应式处理
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
    
    // 初始适配内容
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
            vertLines: { color: 'rgba(42, 46, 57, 0.6)' },
            horzLines: { color: 'rgba(42, 46, 57, 0.6)' },
        },
        rightPriceScale: {
            borderColor: '#2A2E39',
            scaleMargins: { top: 0.1, bottom: 0.2 },
        },
        timeScale: {
            borderColor: '#2A2E39',
            timeVisible: true,
            borderVisible: true,
            rightOffset: 10,
            barSpacing: 6,
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
    
    console.log('权益曲线原始数据条数:', equityData.length);
    
    const formattedData = [];
    equityData.forEach((item, index) => {
        const dateStr = item.date || item.time || item.timestamp;
        let time;
        if (typeof dateStr === 'string') {
            time = dateStr.split('T')[0].split(' ')[0];
        } else {
            console.warn(`权益数据${index}时间格式异常:`, dateStr);
            return;
        }
        
        const value = parseFloat(item.equity || item.value || item.total_value || item.portfolio_value || 0);
        
        formattedData.push({ time, value });
    });
    
    console.log('权益曲线转换后数据条数:', formattedData.length);
    
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
    new ResizeObserver(() => {
        chart.applyOptions({ 
            width: container.clientWidth, 
            height: container.clientHeight 
        });
    }).observe(container);
    
    setTimeout(() => chart.timeScale().fitContent(), 100);
    
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
