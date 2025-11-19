/**
 * TradeIF - Lightweight Charts 完全优化版本
 */

function createPriceChart(containerId, data, trades = []) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`容器 ${containerId} 不存在`);
        return null;
    }
    
    container.innerHTML = '';
    
    // 创建工具提示
    const toolTip = document.createElement('div');
    toolTip.style.cssText = `
        position: absolute; display: none; padding: 12px;
        background: rgba(19, 23, 34, 0.95); border: 1px solid #2962FF;
        border-radius: 4px; color: #D1D4DC; font-size: 12px;
        z-index: 1000; pointer-events: none; min-width: 180px;
        font-family: 'Trebuchet MS', Arial, sans-serif;
    `;
    container.appendChild(toolTip);
    
    // 图表配置
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
    
    // K线系列
    const candlestickSeries = chart.addCandlestickSeries({
        upColor: '#26A69A',
        downColor: '#EF5350',
        borderVisible: false,
        wickUpColor: '#26A69A',
        wickDownColor: '#EF5350',
    });
    
    // 转换数据 - 关键修复
    const candleData = data.map(item => {
        const dateStr = item.date || item.time || item.timestamp;
        // 直接使用YYYY-MM-DD格式字符串
        return {
            time: dateStr.split('T')[0], // 确保只取日期部分
            open: parseFloat(item.open),
            high: parseFloat(item.high),
            low: parseFloat(item.low),
            close: parseFloat(item.close),
        };
    });
    
    candlestickSeries.setData(candleData);
    
    // MA线
    const ma5Series = chart.addLineSeries({
        color: '#FF6D00', lineWidth: 1.5, priceLineVisible: false,
    });
    const ma10Series = chart.addLineSeries({
        color: '#2962FF', lineWidth: 1.5, priceLineVisible: false,
    });
    const ma20Series = chart.addLineSeries({
        color: '#9C27B0', lineWidth: 1.5, priceLineVisible: false,
    });
    
    const ma5Data = calculateMA(candleData, 5);
    const ma10Data = calculateMA(candleData, 10);
    const ma20Data = calculateMA(candleData, 20);
    
    if (ma5Data.length > 0) ma5Series.setData(ma5Data);
    if (ma10Data.length > 0) ma10Series.setData(ma10Data);
    if (ma20Data.length > 0) ma20Series.setData(ma20Data);
    
    // 交易标记 - 关键修复
    if (trades && trades.length > 0) {
        console.log(`准备添加 ${trades.length} 个交易标记`);
        
        const markers = trades.map(trade => {
            const isBuy = trade.action === '买入' || trade.type === 'buy' || trade.signal > 0;
            const dateStr = (trade.date || trade.time || trade.timestamp).split('T')[0];
            
            return {
                time: dateStr, // 使用YYYY-MM-DD格式
                position: isBuy ? 'belowBar' : 'aboveBar',
                color: isBuy ? '#26A69A' : '#EF5350',
                shape: isBuy ? 'arrowUp' : 'arrowDown',
                text: isBuy ? '买' : '卖',
            };
        });
        
        candlestickSeries.setMarkers(markers);
        console.log(`✓ 成功添加 ${markers.length} 个交易标记`);
    }
    
    // 工具提示
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
        
        const dateStr = param.time;
        const dataPoint = data.find(d => (d.date || d.time || d.timestamp).startsWith(dateStr));
        const trade = trades.find(t => (t.date || t.time || t.timestamp).startsWith(dateStr));
        
        let html = `
            <div style="margin-bottom: 6px; font-weight: bold; color: #2962FF;">${dateStr}</div>
            <div>开: ${price.open.toFixed(2)}</div>
            <div>高: <span style="color: #26A69A;">${price.high.toFixed(2)}</span></div>
            <div>低: <span style="color: #EF5350;">${price.low.toFixed(2)}</span></div>
            <div>收: <span style="color: ${price.close >= price.open ? '#26A69A' : '#EF5350'};">${price.close.toFixed(2)}</span></div>
        `;
        
        if (dataPoint && dataPoint.volume) {
            html += `<div>量: ${formatVolume(dataPoint.volume)}</div>`;
        }
        
        if (trade) {
            const action = trade.action || (trade.signal > 0 ? '买入' : '卖出');
            html += `<div style="margin-top: 6px; color: ${action === '买入' ? '#26A69A' : '#EF5350'};">【${action}】</div>`;
        }
        
        toolTip.innerHTML = html;
        toolTip.style.display = 'block';
        toolTip.style.left = Math.min(param.point.x + 10, container.clientWidth - 200) + 'px';
        toolTip.style.top = Math.min(param.point.y + 10, container.clientHeight - 150) + 'px';
    });
    
    // 响应式
    new ResizeObserver(() => {
        chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    }).observe(container);
    
    setTimeout(() => chart.timeScale().fitContent(), 100);
    return chart;
}

function createEquityChart(containerId, equityData) {
    const container = document.getElementById(containerId);
    if (!container) return null;
    
    container.innerHTML = '';
    
    const chart = LightweightCharts.createChart(container, {
        width: container.clientWidth,
        height: container.clientHeight,
        layout: { background: { color: '#131722' }, textColor: '#D1D4DC' },
        grid: { vertLines: { color: '#2A2E39' }, horzLines: { color: '#2A2E39' } },
        rightPriceScale: { borderColor: '#2A2E39', scaleMargins: { top: 0.1, bottom: 0.2 } },
        timeScale: { borderColor: '#2A2E39', timeVisible: true },
    });
    
    const areaSeries = chart.addAreaSeries({
        topColor: 'rgba(41, 98, 255, 0.4)',
        bottomColor: 'rgba(41, 98, 255, 0.0)',
        lineColor: '#2962FF',
        lineWidth: 2,
    });
    
    const formattedData = equityData.map(item => ({
        time: (item.date || item.time || item.timestamp).split('T')[0],
        value: parseFloat(item.equity || item.value || item.total_value || item.portfolio_value || 0),
    }));
    
    areaSeries.setData(formattedData);
    
    new ResizeObserver(() => {
        chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    }).observe(container);
    
    setTimeout(() => chart.timeScale().fitContent(), 100);
    return chart;
}

function calculateMA(data, period) {
    if (!data || data.length < period) return [];
    const result = [];
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        result.push({ time: data[i].time, value: sum / period });
    }
    return result;
}

function formatVolume(volume) {
    if (volume >= 100000000) return (volume / 100000000).toFixed(2) + '亿';
    if (volume >= 10000) return (volume / 10000).toFixed(2) + '万';
    return volume.toFixed(0);
}
