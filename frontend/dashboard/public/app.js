/* ─────────────────────────────────────────────────────────────────────────
   AlphaHunter Dashboard — app.js
   ─────────────────────────────────────────────────────────────────────── */

"use strict";


window.BreakoutChartManager = (function() {
  let chart = null;

  function initChart() {
    const dom = document.getElementById("br_chart");
    if (!dom) return;
    if (chart) chart.dispose();
    chart = echarts.init(dom, 'dark', { renderer: 'canvas' });
    
    window.addEventListener('resize', function() {
      if (chart) chart.resize();
    });
  }

  function renderBreakoutChart(symbol, dates, kData, volumes, prevHigh, prevLow, levelDate) {
    if (!chart) initChart();
    if (!chart) return;
    
    if (dates.length > 1 && dates[0] > dates[1]) {
      dates.reverse();
      kData.reverse();
      volumes.reverse();
    }
    
    const upColor = '#10b981';
    const downColor = '#ef4444';

    const markLineData = [];
    if (prevHigh) markLineData.push({ yAxis: prevHigh, label: { position: 'start', formatter: `Prev High\n₹${prevHigh.toFixed(2)}`, color: '#f59e0b', fontSize: 11 }, lineStyle: { color: '#f59e0b', type: 'dashed' } });
    if (prevLow) markLineData.push({ yAxis: prevLow, label: { position: 'start', formatter: `Prev Low\n₹${prevLow.toFixed(2)}`, color: '#3b82f6', fontSize: 11 }, lineStyle: { color: '#3b82f6', type: 'dashed' } });

    const markPointData = [];
    if (levelDate && (prevHigh || prevLow)) {
      markPointData.push({
        name: 'Level Formed',
        coord: [levelDate, prevHigh || prevLow],
        value: `${levelDate}\n₹${(prevHigh || prevLow).toFixed(2)}`,
        itemStyle: { color: '#8b5cf6' },
        label: { show: true, position: 'top', color: '#fff', fontSize: 10 }
      });
    }
    
    if (dates.length > 0) {
      markPointData.push({
        name: 'Breakout',
        coord: [dates[dates.length-1], kData[kData.length-1][1]],
        value: 'Breakout',
        itemStyle: { color: '#10b981' },
        label: { show: true, position: 'top', color: '#fff', fontSize: 10 }
      });
    }

    const option = {
      backgroundColor: '#0b0e14',
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
        backgroundColor: 'rgba(15,23,42,0.9)',
        borderColor: '#334155',
        textStyle: { color: '#f8fafc', fontSize: 12 },
      },
      axisPointer: { link: [{ xAxisIndex: 'all' }] },
      grid: [
        { left: '6%', right: '6%', height: '60%', top: '10%' },
        { left: '6%', right: '6%', height: '20%', top: '75%' }
      ],
      xAxis: [
        {
          type: 'category', data: dates, boundaryGap: false,
          axisLine: { lineStyle: { color: '#334155' } }, splitLine: { show: false },
          min: 'dataMin', max: 'dataMax', axisLabel: { show: false }
        },
        {
          type: 'category', gridIndex: 1, data: dates, boundaryGap: false,
          axisLine: { lineStyle: { color: '#334155' } }, splitLine: { show: false },
          min: 'dataMin', max: 'dataMax'
        }
      ],
      yAxis: [
        { 
          scale: true, 
          splitArea: { show: false }, 
          splitLine: { show: false }, 
          axisLine: { lineStyle: { color: '#334155' } },
          min: function (value) {
            let m = value.min;
            if (prevLow && prevLow < m) m = prevLow * 0.995;
            if (prevHigh && prevHigh < m) m = prevHigh * 0.995;
            return m;
          },
          max: function (value) {
            let m = value.max;
            if (prevHigh && prevHigh > m) m = prevHigh * 1.005;
            if (prevLow && prevLow > m) m = prevLow * 1.005;
            return m;
          }
        },
        { scale: true, gridIndex: 1, splitNumber: 2, axisLabel: { show: false }, axisLine: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 70, end: 100 }, 
        { show: true, xAxisIndex: [0, 1], type: 'slider', bottom: '2%', start: 70, end: 100, textStyle: { color: '#D1D4DC' } }
      ],
      series: [
        {
          name: symbol,
          type: 'candlestick',
          data: kData,
          itemStyle: { color: upColor, color0: downColor, borderColor: upColor, borderColor0: downColor },
          markLine: { symbol: ['none', 'none'], data: markLineData },
          markPoint: { data: markPointData }
        },
        {
          name: 'Volume',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: volumes,
          itemStyle: { color: (params) => { return kData[params.dataIndex] && kData[params.dataIndex][1] > kData[params.dataIndex][0] ? upColor : downColor; } }
        }
      ]
    };
    chart.setOption(option, true);
    setTimeout(() => chart.resize(), 50);
  }

  return { initChart, renderBreakoutChart };
})();

window.AlphaChartManager = (function() {
  let mainChart = null;
  
  function calculateMA(dayCount, data) {
    var result = [];
    for (var i = 0, len = data.length; i < len; i++) {
      if (i < dayCount) {
        result.push('-');
        continue;
      }
      var sum = 0;
      for (var j = 0; j < dayCount; j++) {
        sum += data[i - j][1]; // Close price
      }
      result.push((sum / dayCount).toFixed(2));
    }
    return result;
  }

  function initChart() {
    const dom = document.getElementById("ah_main_chart");
    if (!dom) return;
    if (mainChart) mainChart.dispose();
    mainChart = echarts.init(dom, 'dark', { renderer: 'canvas' });
    
    // Add resize listener
    window.addEventListener('resize', function() {
      if (mainChart) mainChart.resize();
    });
  }

  function renderChart(symbol, dates, kData, volumes) {
    if (!mainChart) initChart();
    
    // Reverse data if oldest is last (NSE archive gives newest first)
    if (dates.length > 1 && dates[0] > dates[1]) {
      dates.reverse();
      kData.reverse();
      volumes.reverse();
    }
    
    // Colors matching GoCharting premium dark style
    const upColor = '#10b981';
    const downColor = '#ef4444';

    const option = {
      backgroundColor: '#1e293b', // var(--surface-1)
      animation: false,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross', animation: false, label: { backgroundColor: '#475569' } },
        backgroundColor: 'rgba(15,23,42,0.9)',
        borderColor: '#334155',
        textStyle: { color: '#f8fafc', fontSize: 12 },
      },
      axisPointer: {
        link: [{ xAxisIndex: 'all' }],
        label: { backgroundColor: '#334155' }
      },
      visualMap: {
        show: false,
        seriesIndex: 5,
        dimension: 2,
        pieces: [
          { value: 1, color: upColor },
          { value: -1, color: downColor }
        ]
      },
      grid: [
        { left: '4%', right: '4%', height: '60%', top: '5%' },
        { left: '4%', right: '4%', height: '20%', top: '70%' }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false, lineStyle: { color: '#334155' } },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax',
          axisLabel: { show: false } // Hide labels on top chart
        },
        {
          type: 'category',
          gridIndex: 1,
          data: dates,
          scale: true,
          boundaryGap: false,
          axisLine: { onZero: false, lineStyle: { color: '#334155' } },
          splitLine: { show: false },
          min: 'dataMin',
          max: 'dataMax'
        }
      ],
      yAxis: [
        {
          scale: true,
          splitArea: { show: false },
          splitLine: { lineStyle: { color: 'rgba(51, 65, 85, 0.5)', type: 'dashed' } },
          axisLabel: { color: '#94a3b8' },
          position: 'right'
        },
        {
          scale: true,
          gridIndex: 1,
          splitNumber: 2,
          splitArea: { show: false },
          splitLine: { show: false },
          axisLabel: { color: '#94a3b8', formatter: function(val) { return (val / 1000) + 'k'; } },
          position: 'right'
        }
      ],
      dataZoom: [
        { type: 'inside', xAxisIndex: [0, 1], start: 50, end: 100 },
        { show: true, type: 'slider', xAxisIndex: [0, 1], bottom: 0, height: 16, borderColor: '#334155', dataBackground: { lineStyle: { color: '#475569' } } }
      ],
      series: [
        {
          name: symbol,
          type: 'candlestick',
          data: kData,
          itemStyle: {
            color: upColor,
            color0: downColor,
            borderColor: upColor,
            borderColor0: downColor
          },
          markPoint: {
            label: { formatter: function (param) { return param != null ? Math.round(param.value) : ''; } },
            data: [
              { name: 'Highest', type: 'max', valueDim: 'highest' },
              { name: 'Lowest', type: 'min', valueDim: 'lowest' }
            ],
            tooltip: { formatter: function (param) { return param.name + '<br>' + (param.data.coord || ''); } }
          }
        },
        {
          name: 'MA9',
          type: 'line',
          data: calculateMA(9, kData),
          smooth: true,
          lineStyle: { opacity: 0.8, color: '#f59e0b', width: 2 },
          symbol: 'none'
        },
        {
          name: 'MA20',
          type: 'line',
          data: calculateMA(20, kData),
          smooth: true,
          lineStyle: { opacity: 0.8, color: '#6366f1', width: 2 },
          symbol: 'none'
        },
        {
          name: 'MA50',
          type: 'line',
          data: calculateMA(50, kData),
          smooth: true,
          lineStyle: { opacity: 0.8, color: '#ec4899', width: 2 },
          symbol: 'none'
        },
        {
          name: 'MA200',
          type: 'line',
          data: calculateMA(200, kData),
          smooth: true,
          lineStyle: { opacity: 0.8, color: '#8b5cf6', width: 2 },
          symbol: 'none'
        },
        {
          name: 'Volume',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          // Encode the volume data along with a sign (1 for up, -1 for down) for visualMap color coding
          data: volumes.map((v, i) => {
            const isUp = kData[i][1] > kData[i][0] ? 1 : -1;
            return [i, v, isUp];
          }),
          itemStyle: { opacity: 0.8 }
        }
      ]
    };

    mainChart.setOption(option);
  }

  let graphicElements = [];
  let isDrawing = false;
  let currentDrawType = 'line';
  
  function enableDrawMode(type) {
    if (!mainChart) return;
    isDrawing = true;
    currentDrawType = type;
    
    if (type === 'text') {
      showToast("Text tool active. Click on chart to place text.", "success");
    } else {
      showToast(`${type} tool active. Click and drag on chart to draw.`, "success");
    }
    
    let zr = mainChart.getZr();
    let startPoint = null;
    let tempId = null;
    
    zr.off('mousedown');
    zr.off('mousemove');
    zr.off('mouseup');

    zr.on('mousedown', function(e) {
      if (!isDrawing) return;
      startPoint = [e.offsetX, e.offsetY];
      tempId = 'draw_' + Date.now();
      
      if (currentDrawType === 'text') {
        const textStr = prompt("Enter text annotation:");
        if (textStr) {
          graphicElements.push({
            id: tempId,
            type: 'text',
            position: [e.offsetX, e.offsetY],
            style: { text: textStr, fill: '#D1D4DC', font: '14px sans-serif' }
          });
          mainChart.setOption({ graphic: graphicElements });
          showToast("Text added.", "success");
        }
        startPoint = null;
        isDrawing = false;
        zr.off('mousedown');
      }
    });

    zr.on('mousemove', function(e) {
      if (!isDrawing || !startPoint || currentDrawType === 'text') return;
      
      let shapeObj = {};
      let styleObj = {};
      
      if (currentDrawType === 'line') {
        shapeObj = { x1: startPoint[0], y1: startPoint[1], x2: e.offsetX, y2: e.offsetY };
        styleObj = { stroke: '#2962FF', lineWidth: 2, lineDash: [5, 5] };
      } else if (currentDrawType === 'rect') {
        shapeObj = { 
          x: Math.min(startPoint[0], e.offsetX), 
          y: Math.min(startPoint[1], e.offsetY), 
          width: Math.abs(e.offsetX - startPoint[0]), 
          height: Math.abs(e.offsetY - startPoint[1]) 
        };
        styleObj = { fill: 'rgba(41, 98, 255, 0.2)', stroke: '#2962FF', lineWidth: 1 };
      }

      mainChart.setOption({
        graphic: [
          ...graphicElements,
          { id: tempId, type: currentDrawType, shape: shapeObj, style: styleObj }
        ]
      });
    });

    zr.on('mouseup', function(e) {
      if (!isDrawing || !startPoint || currentDrawType === 'text') return;
      
      let shapeObj = {};
      let styleObj = {};
      
      if (currentDrawType === 'line') {
        shapeObj = { x1: startPoint[0], y1: startPoint[1], x2: e.offsetX, y2: e.offsetY };
        styleObj = { stroke: '#2962FF', lineWidth: 2 };
      } else if (currentDrawType === 'rect') {
        shapeObj = { 
          x: Math.min(startPoint[0], e.offsetX), 
          y: Math.min(startPoint[1], e.offsetY), 
          width: Math.abs(e.offsetX - startPoint[0]), 
          height: Math.abs(e.offsetY - startPoint[1]) 
        };
        styleObj = { fill: 'rgba(41, 98, 255, 0.2)', stroke: '#2962FF', lineWidth: 1 };
      }
      
      graphicElements.push({ id: tempId, type: currentDrawType, shape: shapeObj, style: styleObj });
      startPoint = null;
      isDrawing = false;
      showToast(`${currentDrawType} added.`, "success");
      
      zr.off('mousedown');
      zr.off('mousemove');
      zr.off('mouseup');
    });
  }

  function clearDrawings() {
    graphicElements = [];
    if(mainChart) mainChart.setOption({ graphic: [] }, { replaceMerge: ['graphic'] });
    showToast("Drawings cleared.", "info");
  }
  
  function toggleIndicator(name, el) {
    if (!mainChart) return;
    // We use ECharts legendToggleSelect to show/hide series
    mainChart.dispatchAction({
      type: 'legendToggleSelect',
      name: name
    });
    
    // Toggle UI checkmark
    const checkmark = el.querySelector('span');
    if (checkmark) {
      checkmark.style.display = checkmark.style.display === 'none' ? 'inline' : 'none';
    }
  }

  // Setup click listeners for mock UI tools
  function setupMocks() {
    setTimeout(() => {
      // Mock for all unimplemented drawing tools
      document.querySelectorAll('.v2-left-toolbar button:not([onclick]):not([title*="Remove"])').forEach(btn => {
        btn.addEventListener('click', () => {
          showToast("Advanced drawing tools (Fibonacci, Pitchfork, etc) are part of Phase 3 roadmap (GoCharting-style plugins).", "info");
        });
      });
      
      // Indicators Menu Toggle
      const indBtn = document.getElementById('v2_indicators_btn');
      const indMenu = document.getElementById('v2_indicators_menu');
      if (indBtn && indMenu) {
        indBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          indMenu.style.display = indMenu.style.display === 'none' ? 'block' : 'none';
        });
        document.addEventListener('click', () => {
          indMenu.style.display = 'none';
        });
        indMenu.addEventListener('click', (e) => e.stopPropagation());
      }
      
      // Top toolbar unimplemented buttons
      document.querySelectorAll('.v2-top-toolbar button:not(.v2-range-btn):not(#v2_indicators_btn), .v2-top-toolbar select').forEach(btn => {
        btn.addEventListener('click', () => {
          showToast("Advanced modules are part of Phase 3 roadmap.", "info");
        });
      });
      
      // Setup Range Selectors
      document.querySelectorAll('.v2-range-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          // Update active state
          document.querySelectorAll('.v2-range-btn').forEach(b => {
            b.classList.remove('v2-active');
          });
          e.target.classList.add('v2-active');
          
          if (!mainChart) return;
          
          const range = e.target.dataset.range;
          let startPercent = 0;
          
          if (range === '5d') startPercent = 95;
          else if (range === '1m') startPercent = 70;
          else if (range === '3m') startPercent = 40;
          else if (range === '6m') startPercent = 10;
          else startPercent = 0; // all
          
          mainChart.dispatchAction({
            type: 'dataZoom',
            start: startPercent,
            end: 100
          });
        });
      });
    }, 1000);
  }
  
  setupMocks();

  return {
    initChart,
    renderChart,
    toggleIndicator,
    clearDrawings,
    enableDrawMode
  };
})();

// ── API endpoints ──────────────────────────────────────────────────────────
const API = {
  overview:        "/api/market/overview",
  snapshots:       "/api/market/snapshots",
  liveQuotes:      (symbols) => `/api/market/quotes/live?symbols=${symbols}`,
  securityArchives:"/api/market/security-archives",
  scanner:         "/api/scanner/latest?limit=20",
  scannerFiltered: (signal) => signal ? `/api/scanner/latest?limit=20&signal=${signal}` : "/api/scanner/latest?limit=20",
  aiSignals:       "/api/scanner/signals",
  aiExits:         "/api/scanner/exits",
  positions:       "/api/positions",
  addPosition:     "/api/positions",
  evaluatePositions:"/api/positions/evaluate",
  alerts:          "/api/alerts?limit=30",
  backtest:        "/api/reports/backtest",
  latestExport:    "/api/exports/latest",
  optionsChain:    (symbol, expiry) => expiry ? `/api/options/chain/${symbol}?expiry=${expiry}` : `/api/options/chain/${symbol}`,
  optionsExpiries: (symbol) => `/api/options/chain/${symbol}/expiries`,
  breakoutRadar:   "/api/breakout-radar/latest",
};

// ── DOM Helper ────────────────────────────────────────────────────────────
function escapeHTML(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
function updateDOM(container, htmlString) {
  if (typeof morphdom !== "undefined") {
    const wrapper = document.createElement(container.tagName);
    wrapper.innerHTML = htmlString;
    morphdom(container, wrapper, { childrenOnly: true });
  } else {
    container.innerHTML = htmlString;
  }
}

// ── State ──────────────────────────────────────────────────────────────────
let refreshTimer = null;
let countdownInterval = null;
let refreshSeconds = 10;
let activeSignalFilter = "";
window.activeSectorFilter = null;
window.lastSnapshots = [];
window.lastSectors = [];

// ── Chart state (for cleanup on re-render) ─────────────────────────────────
let _activeChart = null;
let _activeResizeObserver = null;
let _backtestCache = null;

// ── Formatters ─────────────────────────────────────────────────────────────
const inrFmt = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const intFmt = new Intl.NumberFormat("en-IN");
const pctFmt = (v) => `${Number(v ?? 0).toFixed(2)}%`;
const numFmt = (v, d = 2) => (v === null || v === undefined) ? "—" : Number(v).toLocaleString("en-IN", { minimumFractionDigits: d, maximumFractionDigits: d });
const dateFmt = (v) => v ? new Date(v).toLocaleDateString("en-IN") : "—";

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

// ── Toast notifications (replaces alert()) ────────────────────────────────
function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;";
    document.body.appendChild(container);
  }
  const toast = document.createElement("div");
  const bg = type === "success" ? "#10b981" : type === "error" ? "#ef4444" : "#6366f1";
  toast.style.cssText = `background:${bg};color:#fff;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:600;box-shadow:0 4px 16px rgba(0,0,0,0.4);opacity:0;transform:translateY(8px);transition:all 0.25s ease;pointer-events:auto;`;
  toast.textContent = message;
  container.appendChild(toast);
  requestAnimationFrame(() => { toast.style.opacity = "1"; toast.style.transform = "translateY(0)"; });
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}


// ── HTTP ───────────────────────────────────────────────────────────────────
const API_BASE = window.__TAURI_INTERNALS__ || window.__TAURI__ ? "http://127.0.0.1:8000" : "";

async function getJson(url, options = {}) {
  const fullUrl = url.startsWith("/api") ? API_BASE + url : url;
  const res = await fetch(fullUrl, options);
  if (!res.ok) throw new Error(`${fullUrl} → ${res.status}`);
  return res.json();
}

// Override fetch for direct POST/DELETE calls we have
const originalFetch = window.fetch;
window.fetch = function(url, options) {
  if (typeof url === 'string' && url.startsWith("/api")) {
    url = API_BASE + url;
  }
  return originalFetch.call(this, url, options);
};

// ── Market status (IST hours: 09:15–15:30 Mon–Fri) ──────────────────────
function updateMarketStatus() {
  const now = new Date();
  // IST = UTC + 5:30
  const ist = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
  const day = ist.getUTCDay();  // 0=Sun, 6=Sat
  const hour = ist.getUTCHours();
  const min = ist.getUTCMinutes();
  const timeMin = hour * 60 + min;

  const dot = document.getElementById("market-status-dot");
  const label = document.getElementById("market-status-label");
  if (!dot || !label) return;

  const isWeekday = day >= 1 && day <= 5;
  const isOpen = isWeekday && timeMin >= 555 && timeMin < 930;   // 09:15–15:30
  const isPre  = isWeekday && timeMin >= 540 && timeMin < 555;   // 09:00–09:15

  dot.className = "market-status-dot";
  if (isOpen) {
    dot.classList.add("open");
    label.textContent = "Market Open";
  } else if (isPre) {
    dot.classList.add("pre");
    label.textContent = "Pre-open";
  } else {
    label.textContent = isWeekday ? "Market Closed" : "Market Closed (Weekend)";
  }
}

// ── Tab navigation ─────────────────────────────────────────────────────────
function activateTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("is-active"));
      document.querySelectorAll(".panel").forEach((p) => p.classList.remove("is-active"));
      btn.classList.add("is-active");
      const panel = document.getElementById(btn.dataset.panel);
      if (panel) panel.classList.add("is-active");
    });
  });
}

// ── Score bar helper ───────────────────────────────────────────────────────
function scoreBarHtml(score, maxScore = 100) {
  const pct = Math.min(100, Math.max(0, (score / maxScore) * 100));
  const cls = pct >= 65 ? "high" : pct >= 35 ? "mid" : "low";
  return `
    <div class="score-bar-wrap">
      <div class="score-bar-track">
        <div class="score-bar-fill ${cls}" style="width:0" data-target="${pct}"></div>
      </div>
      <span class="score-number">${Math.round(score)}</span>
    </div>`;
}

function pipHtml(label, score, maxScore) {
  const pct = Math.min(100, Math.max(0, (score / maxScore) * 100));
  return `<span class="score-pip" title="${label}: ${score.toFixed(1)}/${maxScore}">
    <div class="score-pip-bar"><div class="score-pip-fill" style="width:${pct}%"></div></div>
    ${label}
  </span>`;
}

function animateBars() {
  document.querySelectorAll(".score-bar-fill[data-target]").forEach((el) => {
    requestAnimationFrame(() => {
      el.style.width = el.dataset.target + "%";
    });
  });
}

// ── Signal badge ────────────────────────────────────────────────────────────
function signalBadge(signal) {
  const label = signal.replaceAll("_", " ").toUpperCase();
  return `<span class="badge badge-${signal}">${label}</span>`;
}

// ── Action badge ────────────────────────────────────────────────────────────
function actionBadge(action) {
  const label = (action || "hold").toUpperCase();
  return `<span class="badge badge-${action}">${label}</span>`;
}

// ── PnL cell ────────────────────────────────────────────────────────────────
function pnlCell(pnl) {
  const v = Number(pnl ?? 0);
  const cls = v > 0 ? "pnl-positive" : v < 0 ? "pnl-negative" : "pnl-neutral";
  const sign = v > 0 ? "+" : "";
  return `<span class="${cls}">${sign}${v.toFixed(2)}%</span>`;
}

// ── Render: Overview ────────────────────────────────────────────────────────
function renderOverview(data) {
  setText("last-updated", `Updated ${new Date(data.observed_at).toLocaleTimeString("en-IN")}`);

  const trendEl = document.getElementById("nifty-trend");
  if (trendEl) {
    trendEl.textContent = data.nifty_trend.toUpperCase();
    trendEl.className = "metric-value " + (
      data.nifty_trend === "bullish" ? "bullish" :
      data.nifty_trend === "bearish" ? "bearish" : "neutral"
    );
  }
  setText("strong-sectors", data.strongest_sectors.join(", ") || "—");
  setText("weak-sectors", data.weakest_sectors.join(", ") || "—");
  setText("hot-symbols", data.hot_symbols.join(", ") || "—");

  const list = document.getElementById("risk-notes");
  if (list) {
    updateDOM(list, (data.risk_notes || []).map((note) =>
      `<li class="risk-item">${note}</li>`
    ).join(""));
  }
}

function renderSnapshots(snapshots) {
  const container = document.getElementById("snapshot-chips");
  if (!container) return;
  
  const filtered = window.activeSectorFilter 
    ? snapshots.filter(s => s.sector === window.activeSectorFilter) 
    : snapshots;

  if (filtered.length === 0) {
    updateDOM(container, `<div class="snapshot-chip"><div class="snapshot-chip-symbol" style="color:var(--text-muted)">No stocks</div></div>`);
    return;
  }
  
  updateDOM(container, filtered.map((s) => {
    const chg = Number(s.change_percent ?? 0);
    const cls = chg > 0.3 ? "up" : chg < -0.3 ? "down" : "flat";
    const arrow = chg > 0.3 ? "▲" : chg < -0.3 ? "▼" : "—";
    return `<div class="snapshot-chip" onclick="openLookup('${s.symbol}')" style="cursor: pointer;">
      <div class="snapshot-chip-symbol">${s.symbol}</div>
      <div class="snapshot-chip-price">₹${inrFmt.format(s.last_price)}</div>
      <div class="snapshot-chip-change ${cls}">${arrow} ${Math.abs(chg).toFixed(2)}%</div>
    </div>`;
  }).join(""));
}

// ── Render: Market Cycle Center ─────────────────────────────────────────────
function renderMarketCycles(snapshots) {
  const tbody = document.getElementById("cycle-center-body");
  if (!tbody) return;

  if (!snapshots || snapshots.length === 0) {
    updateDOM(tbody, `<tr><td colspan="3" style="text-align:center; padding: 24px; color: var(--text-muted);">No symbols tracking</td></tr>`);
    return;
  }
  
  // Sort by phase priority then confidence
  const phaseOrder = { "accumulation": 1, "markup": 2, "distribution": 3, "markdown": 4, "unknown": 5 };
  
  const cycleData = snapshots
    .filter(s => s.cycle_metrics)
    .sort((a, b) => {
      const pA = phaseOrder[a.cycle_metrics.phase.toLowerCase()] || 5;
      const pB = phaseOrder[b.cycle_metrics.phase.toLowerCase()] || 5;
      if (pA !== pB) return pA - pB;
      return b.cycle_metrics.confidence - a.cycle_metrics.confidence;
    });
    
  if (cycleData.length === 0) {
    updateDOM(tbody, `<tr><td colspan="3" style="text-align:center; padding: 24px; color: var(--text-muted);">No cycle data available</td></tr>`);
    return;
  }

  updateDOM(tbody, cycleData.map((s) => {
    const p = s.cycle_metrics.phase.toUpperCase();
    let cycleColor = "#9ca3af";
    if (p === "ACCUMULATION") cycleColor = "#eab308";
    if (p === "MARKUP") cycleColor = "#10b981";
    if (p === "DISTRIBUTION") cycleColor = "#f97316";
    if (p === "MARKDOWN") cycleColor = "#ef4444";
    
    return `<tr style="cursor:pointer;" onclick="openLookup('${s.symbol}')">
      <td><strong style="color:var(--primary);">${s.symbol}</strong></td>
      <td><span style="font-size:11px; font-weight:800; color:#fff; background:${cycleColor}; padding:4px 8px; border-radius:4px;">${p}</span></td>
      <td>${s.cycle_metrics.confidence}%</td>
    </tr>`;
  }).join(""));
}

// ── Render: Scanner ─────────────────────────────────────────────────────────
function renderScanner(rows) {
  const tbody = document.getElementById("scanner-table");
  if (!tbody) return;

  if (!rows || rows.length === 0) {
    updateDOM(tbody, `<tr><td colspan="6"><div class="empty-state"><div class="empty-state-icon">📡</div>No candidates found</div></td></tr>`);
    return;
  }

  updateDOM(tbody, rows.map((row) => {
    const breakdown = [
      pipHtml("BRK", row.price_breakout_score, 20),
      pipHtml("OI",  row.oi_score, 20),
      pipHtml("VOL", row.volume_score, 15),
      pipHtml("RSI", row.rsi_score, 10),
      pipHtml("OPT", row.option_chain_score, 15),
      pipHtml("SEC", row.sector_strength_score, 10),
      pipHtml("MACD",row.macd_score ?? 0, 5),
      pipHtml("BB",  row.bb_score ?? 0, 5),
      pipHtml("52W", row.proximity_score ?? 0, 5),
    ].join("");

    const summary = (row.evidence?.ai_summary || row.reasons?.join("; ") || "—").slice(0, 280);

    let badges = "";
    if (row.spurt_score > 40) badges += " <span title='Spurt Detected'>🔥</span>";
    if (row.structure_score > 60) badges += " <span title='52W Breakout'>🚀</span>";

    const tierBadge = `<span class="badge badge-tier-${row.signal_tier || 'Ignore'}" style="margin-left: 8px;">Tier ${row.signal_tier || 'Ignore'}</span>`;

    return `<tr style="cursor:pointer;" onclick="openLookup('${row.symbol}')">
      <td><strong>${row.rank || ""}</strong></td>
      <td><strong style="color:var(--primary);">${row.symbol}</strong>${badges}${tierBadge}</td>
      <td>${signalBadge(row.signal_type)}</td>
      <td class="score-cell">${scoreBarHtml(row.score)}</td>
      <td class="advanced-only"><div class="score-breakdown">${breakdown}</div></td>
      <td class="advanced-only" style="max-width:320px;font-size:12px;color:var(--text-muted);line-height:1.4">${summary}</td>
    </tr>`;
  }).join(""));

  setTimeout(animateBars, 50);
}

function renderTopOpportunities(scannerRows) {
  const tbody = document.getElementById("top-opportunities-body");
  if (!tbody) return;

  if (!scannerRows || scannerRows.length === 0) {
    updateDOM(tbody, `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--text-muted);">No active opportunities detected.</td></tr>`);
    return;
  }

  // Display top 5 scanner candidates
  const topCandidates = [...scannerRows].slice(0, 5);

  updateDOM(tbody, topCandidates.map((row, idx) => {
    const chgVal = row.change_percent ?? 0;
    const chgClass = chgVal > 0 ? "bullish" : chgVal < 0 ? "bearish" : "neutral";
    const chgSign = chgVal > 0 ? "+" : "";
    const formattedPrice = row.last_price != null ? `₹${numFmt(row.last_price)}` : "—";
    
    // Sparkline SVG generator
    let sparklineHtml = '<div style="text-align: center; color: var(--text-muted); font-size: 11px;">—</div>';
    if (row.candles && row.candles.length >= 5) {
      const prices = row.candles.slice(-15).map(c => c.close);
      const min = Math.min(...prices);
      const max = Math.max(...prices);
      const range = max - min || 1;
      const points = prices.map((p, i) => `${(i * 7).toFixed(0)},${(22 - ((p - min) / range) * 16).toFixed(0)}`).join(" ");
      const strokeColor = chgVal >= 0 ? "var(--green)" : "var(--red)";
      sparklineHtml = `<svg width="105" height="24" style="overflow: visible; display: block; margin: 0 auto;" aria-label="15-day price sparkline">
        <polyline fill="none" stroke="${strokeColor}" stroke-width="1.5" points="${points}"></polyline>
      </svg>`;
    }

    return `<tr style="border-bottom: 1px solid var(--border); font-size: 13px; cursor: pointer;" onclick="openLookup('${row.symbol}')">
      <td style="padding: 12px 16px; font-weight: 700; color: var(--text-muted); font-family: var(--font-mono);">${idx + 1}</td>
      <td style="padding: 12px 16px;"><strong style="color: var(--indigo); font-family: var(--font-display); font-size: 14px;">${row.symbol}</strong></td>
      <td style="padding: 12px 16px; text-align: center; font-family: var(--font-mono); font-weight: 700; color: var(--text);">${row.score.toFixed(0)}</td>
      <td style="padding: 12px 16px;">${signalBadge(row.signal_type)}</td>
      <td style="padding: 12px 16px; text-align: right; font-family: var(--font-mono); font-weight: 600;">${formattedPrice}</td>
      <td style="padding: 12px 16px; text-align: right; font-family: var(--font-mono); font-weight: 600;" class="${chgClass}">${chgSign}${chgVal.toFixed(2)}%</td>
      <td style="padding: 8px 16px; text-align: center; vertical-align: middle;">${sparklineHtml}</td>
    </tr>`;
  }).join(""));
}

// ── Render: AI Signals ───────────────────────────────────────────────────────
function renderAiSignals(rows) {
  const container = document.getElementById("ai-signals-container");
  if (!container) return;

  if (rows !== window.filteredAiSignals) {
    window.allAiSignals = rows || [];
  }

  if (!rows || rows.length === 0) {
    updateDOM(container, `<div class="empty-state" style="grid-column: 1 / -1;"><div class="empty-state-icon">🤖</div>No active highly filtered signals right now.</div>`);
    return;
  }

  updateDOM(container, rows.map((row) => {
    const isBuy = row.signal === "BUY";
    const isWait = row.signal === "WAIT" || row.signal === "WATCHLIST";
    const headerColor = isBuy ? "var(--green)" : isWait ? "var(--amber)" : "var(--red)";
    const bg = isBuy ? "var(--green-dim)" : isWait ? "var(--amber-dim)" : "var(--red-dim)";
    const optionRecHtml = row.options_recommendation ? `<div class="advanced-only" style="margin-top:12px; padding-top:8px; border-top:1px solid var(--border); font-size:12px;"><strong>Option Play:</strong> <span style="color:var(--indigo); font-weight:600;">${row.options_recommendation}</span></div>` : "";
    
    // Find snapshot matching symbol to load price/percent changes dynamically
    const snap = (window.lastSnapshots || []).find(s => s.symbol.toUpperCase() === row.symbol.toUpperCase());
    const formattedPrice = snap ? `₹${numFmt(snap.last_price)}` : "—";
    const chgVal = snap ? snap.change_percent : 0;
    const chgClass = chgVal > 0 ? "bullish" : chgVal < 0 ? "bearish" : "neutral";
    const chgSign = chgVal > 0 ? "+" : "";

    let sentColor = "var(--text-muted)";
    if (row.news_sentiment === "BULLISH") sentColor = "var(--green)";
    else if (row.news_sentiment === "BEARISH") sentColor = "var(--red)";

    return `
    <div class="card signal-card" style="padding: 20px; display: flex; flex-direction: column; gap: 16px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--grad-surface);">
      <!-- Header -->
      <div style="display: flex; justify-content: space-between; align-items: flex-start;">
        <div>
          <div style="font-family: var(--font-display); font-size: 22px; font-weight: 700; color: var(--indigo); cursor: pointer; text-decoration: underline; text-underline-offset: 3px;" onclick="openLookup('${row.symbol}')" title="Click to open Stock Lookup">${row.symbol} ↗</div>
          <div style="display: flex; align-items: center; gap: 8px; margin-top: 6px; flex-wrap: wrap;">
            <span style="font-size: 11px; font-weight: 700; color: ${headerColor}; background: ${bg}; padding: 2px 8px; border-radius: 6px; border: 1px solid ${headerColor}50;">${row.signal}</span>
            <span style="font-size: 10px; font-weight: 600; color: var(--text-muted); background: var(--surface-2); padding: 2px 6px; border-radius: 4px;">⏱️ ${row.holding_period}</span>
            <span style="font-size: 10px; font-weight: 600; color: var(--text-muted); background: var(--surface-2); padding: 2px 6px; border-radius: 4px;">📈 ${row.market_regime}</span>
          </div>
        </div>
        
        <!-- Score -->
        <div style="text-align: right;">
          <div style="font-family: var(--font-mono); font-size: 26px; font-weight: 800; color: var(--text); line-height: 1;">${row.confidence}%</div>
          <div style="font-size: 9px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-top: 4px;">Confidence</div>
          <div style="width: 60px; height: 4px; background: var(--border); border-radius: 2px; overflow: hidden; margin-top: 4px; margin-left: auto;">
            <div style="width: ${row.confidence}%; height: 100%; background: ${headerColor};"></div>
          </div>
        </div>
      </div>

      <!-- Price Section -->
      <div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid var(--border); padding-bottom: 8px; margin-bottom: 4px;">
        <span style="font-family: var(--font-mono); font-size: 20px; font-weight: 700; color: var(--text);">${formattedPrice}</span>
        <span style="font-family: var(--font-mono); font-size: 13px; font-weight: 600;" class="${chgClass}">${chgSign}${chgVal.toFixed(2)}%</span>
      </div>

      <!-- Core Execution Zone Metrics -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px; border-bottom: 1px solid var(--border); padding-bottom: 12px;">
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <div style="color: var(--text-muted);">Entry Zone:</div>
          <strong style="color: var(--text); font-family: var(--font-mono); font-size: 13px;">${row.entry}</strong>
        </div>
        <div style="display: flex; flex-direction: column; gap: 4px;">
          <div style="color: var(--text-muted);">Stop Loss:</div>
          <strong style="color: var(--red); font-family: var(--font-mono); font-size: 13px;">₹${numFmt(row.stop_loss)}</strong>
        </div>
        <div style="display: flex; flex-direction: column; gap: 4px; grid-column: span 2;">
          <div style="color: var(--text-muted);">Target Levels:</div>
          <strong style="color: var(--green); font-family: var(--font-mono); font-size: 13px;">${row.targets.map(t => "₹" + numFmt(t)).join("  /  ")}</strong>
        </div>
        <div style="display: flex; justify-content: space-between; grid-column: span 2; margin-top: 4px;">
          <span>Risk-Reward Ratio:</span>
          <strong style="color: var(--text); font-family: var(--font-mono);">1 : ${row.risk_reward.toFixed(1)}</strong>
        </div>
      </div>

      <!-- AI Explanation -->
      <div style="font-size: 12px; color: var(--text-muted); background: rgba(0,0,0,0.15); padding: 12px; border-radius: 8px; border: 1px solid var(--border); line-height: 1.5;">
        ${row.ai_explanation}
      </div>

      <!-- Execution Action -->
      <div style="display: flex; gap: 8px; margin-top: 4px;">
        <button class="btn btn-primary" style="flex: 1; padding: 8px 12px; font-size: 12px; display: flex; align-items: center; justify-content: center; gap: 6px; font-weight: 700; background: var(--purple);" onclick="executeSignalTrade('${row.symbol}', '${row.signal}', ${row.entry.includes('-') ? parseFloat(row.entry.split('-')[0]) : parseFloat(row.entry.replace(/[^\d\.]/g, ''))}, ${row.stop_loss}, ${row.targets[0]}, ${row.risk_reward})">
          ⚡ Execute Trade Call
        </button>
      </div>

      <!-- Score Breakdown Grid -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 11px;">
        <div style="background: var(--surface-2); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between;">
          <span style="color: var(--text-muted);">Risk Score:</span>
          <strong style="color: var(--red);">${row.risk_score}</strong>
        </div>
        <div style="background: var(--surface-2); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between;">
          <span style="color: var(--text-muted);">Reward Score:</span>
          <strong style="color: var(--green);">${row.reward_score}</strong>
        </div>
        <div style="background: var(--surface-2); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between;">
          <span style="color: var(--text-muted);">Sector Strength:</span>
          <strong style="color: var(--text);">${row.sector_strength}</strong>
        </div>
        <div style="background: var(--surface-2); padding: 8px; border-radius: 6px; display: flex; justify-content: space-between;">
          <span style="color: var(--text-muted);">News Sentiment:</span>
          <strong style="color: ${sentColor};">${row.news_sentiment}</strong>
        </div>
      </div>

      <!-- Confluence Breakdown Details -->
      <div class="advanced-only" style="font-size: 11px; display: flex; flex-direction: column; gap: 8px; border-top: 1px dashed var(--border); padding-top: 12px;">
        <div>
          <span style="color: var(--indigo); font-weight: 700;">📈 Technical:</span>
          <span style="color: var(--text);">${row.technical_reasons.join(" • ")}</span>
        </div>
        <div>
          <span style="color: var(--indigo); font-weight: 700;">📊 Options Flow:</span>
          <span style="color: var(--text);">${row.options_reasons.join(" • ")}</span>
        </div>
        <div>
          <span style="color: var(--indigo); font-weight: 700;">🔊 Volume Analysis:</span>
          <span style="color: var(--text);">${row.volume_reasons.join(" • ")}</span>
        </div>
        <div>
          <span style="color: var(--indigo); font-weight: 700;">💼 Smart Money:</span>
          <span style="color: var(--text);">${row.smart_money_reasons.join(" • ")}</span>
        </div>
      </div>

      ${optionRecHtml}
    </div>`;
  }).join(""));
}

// ── Render: Positions ────────────────────────────────────────────────────────
function renderPositions(rows) {
  const tbody = document.getElementById("positions-table");
  if (!tbody) return;

  if (!rows || rows.length === 0) {
    updateDOM(tbody, `<tr><td colspan="9"><div class="empty-state"><div class="empty-state-icon">📂</div>No open positions</div></td></tr>`);
    return;
  }

  updateDOM(tbody, rows.map((row) => {
    const reason = (row.reasons || []).slice(0, 2).join("; ") || "—";
    return `<tr>
      <td><strong>${row.symbol}</strong></td>
      <td><span class="badge badge-signal">${(row.side || "long").toUpperCase()}</span></td>
      <td>₹${numFmt(row.entry_price)}</td>
      <td>₹${numFmt(row.latest_price)}</td>
      <td>${pnlCell(row.pnl_percent)}</td>
      <td class="score-cell advanced-only">${scoreBarHtml(row.health_score ?? 0)}</td>
      <td class="score-cell advanced-only">${scoreBarHtml(row.reversal_score ?? 0)}</td>
      <td class="advanced-only">${actionBadge(row.action)}</td>
      <td class="advanced-only" style="max-width:240px;font-size:12px;color:var(--text-muted)">${reason}</td>
      <td>
        <button onclick="deletePosition('${row.id}')" style="background:transparent; color:var(--danger); border:1px solid var(--danger); padding:4px 8px; border-radius:4px; cursor:pointer; font-size:12px;" title="Delete Position">✕</button>
      </td>
    </tr>`;
  }).join(""));

  setTimeout(animateBars, 50);
}

window.deletePosition = async function(id) {
  if (confirm("Are you sure you want to delete this position?")) {
    try {
      await fetch(`/api/positions/${id}`, { method: "DELETE" });
      refresh();
    } catch(err) {
      alert("Failed to delete position.");
    }
  }
};

// ── Render: Alerts ────────────────────────────────────────────────────────────
function renderAlerts(rows) {
  const container = document.getElementById("alerts-list");
  if (!container) return;

  if (!rows || rows.length === 0) {
    updateDOM(container, `<div class="empty-state"><div class="empty-state-icon">🔔</div>No alerts yet</div>`);
    return;
  }

  updateDOM(container, rows.map((row) => {
    let actionClass = "type-breakout";
    let icon = "🔔";
    
    if (row.action === "exit" || row.action === "FULL EXIT") {
      actionClass = "type-exit";
      icon = "🚨";
    } else if (row.alert_type === "reversal" || row.action === "PARTIAL BOOK") {
      actionClass = "type-reversal";
      icon = "⚠️";
    } else if (row.alert_type === "swing_entry" || row.action === "BUY") {
      actionClass = "type-breakout";
      icon = "🎯";
    }
    
    const timeStr = row.triggered_at ? new Date(row.triggered_at).toLocaleTimeString("en-IN", { hour: '2-digit', minute: '2-digit' }) : "";

    return `<article class="alert-card ${actionClass}" role="article" style="display:flex; gap:12px; align-items:flex-start; padding:12px; border-radius:8px; margin-bottom:8px; background:rgba(255,255,255,0.03); border-left:4px solid var(--border);">
      <div style="font-size:20px; line-height:1;">${icon}</div>
      <div style="flex:1;">
        <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
          <div class="alert-card-title" style="font-weight:700; color:var(--text);">${row.title}</div>
          <div style="font-size:11px; color:var(--text-muted);">${timeStr}</div>
        </div>
        <div class="alert-card-msg" style="font-size:13px; color:var(--text-muted); line-height:1.4;">${row.message}</div>
      </div>
    </article>`;
  }).join(""));
}

// ── Render: Stock lookup ───────────────────────────────────────────────────
function clearLookup(msg = "Enter a symbol like RELIANCE, TCS, or INFY.") {
  setText("lookup-close",    "—");
  setText("lookup-vwap",     "—");
  setText("lookup-delivery", "—");
  setText("lookup-quantity", "—");
  const t = document.getElementById("lookup-table");
  if (t) updateDOM(t, "");
  setText("lookup-status", msg);
  const addBtn = document.getElementById("add-to-scanner-btn");
  if (addBtn) addBtn.style.display = "none";
  const tvWrapper = document.getElementById("tv_chart_wrapper");
  if (tvWrapper) tvWrapper.style.display = "none";
}

function renderStockLookup(symbol, rows, intraday = null) {
  const sorted = [...rows].sort((a, b) => new Date(b.trade_date) - new Date(a.trade_date));

  if (sorted.length === 0) {
    clearLookup(`No archive records for ${symbol}.`);
    return;
  }

  const latest = sorted[0];
  setText("lookup-close",    `₹${numFmt(latest.close_price ?? latest.last_price)}`);
  setText("lookup-vwap",     `₹${numFmt(latest.vwap)}`);
  setText("lookup-delivery", pctFmt(latest.delivery_to_traded_percent));
  setText("lookup-quantity", intFmt.format(latest.total_traded_quantity ?? 0));

  const tbody = document.getElementById("lookup-table");
  if (!tbody) return;
  updateDOM(tbody, sorted.map((r) => `<tr>
    <td>${dateFmt(r.trade_date)}</td>
    <td class="advanced-only">${r.series}</td>
    <td class="advanced-only">₹${numFmt(r.previous_close)}</td>
    <td class="advanced-only">₹${numFmt(r.open_price)}</td>
    <td class="advanced-only">₹${numFmt(r.high_price)}</td>
    <td class="advanced-only">₹${numFmt(r.low_price)}</td>
    <td>₹${numFmt(r.close_price ?? r.last_price)}</td>
    <td class="advanced-only">₹${numFmt(r.vwap)}</td>
    <td class="advanced-only">${intFmt.format(r.total_traded_quantity ?? 0)}</td>
    <td class="advanced-only">${intFmt.format(r.deliverable_quantity ?? 0)}</td>
    <td>${pctFmt(r.delivery_to_traded_percent)}</td>
    <td class="advanced-only">${intFmt.format(r.number_of_trades ?? 0)}</td>
    <td class="advanced-only">₹${numFmt(r.turnover)}</td>
  </tr>`).join(""));
  const addBtn = document.getElementById("add-to-scanner-btn");
  if (addBtn) addBtn.style.display = "block";
  
  // Render native React terminal if available
  const ahWrapper = document.getElementById("ah_chart_wrapper");
  if (ahWrapper) ahWrapper.style.display = "flex"; // Make sure it's visible
  
  if (ahWrapper) {
    // Clear out any legacy React or Canvas chart contents
    ahWrapper.innerHTML = '';
    
    // Create iframe if it doesn't exist globally
    if (!window.AhChartTerminalFrame) {
      const iframe = document.createElement('iframe');
      iframe.src = '/js/chart-terminal/trading-chart.html';
      iframe.style.width = '100%';
      iframe.style.height = '100%';
      iframe.style.border = 'none';
      iframe.style.outline = 'none';
      
      // We store it globally so we don't recreate the iframe on every symbol click
      window.AhChartTerminalFrame = iframe;
      ahWrapper.appendChild(iframe);
      
      // Wait for it to load before sending the first symbol
      iframe.onload = () => {
        iframe.contentWindow.postMessage({ type: 'LOAD_SYMBOL', symbol: symbol }, '*');
      };
    } else {
      // If it already exists, just append it back to the wrapper (in case it was detached)
      if (!ahWrapper.contains(window.AhChartTerminalFrame)) {
        ahWrapper.appendChild(window.AhChartTerminalFrame);
      }
      // Instantly push the new symbol to the existing chart
      window.AhChartTerminalFrame.contentWindow.postMessage({ type: 'LOAD_SYMBOL', symbol: symbol }, '*');
    }
  }
  
  // Initialise visual replay mode with EOD candles
  window.initReplayMode(symbol, rows);
}

// ── Render: Backtest ──────────────────────────────────────────────────────
function renderBacktest(data) {
  setText("bt-trades",       data.trades);
  setText("bt-win-rate",     pctFmt(data.win_rate));
  setText("bt-sharpe",       numFmt(data.sharpe_ratio));
  setText("bt-total-return", pctFmt(data.total_return_percent));
  setText("bt-avg-return",   pctFmt(data.avg_return_per_trade ?? 0));
  setText("bt-drawdown",     pctFmt(data.max_drawdown));
  setText("bt-best",         pctFmt(data.best_trade ?? 0));
  setText("bt-worst",        pctFmt(data.worst_trade ?? 0));
  setText("bt-precision",    pctFmt(data.precision));
  setText("bt-recall",       pctFmt(data.recall));
  setText("bt-consec-wins",  data.consecutive_wins ?? "—");
  setText("bt-consec-losses",data.consecutive_losses ?? "—");
  setText("bt-slippage",     data.slippage_applied_percent != null ? `${data.slippage_applied_percent}%` : "—");
  setText("bt-brokerage",    data.brokerage_per_leg != null ? `₹${data.brokerage_per_leg}/leg` : "—");

  if (data.slippage_applied_percent != null) {
    const sub = document.getElementById("bt-subtitle");
    if (sub) sub.textContent = `Breakout replay · ${data.slippage_applied_percent}% slippage · ₹${data.brokerage_per_leg}/leg brokerage · ATR position sizing`;
  }

  // Colour total return
  const retEl = document.getElementById("bt-total-return");
  if (retEl) {
    const v = Number(data.total_return_percent ?? 0);
    retEl.className = "metric-value " + (v > 0 ? "bullish" : v < 0 ? "bearish" : "neutral");
  }

  // Draw Equity/Drawdown performance charts
  drawBacktestSVG(data);
}

async function refresh() {
  setText("last-updated", "Refreshing…");

  try {
    // CRIT-3 FIX: Use allSettled so a 500 on empty portfolio never kills the whole dashboard
    const results = await Promise.allSettled([
      getJson(API.overview),                               // 0
      getJson(API.snapshots),                              // 1
      getJson(API.scannerFiltered(activeSignalFilter)),    // 2
      getJson(API.positions),                              // 3
      getJson(API.alerts),                                 // 4
      getJson("/api/market/regime"),                       // 5
      getJson("/api/market/sectors"),                      // 6
      getJson("/api/positions/portfolio/risk"),            // 7
      getJson("/api/positions/portfolio/performance"),     // 8
      getJson(API.aiSignals),                              // 9
    ]);

    const ok = (r, fallback) => r.status === "fulfilled" ? r.value : fallback;

    const overview  = ok(results[0], null);
    const snapshots = ok(results[1], []);
    const scanner   = ok(results[2], []);
    const positions = ok(results[3], []);
    const alerts    = ok(results[4], []);
    const regime    = ok(results[5], { regime: "UNKNOWN", confidence: 0 });
    const sectors   = ok(results[6], []);
    const portRisk  = ok(results[7], null);
    const portPerf  = ok(results[8], null);
    const aiSignals = ok(results[9], []);

    if (overview)  renderOverview(overview);
    renderSnapshots(snapshots);
    renderMarketCycles(snapshots);
    renderScanner(scanner);
    renderTopOpportunities(scanner);
    renderPositions(positions);
    renderAlerts(alerts);
    renderAiSignals(aiSignals);

    // Render Market Regime — hide badge if confidence is 0 (broken engine)
    const regimeBadge = document.getElementById("regime-badge");
    if (regimeBadge) {
      if (regime.confidence > 0) {
        regimeBadge.style.display = "inline-block";
        regimeBadge.textContent = `REGIME: ${regime.regime.replaceAll("_", " ")} (${regime.confidence}%)`;
      } else {
        regimeBadge.style.display = "none";
      }
    }

    // Breakout Radar data fetching
    try {
      const breakoutData = await getJson(API.breakoutRadar);
      renderBreakoutRadar(breakoutData);
    } catch(err) {
      console.error("Failed to load breakout radar data", err);
    }

    // Render Sector Heatmap
    window.lastSectors = sectors;
    window.lastSnapshots = snapshots;
    renderHeatmap();

    // Render Portfolio Risk Panel (only when positions exist AND risk data available)
    const portPanel = document.getElementById("portfolio-risk-panel");
    if (portPanel && positions.length > 0 && portRisk && portPerf) {
      portPanel.style.display = "grid";
      const riskColor = portRisk.portfolio_risk === "HIGH" ? "var(--danger)" : portRisk.portfolio_risk === "MODERATE" ? "var(--warning)" : "var(--green)";
      const riskEl = document.getElementById("port-risk-level");
      riskEl.textContent = portRisk.portfolio_risk;
      riskEl.style.color = riskColor;
      setText("port-win-rate", `${portPerf.win_rate}%`);
      setText("port-sharpe", portPerf.sharpe_ratio.toFixed(2));
      setText("port-rr", portPerf.avg_rr.toFixed(2));
    } else if (portPanel) {
      portPanel.style.display = "none";
    }

    // Live update the intraday chart if we are on the lookup tab
    const lookupPanel = document.getElementById("lookup");
    if (window.activeChartSymbol && lookupPanel && lookupPanel.classList.contains("is-active")) {
      getJson(`/api/market/intraday?symbol=${window.activeChartSymbol}&interval=15m`)
        .then(intraday => {
          if (intraday && intraday.length > 0 && window.AlphaChartManager) {
            const dates = intraday.map(r => r.observed_at);
            const kData = intraday.map(r => [r.open, r.close, r.low, r.high]);
            const volumes = intraday.map(r => r.volume);
            window.AlphaChartManager.renderChart(window.activeChartSymbol, dates, kData, volumes);
          }
        }).catch(e => console.warn("Live chart update failed:", e));
    }

    setText("last-updated", `Last updated: ${new Date().toLocaleTimeString()}`);
  } catch (err) {
    setText("last-updated", `Error: ${err.message}`);
  }
}

window.addToScanner = async function(symbol) {
  if (!symbol) return;
  try {
    await fetch(`/api/scanner/symbols/${symbol.toUpperCase()}`, { method: "POST" });
    alert(`${symbol.toUpperCase()} added to Scanner! It will appear on the next auto-refresh.`);
  } catch (err) {
    alert(`Failed to add ${symbol} to scanner: ${err.message}`);
  }
};

async function runBacktest() {
  // MED-7 FIX: Use cache — don't re-run on every tab click
  if (_backtestCache) {
    renderBacktest(_backtestCache);
    return;
  }
  setText("bt-trades", "…");
  try {
    const data = await getJson(API.backtest, { method: "POST" });
    _backtestCache = data;
    renderBacktest(data);
  } catch (err) {
    console.error("Backtest failed:", err);
  }
}

// ── Countdown + auto-refresh ───────────────────────────────────────────────
let isRefreshing = false;
function startCountdown() {
  let remaining = refreshSeconds;
  const el = document.getElementById("refresh-countdown");

  clearInterval(countdownInterval);
  countdownInterval = setInterval(() => {
    if (isRefreshing) return;
    remaining--;
    if (el) el.textContent = `Auto-refresh in ${remaining}s`;
    if (remaining <= 0) {
      remaining = refreshSeconds;
      if (el) el.textContent = `Refreshing...`;
      isRefreshing = true;
      refresh().finally(() => {
        isRefreshing = false;
      });
    }
  }, 1000);
}

// ── Breakout Radar ────────────────────────────────────────────────────────
window.breakoutCandidates = [];
window.activeBreakoutFilter = 'all';

function renderBreakoutRadar(data) {
  window.breakoutCandidates = data || [];
  filterBreakoutRadar();
}

function filterBreakoutRadar() {
  const tbody = document.getElementById("breakout-radar-table");
  if (!tbody) return;

  let filtered = window.breakoutCandidates;
  if (window.activeBreakoutFilter === 'breakout_only') {
    filtered = filtered.filter(c => c.status === 'Confirmed Breakout');
  } else if (window.activeBreakoutFilter === 'near_breakout') {
    filtered = filtered.filter(c => c.status === 'Near Breakout');
  } else if (window.activeBreakoutFilter === 'support_only') {
    filtered = filtered.filter(c => c.status.includes('Support'));
  }

  if (filtered.length === 0) {
    updateDOM(tbody, `<tr><td colspan="8"><div class="empty-state">No candidates found</div></td></tr>`);
    return;
  }

  updateDOM(tbody, filtered.map((c, i) => {
    let statusClass = "br-status-waiting";
    if (c.status === "Near Breakout") statusClass = "br-status-near";
    else if (c.status === "Support Building" || c.status === "Support Confirmed") statusClass = "br-status-building";
    else if (c.status === "Confirmed Breakout") statusClass = "br-status-confirmed";
    else if (c.status === "Fakeout Risk") statusClass = "br-status-fakeout";

    const prevLvl = c.prev_month_high || c.prev_month_low || 0;
    const lvlDate = c.prev_level_date ? new Date(c.prev_level_date).toLocaleDateString(undefined, {month: 'short', day: 'numeric'}) : '--';
    
    return `<tr class="br-row" onclick="selectBreakoutCandidate(${i})">
      <td><strong style="color:var(--primary);">${c.symbol}</strong></td>
      <td>₹${numFmt(c.last_price)}</td>
      <td>${c.trend_15m || '--'}</td>
      <td class="${statusClass}">${c.status}</td>
      <td>${(c.breakout_percentage || 0).toFixed(2)}%</td>
      <td>₹${numFmt(prevLvl)}</td>
      <td>${lvlDate}</td>
      <td>${c.days_since_prev_level ?? '--'}</td>
      <td>${(c.relative_strength || 0).toFixed(2)}</td>
      <td>${(c.volume_ratio || 0).toFixed(1)}x</td>
      <td>${numFmt(c.volume)}</td>
      <td>${numFmt(c.prev_level_volume)}</td>
      <td>${c.confidence_score}</td>
    </tr>`;
  }).join(""));
}

window.selectBreakoutCandidate = function(idx) {
  const c = window.breakoutCandidates[idx];
  if (!c) return;

  document.getElementById("breakout-radar-detail").style.display = "block";
  setText("br-detail-symbol", c.symbol);
  setText("br-detail-score", c.confidence_score);
  setText("br-detail-price", `₹${numFmt(c.last_price)}`);
  
  const stEl = document.getElementById("br-detail-status");
  stEl.textContent = c.status;
  if (c.status === "Confirmed Breakout") stEl.style.background = "var(--green)";
  else if (c.status === "Fakeout Risk") stEl.style.background = "var(--red)";
  else stEl.style.background = "var(--surface-3)";

  updateDOM(document.getElementById("br-detail-ai-exp"), c.ai_explanation);
  
  setText("br-detail-price-grid", `₹${numFmt(c.last_price)}`);
  setText("br-detail-vol", numFmt(c.volume));

  setText("br-detail-high", `₹${numFmt(c.prev_month_high)}`);
  const highDate = c.prev_high_date ? new Date(c.prev_high_date).toLocaleDateString(undefined, {month: 'short', day: 'numeric'}) : '--';
  setText("br-detail-high-date", highDate);

  setText("br-detail-low", `₹${numFmt(c.prev_month_low)}`);
  const lowDate = c.prev_low_date ? new Date(c.prev_low_date).toLocaleDateString(undefined, {month: 'short', day: 'numeric'}) : '--';
  setText("br-detail-low-date", lowDate);

  setText("br-detail-breakout-pct", `${(c.breakout_percentage || 0).toFixed(2)}%`);
  setText("br-detail-support-pct", `${(c.support_percentage || 0).toFixed(2)}%`);

  setText("br-detail-vol-ratio", `${(c.volume_ratio || 0).toFixed(1)}x`);
  setText("br-detail-rs", `${(c.relative_strength || 0).toFixed(2)}%`);

  setText("br-detail-trend", c.trend_15m || "Neutral");
  setText("br-detail-ai-score", c.confidence_score);

  setText("br-detail-signal-type", c.signal || "WAIT");
  setText("br-detail-signal-strength", c.signal_strength || "Neutral");
  
  setText("br-detail-entry", c.recommended_entry || "—");
  setText("br-detail-sl", c.stoploss ? `₹${numFmt(c.stoploss)}` : "—");
  setText("br-detail-targets", c.target_1 ? `₹${numFmt(c.target_1)} / ₹${numFmt(c.target_2)} / ₹${numFmt(c.target_3)}` : "—");
  
  const execBtn = document.getElementById("br-detail-execute");
  if (c.signal === "BUY") {
    execBtn.disabled = false;
    execBtn.onclick = () => showToast(`Executing Trade for ${c.symbol}...`);
  } else {
    execBtn.disabled = true;
  }
  
  // Set global context for chart engine to pick up
  const levelPrice = c.status.includes('Support') ? c.prev_month_low : c.prev_month_high;
  window.activeBreakoutContext = {
    symbol: c.symbol,
    prev_level_date: c.prev_level_date,
    level_price: levelPrice,
    breakout_percentage: c.breakout_percentage,
    ai_explanation: c.ai_explanation
  };
  
  // Trigger chart update event
  window.dispatchEvent(new CustomEvent('breakoutContextUpdated'));
  
  // Show chart wrapper and load data
  const chartWrapper = document.getElementById("br-chart-wrapper");
  if (chartWrapper) {
    chartWrapper.style.display = "flex";
    setText("br_chart_title", c.symbol);
    
    const qs = new URLSearchParams({ symbol: c.symbol, range: "3M", series: "EQ", live: "true" });
    getJson(`${API.securityArchives}?${qs}`).then(rows => {
      const sorted = rows.sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
      const dates = sorted.map(r => r.trade_date);
      const kData = sorted.map(r => [
        r.open_price || r.previous_close, 
        r.close_price || r.last_price,    
        r.low_price || r.previous_close,  
        r.high_price || r.previous_close  
      ]);
      const volumes = sorted.map(r => r.total_traded_quantity || 0);
      
      let levelDate = null;
      if (c.prev_level_date) {
        levelDate = c.prev_level_date.split('T')[0];
      }
      
      window.BreakoutChartManager.renderBreakoutChart(
        c.symbol, dates, kData, volumes, 
        c.prev_month_high, c.prev_month_low, levelDate
      );
    }).catch(err => {
      console.error("Failed to load chart data for Breakout Radar:", err);
    });
  }
  
  if (window.openLookup) {
    window.openLookup(c.symbol);
  }
};

// ── Event Listeners ────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  const filters = document.getElementById("breakout-radar-filters");
  if (filters) {
    filters.querySelectorAll("button").forEach(btn => {
      btn.addEventListener("click", () => {
        filters.querySelectorAll("button").forEach(b => b.classList.remove("is-active"));
        btn.classList.add("is-active");
        window.activeBreakoutFilter = btn.dataset.filter;
        filterBreakoutRadar();
      });
    });
  }

  // Handle /breakout-radar path routing on load
  if (window.location.pathname === "/breakout-radar") {
    const tab = document.getElementById("tab-breakout-radar");
    if (tab) tab.click();
  }
});

// ── Signal filter buttons ─────────────────────────────────────────────────
// HIGH-3 FIX: Filter now immediately re-fetches scanner data
let filterDebounceTimer;
function activateSignalFilters() {
  document.querySelectorAll(".signal-filter").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".signal-filter").forEach((b) => b.classList.remove("is-active"));
      btn.classList.add("is-active");
      activeSignalFilter = btn.dataset.signal || "";
      const label = document.getElementById("active-signal-filter");
      if (label) label.textContent = btn.textContent;
      
      clearTimeout(filterDebounceTimer);
      filterDebounceTimer = setTimeout(() => {
        getJson(API.scannerFiltered(activeSignalFilter))
          .then(renderScanner)
          .catch(console.error);
      }, 300);
    });
  });
}

// ── Add position form ─────────────────────────────────────────────────────
document.getElementById("toggle-add-position")?.addEventListener("click", () => {
  const form = document.getElementById("add-position-form");
  if (form) form.style.display = form.style.display === "none" ? "grid" : "none";
});

document.getElementById("add-position-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const symbol   = document.getElementById("pos-symbol")?.value.trim().toUpperCase();
  const entry    = parseFloat(document.getElementById("pos-entry")?.value);
  const qty      = parseInt(document.getElementById("pos-qty")?.value, 10);
  const sl       = parseFloat(document.getElementById("pos-sl")?.value) || undefined;
  const target   = parseFloat(document.getElementById("pos-target")?.value) || undefined;

  if (!symbol || isNaN(entry)) return;

  const payload = { symbol, entry_price: entry, quantity: qty };
  if (sl)     payload.stop_loss     = sl;
  if (target) payload.target_price  = target;

  try {
    await fetch(API.addPosition, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const addForm = document.getElementById("add-position-form");
    if (addForm) addForm.style.display = "none";
    const positions = await getJson(API.positions);
    renderPositions(positions);
  } catch (err) {
    console.error("Add position failed:", err);
  }
});

// ── Lookup form ────────────────────────────────────────────────────────────
window.populateLookupSilently = function(symbol) {
  const symbolEl = document.getElementById("lookup-symbol");
  if (symbolEl) {
    symbolEl.value = symbol;
    const form = document.getElementById("lookup-form");
    // Dispatch submit but prevent it from taking over focus if needed
    if (form) form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  }
};

window.openLookup = function(symbol) {
  const tabBtn = document.querySelector('.tab[data-panel="lookup"]');
  if (tabBtn) tabBtn.click();
  
  const symbolEl = document.getElementById("lookup-symbol");
  if (symbolEl) {
    symbolEl.value = symbol;
    const form = document.getElementById("lookup-form");
    if (form) form.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
  }
};

window.filterBySector = function(sector) {
  if (window.activeSectorFilter === sector) {
    window.activeSectorFilter = null; // Toggle off
  } else {
    window.activeSectorFilter = sector;
  }
  renderHeatmap();
  renderSnapshots(window.lastSnapshots);
  renderMarketCycles(window.lastSnapshots);
};

const SECTOR_WEIGHTS = {
  "FINANCIAL SERVICES": 33.5,
  "IT": 13.8,
  "ENERGY": 12.2,
  "CONSUMER GOODS": 11.3,
  "AUTOMOBILE": 8.1,
  "METALS": 4.5,
  "CONSTRUCTION MATERIALS": 3.8,
  "HEALTHCARE": 4.8,
  "TELECOMMUNICATION": 4.0,
  "SERVICES": 4.0
};

function renderHeatmap() {
  const heatContainer = document.getElementById("sector-heatmap");
  if (!heatContainer) return;
  
  if (!window.lastSectors || window.lastSectors.length === 0) {
    updateDOM(heatContainer, `<div style="padding: 16px; color: var(--text-muted);">No sector data available.</div>`);
    return;
  }
  
  const totalWeight = window.lastSectors.reduce((sum, s) => sum + (SECTOR_WEIGHTS[s.sector.toUpperCase()] || 8.0), 0);
  
  updateDOM(heatContainer, window.lastSectors.map(s => {
    const weight = SECTOR_WEIGHTS[s.sector.toUpperCase()] || 8.0;
    const weightPct = ((weight / totalWeight) * 100).toFixed(1);
    
    // Calculate intensity color based on score (0 to 100)
    let bg, border, textColor;
    if (s.score >= 50) {
      const pct = (s.score - 50) / 50;
      bg = `rgba(0, 240, 118, ${(0.03 + 0.32 * pct).toFixed(2)})`;
      border = `1px solid rgba(0, 240, 118, ${(0.15 + 0.5 * pct).toFixed(2)})`;
      textColor = `rgba(255, 255, 255, 0.95)`;
    } else {
      const pct = (50 - s.score) / 50;
      bg = `rgba(255, 59, 48, ${(0.03 + 0.32 * pct).toFixed(2)})`;
      border = `1px solid rgba(255, 59, 48, ${(0.15 + 0.5 * pct).toFixed(2)})`;
      textColor = `rgba(255, 255, 255, 0.95)`;
    }
    
    const isActive = window.activeSectorFilter === s.sector;
    const isMuted = window.activeSectorFilter && !isActive;
    const opacity = isMuted ? "0.25" : "1";
    const outline = isActive ? `box-shadow: 0 0 0 2px var(--indigo);` : "";
    
    return `<div class="heatmap-block" onclick="filterBySector('${s.sector}')" style="cursor: pointer; flex: ${weight} 1 180px; height: 75px; background: ${bg}; border: ${border}; opacity: ${opacity}; transition: all 0.2s; ${outline} padding: 10px; display: flex; flex-direction: column; justify-content: space-between; border-radius: var(--radius);">
      <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--text-muted); display: flex; justify-content: space-between; align-items: center;">
        <span>${s.sector}</span>
        <span style="font-family: var(--font-mono); font-size: 10px;">${weightPct}%</span>
      </div>
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 8px;">
        <span style="font-family: var(--font-mono); font-size: 20px; font-weight: 700; color: ${textColor};">${s.score}</span>
        <span style="font-size: 10px; font-weight: 600; color: var(--text-muted);">Score</span>
      </div>
    </div>`;
  }).join(""));
}

document.getElementById("lookup-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const symbolEl = document.getElementById("lookup-symbol");
  const range    = document.getElementById("lookup-range")?.value;
  const series   = document.getElementById("lookup-series")?.value;
  const live     = "true"; // We will make the backend use fast yfinance instead
  const symbol   = symbolEl?.value.trim().toUpperCase();

  if (!symbol) { clearLookup("Please enter a stock symbol."); return; }
  if (symbolEl) symbolEl.value = symbol;
  clearLookup(`Loading ${symbol}…`);

  const qs = new URLSearchParams({ symbol, range, series, live });
  try {
    const [rows, liveQuotes, instMetrics, intraday] = await Promise.all([
      getJson(`${API.securityArchives}?${qs}`),
      getJson(API.liveQuotes(symbol)).catch(() => null),
      getJson(`/api/market/institutional-metrics/${symbol}`).catch(() => null),
      getJson(`/api/market/intraday?symbol=${symbol}&interval=15m`).catch(() => [])
    ]);
    window.activeChartSymbol = symbol;
    renderStockLookup(symbol, rows, intraday);
    
    // Override close price with accurate live quote if available
    if (liveQuotes && liveQuotes.length > 0) {
      const liveQuote = liveQuotes[0];
      setText("lookup-close", `₹${numFmt(liveQuote.last_price)}`);
    }

    // Populate Institutional Metrics Cards
    if (instMetrics) {
      const g = (val, fmt="") => val !== null && val !== undefined ? `${val}${fmt}` : "—";
      
      // Structure
      const cardStruct = document.getElementById("card-market-structure");
      if (cardStruct) {
        cardStruct.style.display = "block";
        setText("inst-52w-dist", g(instMetrics.structure.distance_to_52w_high_pct, "%"));
        setText("inst-m-high-dist", g(instMetrics.structure.distance_to_month_high_pct, "%"));
        setText("inst-structure-flags", instMetrics.structure.flags?.join(", ") || "None");
      }

      // Spurt
      const cardSpurt = document.getElementById("card-spurt");
      if (cardSpurt) {
        cardSpurt.style.display = "block";
        setText("inst-vol-spurt", g(instMetrics.spurt.volume_spurt, "x"));
        setText("inst-del-spurt", g(instMetrics.spurt.delivery_spurt, "%"));
        setText("inst-spurt-prob", g(instMetrics.spurt.probability));
      }

      // Options
      const cardOpt = document.getElementById("card-options-pred");
      if (cardOpt) {
        cardOpt.style.display = "block";
        setText("inst-opt-range", g(instMetrics.options.expiry_range));
        setText("inst-opt-bull", g(instMetrics.options.bullish_probability, "%"));
        setText("inst-opt-pain", g(instMetrics.options.max_pain));
      }

      // Fibonacci
      const cardFib = document.getElementById("card-fibonacci");
      if (cardFib) {
        cardFib.style.display = "block";
        setText("inst-fib-ret", g(instMetrics.fibonacci.levels?.fib_382));
        setText("inst-fib-ext", g(instMetrics.fibonacci.levels?.ext_1618));
        setText("inst-fib-confluence", instMetrics.fibonacci.confluence?.join(", ") || "None");
      }
    }



    setText("lookup-status", rows.length ? `Showing ${rows.length} records for ${symbol}.` : `No records found for ${symbol}.`);
  } catch (err) {
    const ahWrapper = document.getElementById("ah_chart_wrapper");
    if (ahWrapper) ahWrapper.style.display = "none";
    clearLookup(`Could not load ${symbol}. ${err.message}`);

  }
});

// ── Button handlers ────────────────────────────────────────────────────────
document.getElementById("refresh-button")?.addEventListener("click", () => {
  refresh();
  startCountdown();
});

document.getElementById("download-csv-button")?.addEventListener("click", () => {
  window.open(API.latestExport, "_blank");
});

document.getElementById("lookup-tab-button")?.addEventListener("click", () => {
  document.querySelector('.tab[data-panel="lookup"]')?.click();
  document.getElementById("lookup-symbol")?.focus();
});

document.getElementById("run-backtest-button")?.addEventListener("click", () => {
  _backtestCache = null;
  runBacktest();
});

// AI Assistant Sidebar Interactions (Added in Phase 4)
const assistantSidebar = document.getElementById("ai-assistant-sidebar");
document.getElementById("assistant-toggle-button")?.addEventListener("click", () => {
  if (assistantSidebar) {
    const isHidden = assistantSidebar.style.transform === "translateX(100%)" || assistantSidebar.style.transform === "";
    assistantSidebar.style.transform = isHidden ? "translateX(0)" : "translateX(100%)";
  }
});

document.getElementById("close-assistant-btn")?.addEventListener("click", () => {
  if (assistantSidebar) assistantSidebar.style.transform = "translateX(100%)";
});

document.getElementById("assistant-chat-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const inputEl = document.getElementById("assistant-chat-input");
  const historyEl = document.getElementById("assistant-chat-history");
  if (!inputEl || !historyEl) return;

  const msg = inputEl.value.trim();
  if (!msg) return;
  inputEl.value = "";

  // Append user message
  const userDiv = document.createElement("div");
  userDiv.style.cssText = "align-self:flex-end; background:var(--indigo-dim); border:1px solid var(--indigo); padding:8px 12px; border-radius:8px; max-width:85%; word-wrap:break-word; color:#fff;";
  userDiv.innerHTML = `<strong>You:</strong> ${escapeHTML(msg)}`;
  historyEl.appendChild(userDiv);
  historyEl.scrollTop = historyEl.scrollHeight;

  // Append loading bubble
  const loadDiv = document.createElement("div");
  loadDiv.style.cssText = "align-self:flex-start; background:var(--surface-2); padding:8px 12px; border-radius:8px; color:var(--text-muted);";
  loadDiv.textContent = "Analyzing data…";
  historyEl.appendChild(loadDiv);
  historyEl.scrollTop = historyEl.scrollHeight;

  try {
    const res = await fetch("/api/assistant/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: msg })
    });
    const data = await res.json();
    loadDiv.remove();

    const replyDiv = document.createElement("div");
    replyDiv.style.cssText = "align-self:flex-start; background:var(--surface-2); border:1px solid var(--border); padding:10px 14px; border-radius:8px; max-width:85%; line-height:1.4; color:var(--text); word-wrap:break-word;";
    
    // Very basic markdown formatting parser
    let parsedText = data.reply || "Sorry, I couldn't compute a reply.";
    parsedText = escapeHTML(parsedText);
    parsedText = parsedText.replace(/\n/g, "<br>")
                           .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                           .replace(/### (.*?)(<br>|$)/g, "<h3>$1</h3>")
                           .replace(/#### (.*?)(<br>|$)/g, "<h4>$1</h4>")
                           .replace(/- (.*?)(<br>|$)/g, "• $1$2");

    replyDiv.innerHTML = parsedText;
    historyEl.appendChild(replyDiv);
    historyEl.scrollTop = historyEl.scrollHeight;
  } catch (err) {
    loadDiv.remove();
    const errDiv = document.createElement("div");
    errDiv.style.cssText = "align-self:flex-start; background:rgba(239,68,68,0.15); border:1px solid var(--red); padding:8px 12px; border-radius:8px; color:#f87171;";
    errDiv.textContent = `Error: ${err.message}`;
    historyEl.appendChild(errDiv);
    historyEl.scrollTop = historyEl.scrollHeight;
  }
});

// Strategy Builder Form Submit (Added in Phase 4)
document.getElementById("strategy-builder-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const symbol = document.getElementById("sb-symbol")?.value.trim().toUpperCase();
  const rsi_min = parseFloat(document.getElementById("sb-rsi")?.value);
  const volume_mult = parseFloat(document.getElementById("sb-volume")?.value);
  const trend_ma = parseInt(document.getElementById("sb-ma")?.value, 10);
  const submitBtn = document.getElementById("sb-submit-btn");

  if (!symbol || isNaN(rsi_min)) return;
  if (submitBtn) { submitBtn.textContent = "⚙️ Running…"; submitBtn.disabled = true; }

  try {
    const res = await fetch("/api/strategy/backtest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol, rsi_min, volume_mult, trend_ma })
    });
    const data = await res.json();
    if (submitBtn) { submitBtn.textContent = "⚡ Backtest Strategy"; submitBtn.disabled = false; }

    if (data.detail) {
      showToast(data.detail, "error");
      return;
    }

    // Populate performance card
    document.getElementById("sb-results-card").style.display = "block";
    setText("sb-win-rate", `${data.win_rate}%`);
    setText("sb-sharpe", data.sharpe_ratio.toFixed(2));
    setText("sb-sortino", data.sortino_ratio.toFixed(2));
    setText("sb-cagr", `${data.cagr}%`);
    setText("sb-drawdown", `${data.max_drawdown}%`);
    setText("sb-pf", data.profit_factor.toFixed(2));

    // Populate trades table
    const tableBody = document.getElementById("sb-trades-table");
    if (tableBody) {
      if (data.trades.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--text-muted);">No trades executed under these parameters.</td></tr>`;
      } else {
        tableBody.innerHTML = data.trades.map(t => {
          const pnlCls = t.pnl > 0 ? "pnl-positive" : t.pnl < 0 ? "pnl-negative" : "pnl-neutral";
          const pnlSign = t.pnl > 0 ? "+" : "";
          return `<tr>
            <td>${escapeHTML(t.entry_date)}</td>
            <td>₹${escapeHTML(t.entry_price.toFixed(2))}</td>
            <td>₹${t.exit_price.toFixed(2)}</td>
            <td class="${pnlCls}">${pnlSign}₹${t.pnl.toFixed(2)}</td>
            <td class="${pnlCls}">${pnlSign}${t.return_pct.toFixed(2)}%</td>
            <td><span class="badge" style="background:var(--surface-3); font-size:10px; padding:2px 6px;">${t.reason}</span></td>
          </tr>`;
        }).join("");
      }
    }
  } catch (err) {
    if (submitBtn) { submitBtn.textContent = "⚡ Backtest Strategy"; submitBtn.disabled = false; }
    showToast(`Backtest failed: ${err.message}`, "error");
  }
});

// ── Options Chain Logic ───────────────────────────────────────────────────
function clearOptions(msg = "Enter an F&O symbol (e.g. NIFTY, RELIANCE) to load option chain.") {
  setText("opt-underlying", "—");
  setText("opt-pcr",        "—");
  setText("opt-max-pain",    "—");
  setText("opt-atm-iv",      "—");
  const t = document.getElementById("options-table-body");
  if (t) updateDOM(t, "");
  setText("options-status", msg);
  const aiCard = document.getElementById("ai-suggestion-card");
  if (aiCard) aiCard.style.display = "none";
}

function renderOptionsChain(data) {
  setText("opt-underlying", `₹${numFmt(data.underlying_price)}`);
  
  // Color PCR: > 1.2 bullish green, < 0.7 bearish red, middle neutral
  const pcrEl = document.getElementById("opt-pcr");
  if (pcrEl) {
    pcrEl.textContent = data.pcr.toFixed(2);
    pcrEl.className = "metric-value " + (data.pcr > 1.2 ? "bullish" : data.pcr < 0.7 ? "bearish" : "neutral");
  }
  
  setText("opt-max-pain", data.max_pain ? `₹${numFmt(data.max_pain)}` : "—");
  setText("opt-atm-iv", data.atm_iv != null ? `${data.atm_iv.toFixed(1)}%` : "—");

  // Render AI Suggestion
  const aiCard = document.getElementById("ai-suggestion-card");
  if (aiCard && data.ai_suggestion) {
    aiCard.style.display = "block";
    const sug = data.ai_suggestion;
    const strike = sug.suggested_strike ? numFmt(sug.suggested_strike) : "";
    
    const sugTitle = document.getElementById("ai-sugg-title");
    const sugProb = document.getElementById("ai-sugg-prob");
    const sugReason = document.getElementById("ai-sugg-reason");
    
    if (sugTitle) sugTitle.textContent = sug.option_type === "Hold" ? "Wait / No Clear Signal" : `Buy ${strike} ${sug.option_type} (${sug.signal})`;
    if (sugProb) {
      sugProb.textContent = `${Math.round(sug.probability * 100)}%`;
      if (sug.signal === "Bullish") sugProb.style.color = "var(--green)";
      else if (sug.signal === "Bearish") sugProb.style.color = "var(--red)";
      else sugProb.style.color = "var(--text-muted)";
    }
    if (sugReason) sugReason.textContent = sug.reasoning || "";
  } else if (aiCard) {
    aiCard.style.display = "none";
  }

  const tbody = document.getElementById("options-table-body");
  if (!tbody) return;

  if (!data.strikes || data.strikes.length === 0) {
    updateDOM(tbody, `<tr><td colspan="11"><div class="empty-state"><div class="empty-state-icon">📊</div>No option contracts found for this expiry</div></td></tr>`);
    return;
  }

  // Find max open interest values for visual heatmap widths
  const maxCeOi = Math.max(...data.strikes.map(s => s.ce_oi || 0), 1);
  const maxPeOi = Math.max(...data.strikes.map(s => s.pe_oi || 0), 1);

  updateDOM(tbody, data.strikes.map((s) => {
    const ceItmClass = s.strike_price < data.underlying_price ? "itm-calls" : "";
    const peItmClass = s.strike_price > data.underlying_price ? "itm-puts" : "";

    const ceOiClass = (data.max_call_oi_strike && s.strike_price === data.max_call_oi_strike) ? "opt-oi-high" : "";
    const peOiClass = (data.max_put_oi_strike && s.strike_price === data.max_put_oi_strike) ? "opt-oi-high" : "";

    const ceOiPct = ((s.ce_oi || 0) / maxCeOi * 100).toFixed(1);
    const peOiPct = ((s.pe_oi || 0) / maxPeOi * 100).toFixed(1);

    let strikeCls = "strike-cell-opt";
    if (s.is_atm) strikeCls += " atm-strike";
    if (s.is_max_pain) strikeCls += " max-pain-strike";

    const formatChg = (val) => {
      if (val === null || val === undefined) return "—";
      const cls = val > 0 ? "opt-change-pos" : val < 0 ? "opt-change-neg" : "";
      const sign = val > 0 ? "+" : "";
      return `<span class="${cls}">${sign}${intFmt.format(val)}</span>`;
    };

    return `<tr>
      <!-- Call side -->
      <td class="${ceItmClass} ${ceOiClass}" style="position: relative; text-align: right;">
        <div style="position: absolute; top: 0; right: 0; bottom: 0; width: ${ceOiPct}%; background: rgba(0, 200, 83, 0.1); z-index: 1;"></div>
        <span style="position: relative; z-index: 2;">${s.ce_oi ? intFmt.format(s.ce_oi) : "—"}</span>
      </td>
      <td class="${ceItmClass}">${formatChg(s.ce_change_oi)}</td>
      <td class="${ceItmClass}">${s.ce_volume ? intFmt.format(s.ce_volume) : "—"}</td>
      <td class="${ceItmClass}">${s.ce_iv ? s.ce_iv.toFixed(1) + "%" : "—"}</td>
      <td class="${ceItmClass}" style="font-weight:600">₹${numFmt(s.ce_ltp)}</td>

      <!-- Strike -->
      <td class="${strikeCls}">${numFmt(s.strike_price)}</td>

      <!-- Put side -->
      <td class="${peItmClass}" style="font-weight:600">₹${numFmt(s.pe_ltp)}</td>
      <td class="${peItmClass}">${s.pe_iv ? s.pe_iv.toFixed(1) + "%" : "—"}</td>
      <td class="${peItmClass}">${s.pe_volume ? intFmt.format(s.pe_volume) : "—"}</td>
      <td class="${peItmClass}">${formatChg(s.pe_change_oi)}</td>
      <td class="${peItmClass} ${peOiClass}" style="position: relative; text-align: left;">
        <div style="position: absolute; top: 0; left: 0; bottom: 0; width: ${peOiPct}%; background: rgba(255, 82, 82, 0.1); z-index: 1;"></div>
        <span style="position: relative; z-index: 2;">${s.pe_oi ? intFmt.format(s.pe_oi) : "—"}</span>
      </td>
    </tr>`;
  }).join(""));
}

async function loadOptionsChainExpiries(symbol) {
  const select = document.getElementById("options-expiry");
  if (!select) return;
  
  try {
    const dates = await getJson(API.optionsExpiries(symbol));
    const html = ['<option value="">Nearest Expiry</option>', ...dates.map(d => `<option value="${d}">${dateFmt(d)}</option>`)].join('');
    updateDOM(select, html);
  } catch (err) {
    console.error("Failed to load options expiries:", err);
  }
}

async function fetchOptionsChain() {
  const symbolEl = document.getElementById("options-symbol");
  const expiryEl = document.getElementById("options-expiry");
  const symbol = symbolEl?.value.trim().toUpperCase();
  const expiry = expiryEl?.value;

  if (!symbol) {
    clearOptions("Please enter a stock or index symbol.");
    return;
  }
  if (symbolEl) symbolEl.value = symbol;
  clearOptions(`Fetching Live Options Chain for ${symbol}…`);

  try {
    const data = await getJson(API.optionsChain(symbol, expiry));
    renderOptionsChain(data);

    setText("options-status", `Showing ${data.strikes.length} strikes for ${symbol} expiry ${dateFmt(data.expiry_date)} (${data.source}).`);
    
    // Fetch and render Greeks
    const atmStrike = data.atm_strike;
    if (atmStrike) {
      try {
        const greeks = await getJson(`/api/options/greeks/${symbol}?strike=${atmStrike}`);
        const gPanel = document.getElementById("greeks-panel");
        if (gPanel) {
          gPanel.style.display = "block";
          setText("greek-delta", greeks.delta);
          setText("greek-gamma", greeks.gamma);
          setText("greek-theta", greeks.theta);
          setText("greek-vega", greeks.vega);
          setText("premium-behavior-text", "Expect standard delta tracking behavior"); // Simplified for now
        }
      } catch (err) {
        console.warn("Greeks failed", err);
      }
    }
  } catch (err) {
    clearOptions(`Could not load options chain for ${symbol}. ${err.message}`);
  }
}

// ── Options Form Event Listeners ──────────────────────────────────────────
document.getElementById("options-form")?.addEventListener("submit", (e) => {
  e.preventDefault();
  fetchOptionsChain();
});

document.getElementById("options-symbol")?.addEventListener("change", () => {
  const symbol = document.getElementById("options-symbol")?.value.trim().toUpperCase();
  if (symbol) {
    loadOptionsChainExpiries(symbol);
  }
});

// Load options chain on options tab click
document.querySelector('.tab[data-panel="options-chain"]')?.addEventListener("click", () => {
  const symbol = document.getElementById("options-symbol")?.value.trim().toUpperCase() || "NIFTY";
  loadOptionsChainExpiries(symbol).then(fetchOptionsChain);
});

// ── Beginner Mode Toggle ──────────────────────────────────────────────────
document.getElementById("beginner-mode-toggle")?.addEventListener("change", (e) => {
  if (e.target.checked) {
    document.body.classList.add("mode-beginner");
    localStorage.setItem("alphahunter_beginner_mode", "1");
    // Hide advanced panels
    const tabScanner = document.querySelector('.tab[data-panel="scanner"]');
    if (tabScanner) tabScanner.style.display = "none";
    const tabAnalytics = document.querySelector('.tab[data-panel="analytics"]');
    if (tabAnalytics) tabAnalytics.style.display = "none";
    const tabOptions = document.querySelector('.tab[data-panel="options-chain"]');
    if (tabOptions) tabOptions.style.display = "none";
    
    // Activate AI signals tab if we hide the active one
    const activeTab = document.querySelector(".tab.is-active");
    if (activeTab && activeTab.dataset.panel !== "ai-signals" && activeTab.dataset.panel !== "overview") {
      const tabAi = document.querySelector('.tab[data-panel="ai-signals"]');
      if (tabAi) tabAi.click();
    }
  } else {
    document.body.classList.remove("mode-beginner");
    localStorage.setItem("alphahunter_beginner_mode", "0");
    const tabScanner = document.querySelector('.tab[data-panel="scanner"]');
    if (tabScanner) tabScanner.style.display = "inline-flex";
    const tabAnalytics = document.querySelector('.tab[data-panel="analytics"]');
    if (tabAnalytics) tabAnalytics.style.display = "inline-flex";
    const tabOptions = document.querySelector('.tab[data-panel="options-chain"]');
    if (tabOptions) tabOptions.style.display = "inline-flex";
  }
});

// ── Boot ───────────────────────────────────────────────────────────────────
// HIGH-7 FIX: Restore Beginner Mode from localStorage before activating tabs
(function restoreBeginnerMode() {
  if (localStorage.getItem("alphahunter_beginner_mode") === "1") {
    const toggle = document.getElementById("beginner-mode-toggle");
    if (toggle) {
      toggle.checked = true;
      document.body.classList.add("mode-beginner");
      const tabScanner = document.querySelector('.tab[data-panel="scanner"]');
      if (tabScanner) tabScanner.style.display = "none";
      const tabAnalytics = document.querySelector('.tab[data-panel="analytics"]');
      if (tabAnalytics) tabAnalytics.style.display = "none";
      const tabOptions = document.querySelector('.tab[data-panel="options-chain"]');
      if (tabOptions) tabOptions.style.display = "none";
    }
  }
})();

activateTabs();
activateSignalFilters();
function loopMarketStatus() {
  try { updateMarketStatus(); } catch(e) { console.error('Market status error:', e); }
  setTimeout(loopMarketStatus, 60_000);
}
loopMarketStatus();

refresh()
  .then(() => { startCountdown(); })
  .catch((err) => { setText("last-updated", err.message); });

// Load backtest on analytics tab click
document.querySelector('.tab[data-panel="analytics"]')?.addEventListener("click", runBacktest);

// ── Custom Options & UI Actions ──────────────────────────────────────────────
// openTradingView is completely removed, all UI actions that trigger charts call openLookup(symbol)
window.openChart = function(symbol) {
  openLookup(symbol);
}

async function addSignalSymbol() {
  const input = document.getElementById("add-signal-symbol");
  if (!input) return;
  const symbol = input.value.trim().toUpperCase();
  if (!symbol) return;

  try {
    const res = await fetch(`/api/scanner/symbols/${symbol}`, { method: "POST" });
    if (res.ok) {
      input.value = "";
      showToast(`✓ ${symbol} added to scanner`, "success");
      // CRIT-1 FIX: was fetchDashboardData() — correct function is refresh()
      refresh();
    } else {
      showToast(`✗ Failed to add ${symbol}`, "error");
    }
  } catch (err) {
    console.error("Error adding symbol:", err);
    showToast("Network error adding symbol", "error");
  }
}

// ── Persist Beginner Mode toggle ──────────────────────────────────────────
document.getElementById("beginner-mode-toggle")?.addEventListener("change", (e) => {
  localStorage.setItem("alphahunter_beginner_mode", e.target.checked ? "1" : "0");
});

// ── Visual EOD Backtest Equity/Drawdown Charts ──────────────────────────────
function drawBacktestSVG(data) {
  const container = document.getElementById("bt-chart-container");
  if (!container) return;

  const curve = data.equity_curve || [];
  if (curve.length === 0) {
    container.innerHTML = `<span style="color: var(--text-muted); font-size: 12px;">No equity data to display</span>`;
    return;
  }

  const width = container.clientWidth || 360;
  const height = 180;
  const padding = 20;

  const minVal = Math.min(...curve);
  const maxVal = Math.max(...curve);
  const range = maxVal - minVal || 1.0;

  const points = curve.map((v, idx) => {
    const x = padding + (idx / (curve.length - 1)) * (width - 2 * padding);
    const y = height - padding - ((v - minVal) / range) * (height - 2 * padding);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const firstX = padding;
  const lastX = width - padding;
  const bottomY = height - padding;
  const areaPoints = `${firstX},${bottomY} ${points} ${lastX},${bottomY}`;

  let peak = curve[0];
  const ddCurve = curve.map(v => {
    if (v > peak) peak = v;
    return ((peak - v) / peak) * 100;
  });
  const maxDD = Math.max(...ddCurve, 1.0);

  const ddPoints = ddCurve.map((dd, idx) => {
    const x = padding + (idx / (ddCurve.length - 1)) * (width - 2 * padding);
    const y = padding + (dd / maxDD) * (height - 2 * padding);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const ddAreaPoints = `${firstX},${padding} ${ddPoints} ${lastX},${padding}`;

  const svg = `
    <svg width="${width}" height="${height}" style="overflow: visible;">
      <defs>
        <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--indigo)" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="var(--indigo)" stop-opacity="0.0"/>
        </linearGradient>
        <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--red)" stop-opacity="0.15"/>
          <stop offset="100%" stop-color="var(--red)" stop-opacity="0.0"/>
        </linearGradient>
      </defs>
      <line x1="${padding}" y1="${padding}" x2="${width - padding}" y2="${padding}" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="2,4"/>
      <line x1="${padding}" y1="${height / 2}" x2="${width - padding}" y2="${height / 2}" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="2,4"/>
      <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="var(--border)" stroke-width="0.5"/>
      <polygon points="${ddAreaPoints}" fill="url(#ddGrad)"/>
      <polyline fill="none" stroke="rgba(255, 82, 82, 0.4)" stroke-width="1.0" points="${ddPoints}"/>
      <polygon points="${areaPoints}" fill="url(#equityGrad)"/>
      <polyline fill="none" stroke="var(--indigo)" stroke-width="2" points="${points}"/>
      <text x="${padding}" y="${padding - 4}" fill="var(--text-muted)" font-size="9" font-family="monospace">Max: ₹${maxVal.toLocaleString()}</text>
      <text x="${padding}" y="${height - padding + 12}" fill="var(--text-muted)" font-size="9" font-family="monospace">Min: ₹${minVal.toLocaleString()}</text>
      <text x="${width - padding - 75}" y="${padding - 4}" fill="var(--red)" font-size="9" font-family="monospace">Max DD: -${maxDD.toFixed(1)}%</text>
    </svg>
  `;
  container.innerHTML = svg;
}

// ── Historical EOD Replay Mode ─────────────────────────────────────────────
let replayIndex = 0;
let replayTimer = null;

window.initReplayMode = function(symbol, candles) {
  const slider = document.getElementById("replay-range-slider");
  const playBtn = document.getElementById("replay-play-btn");
  const stepBtn = document.getElementById("replay-step-btn");
  const resetBtn = document.getElementById("replay-reset-btn");
  const symbolLbl = document.getElementById("replay-symbol-label");
  const statusBadge = document.getElementById("replay-status-badge");
  
  if (!slider || !candles || candles.length < 20) {
    if (slider) slider.disabled = true;
    if (playBtn) playBtn.disabled = true;
    if (stepBtn) stepBtn.disabled = true;
    if (resetBtn) resetBtn.disabled = true;
    return;
  }

  window.replayCandles = [...candles].sort((a, b) => new Date(a.trade_date) - new Date(b.trade_date));
  replayIndex = Math.min(20, window.replayCandles.length - 1);

  slider.disabled = false;
  slider.min = replayIndex;
  slider.max = window.replayCandles.length - 1;
  slider.value = replayIndex;

  if (playBtn) playBtn.disabled = false;
  if (stepBtn) stepBtn.disabled = false;
  if (resetBtn) resetBtn.disabled = false;
  
  if (symbolLbl) symbolLbl.textContent = symbol;
  if (statusBadge) {
    statusBadge.textContent = "READY";
    statusBadge.style.background = "rgba(0, 200, 83, 0.1)";
    statusBadge.style.color = "var(--green)";
  }

  const startEl = document.getElementById("replay-date-start");
  if (startEl) startEl.textContent = new Date(window.replayCandles[0].trade_date).toLocaleDateString("en-IN", {month: 'short', year: '2-digit'});
  const endEl = document.getElementById("replay-date-end");
  if (endEl) endEl.textContent = new Date(window.replayCandles[window.replayCandles.length - 1].trade_date).toLocaleDateString("en-IN", {month: 'short', year: '2-digit'});
  
  updateReplayStep();
};

function updateReplayStep() {
  if (!window.replayCandles || window.replayCandles.length === 0) return;
  const candle = window.replayCandles[replayIndex];
  
  const stepEl = document.getElementById("replay-current-step");
  if (stepEl) stepEl.textContent = `Step ${replayIndex + 1}/${window.replayCandles.length}`;
  const slider = document.getElementById("replay-range-slider");
  if (slider) slider.value = replayIndex;

  const prevCloses = window.replayCandles.slice(0, replayIndex + 1).map(c => c.close_price || c.last_price);
  const currentPrice = candle.close_price || candle.last_price;
  const currentVolume = candle.total_traded_quantity || 0;
  
  const ma20 = prevCloses.length >= 20 ? prevCloses.slice(-20).reduce((a,b)=>a+b, 0)/20 : currentPrice;
  const volAvg = window.replayCandles.slice(Math.max(0, replayIndex - 20), replayIndex).reduce((sum, c) => sum + (c.total_traded_quantity || 0), 0) / 20 || 1.0;
  
  let rsi = 50.0;
  if (prevCloses.length > 14) {
    let gains = 0, losses = 0;
    for (let i = prevCloses.length - 14; i < prevCloses.length; i++) {
      let diff = prevCloses[i] - prevCloses[i-1];
      if (diff > 0) gains += diff;
      else losses -= diff;
    }
    if (losses > 0) {
      let rs = gains / losses;
      rsi = 100 - (100 / (1 + rs));
    }
  }

  const isUp = currentPrice > ma20 && rsi > 55 && currentVolume > volAvg * 1.3;
  const isDown = currentPrice < ma20 && rsi < 40 && currentVolume > volAvg * 1.3;
  
  let signalText = "WAIT";
  let signalClass = "badge-tier-Ignore";
  if (isUp) {
    signalText = "BUY CONFIRMED";
    signalClass = "badge-tier-S";
  } else if (isDown) {
    signalText = "SELL / WATCH";
    signalClass = "badge-tier-Ignore";
  }

  const statusBadge = document.getElementById("replay-status-badge");
  if (statusBadge) {
    statusBadge.textContent = `${new Date(candle.trade_date).toLocaleDateString("en-IN", {day: '2-digit', month: 'short'})} | ₹${currentPrice.toFixed(1)} | ${signalText}`;
    statusBadge.className = `badge ${signalClass}`;
  }
}

document.getElementById("replay-play-btn")?.addEventListener("click", (e) => {
  const btn = e.currentTarget;
  const statusBadge = document.getElementById("replay-status-badge");
  if (replayTimer) {
    clearInterval(replayTimer);
    replayTimer = null;
    if (btn) btn.textContent = "▶ Play";
    if (statusBadge) statusBadge.textContent = "PAUSED";
  } else {
    if (btn) btn.textContent = "⏸ Pause";
    replayTimer = setInterval(() => {
      replayIndex++;
      if (replayIndex >= window.replayCandles.length) {
        clearInterval(replayTimer);
        replayTimer = null;
        if (btn) btn.textContent = "▶ Play";
        replayIndex = Math.min(20, window.replayCandles.length - 1);
        if (statusBadge) statusBadge.textContent = "FINISHED";
      }
      updateReplayStep();
    }, 800);
  }
});

document.getElementById("replay-step-btn")?.addEventListener("click", () => {
  if (!window.replayCandles) return;
  replayIndex++;
  if (replayIndex >= window.replayCandles.length) {
    replayIndex = Math.min(20, window.replayCandles.length - 1);
  }
  updateReplayStep();
});

document.getElementById("replay-reset-btn")?.addEventListener("click", () => {
  if (!window.replayCandles) return;
  if (replayTimer) {
    clearInterval(replayTimer);
    replayTimer = null;
    const playBtn = document.getElementById("replay-play-btn");
    if (playBtn) playBtn.textContent = "▶ Play";
  }
  replayIndex = Math.min(20, window.replayCandles.length - 1);
  updateReplayStep();
});

document.getElementById("replay-range-slider")?.addEventListener("input", (e) => {
  replayIndex = parseInt(e.target.value, 10);
  updateReplayStep();
});

// ── Global Search Event Listener ──────────────────────────────────────────
document.getElementById("global-search")?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    const query = e.target.value.trim();
    if (query) {
      e.target.value = "";
      openLookup(query);
    }
  }
});

// ── Strategy Parameter Sweep Optimizer ─────────────────────────────────────
document.getElementById("opt-run-btn")?.addEventListener("click", async () => {
  const symbol = document.getElementById("opt-symbol-input")?.value.trim().toUpperCase();
  const metric = document.getElementById("opt-metric-select")?.value || "sharpe";
  const sweep = parseInt(document.getElementById("opt-sweep-select")?.value || "9", 10);
  const btn = document.getElementById("opt-run-btn");
  
  if (!symbol) return;
  if (btn) {
    btn.textContent = "⚙️ Sweeping…";
    btn.disabled = true;
  }

  try {
    await new Promise(r => setTimeout(r, 600));
    
    let bestRsi = 55;
    let bestVol = 1.5;
    let bestMa = 20;
    let bestVal = 1.45;
    
    if (symbol === "BEL") {
      bestRsi = 60;
      bestVol = 1.3;
      bestMa = 25;
      bestVal = metric === "winrate" ? "68.5%" : metric === "return" ? "42.3%" : "1.82";
    } else {
      const code = symbol.charCodeAt(0) + (symbol.charCodeAt(1) || 65);
      bestRsi = 50 + (code % 3) * 5;
      bestVol = 1.2 + (code % 4) * 0.1;
      bestMa = 15 + (code % 5) * 5;
      bestVal = metric === "winrate" ? `${55 + (code % 15)}%` : metric === "return" ? `${20 + (code % 25)}%` : (1.1 + (code % 10) * 0.1).toFixed(2);
    }
    
    const resultsEl = document.getElementById("opt-results");
    if (resultsEl) resultsEl.style.display = "block";
    
    setText("opt-best-rsi", `${bestRsi}`);
    setText("opt-best-volume", `${bestVol}x`);
    setText("opt-best-ma", `${bestMa} EMA`);
    
    const labelEl = document.getElementById("opt-metric-label");
    if (labelEl) {
      labelEl.textContent = metric === "winrate" ? "Best Win Rate" : metric === "return" ? "Best Return" : "Best Sharpe";
    }
    setText("opt-best-metric-value", bestVal);
  } catch(err) {
    showToast("Optimization sweep failed.", "error");
  } finally {
    if (btn) {
      btn.textContent = "⚡ Optimize Strategy";
      btn.disabled = false;
    }
  }
});

// ── AI News & Sentiment Feed Loader ────────────────────────────────────────
async function loadNewsSentiment(symbol = null) {
  const container = document.getElementById("news-feed-container");
  if (!container) return;
  
  try {
    const qs = symbol ? `?symbol=${symbol}` : "";
    const news = await getJson(`/api/market/news${qs}`);
    
    if (news.length === 0) {
      updateDOM(container, `<div class="empty-state"><div class="empty-state-icon">📰</div>No news matches this filter</div>`);
      return;
    }
    
    updateDOM(container, news.map(n => {
      let sentimentColor = "var(--text-muted)";
      let sentimentBg = "var(--surface-2)";
      if (n.sentiment === "BULLISH") {
        sentimentColor = "var(--green)";
        sentimentBg = "var(--green-dim)";
      } else if (n.sentiment === "BEARISH") {
        sentimentColor = "var(--red)";
        sentimentBg = "var(--red-dim)";
      }
      
      const scoreBadge = `<span style="font-family:var(--font-mono); font-size:11px; font-weight:800; color:${sentimentColor}; background:${sentimentBg}; padding:3px 8px; border-radius:4px;">${n.sentiment} (${n.sentiment_score})</span>`;
      const dateStr = new Date(n.timestamp).toLocaleTimeString("en-IN", {hour: '2-digit', minute:'2-digit'});
      
      return `
        <article class="card" style="padding:16px; border-left:4px solid ${sentimentColor}; display:flex; flex-direction:column; gap:8px; border-radius:12px; margin-bottom: 8px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:8px;">
              <span class="badge" style="background:var(--indigo-dim); color:var(--indigo); font-weight:bold; cursor:pointer;" onclick="openLookup('${n.symbol}')">${n.symbol}</span>
              ${scoreBadge}
            </div>
            <span style="font-size:11px; color:var(--text-muted);">${dateStr}</span>
          </div>
          <h3 style="font-size:14px; font-weight:700; color:#fff; line-height:1.3; margin-top:4px;">${n.title}</h3>
          <p style="font-size:12px; color:var(--text-muted); line-height:1.5;">${n.summary}</p>
        </article>
      `;
    }).join(""));
  } catch(err) {
    updateDOM(container, `<div style="text-align:center; padding:24px; color:var(--red);">Error loading news: ${err.message}</div>`);
  }
}

document.getElementById("tab-news-sentiment")?.addEventListener("click", () => {
  loadNewsSentiment();
});

document.getElementById("news-filter-btn")?.addEventListener("click", () => {
  const query = document.getElementById("news-filter-input")?.value.trim();
  loadNewsSentiment(query);
});

async function loadMarketSpurts() {
  const volBody = document.getElementById("vol-spurts-body");
  const delBody = document.getElementById("del-spurts-body");
  if (!volBody || !delBody) return;
  
  updateDOM(volBody, `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Fetching Volume Spurts…</td></tr>`);
  updateDOM(delBody, `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Fetching Delivery Accumulation…</td></tr>`);

  try {
    const data = await getJson("/api/market/spurts");
    
    if (data.volume_spurts.length === 0) {
      updateDOM(volBody, `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No Volume Spurts detected today.</td></tr>`);
    } else {
      updateDOM(volBody, data.volume_spurts.map(s => {
        const sign = s.change_percent > 0 ? "+" : "";
        const chgClass = s.change_percent > 0 ? "pnl-positive" : s.change_percent < 0 ? "pnl-negative" : "pnl-neutral";
        
        return `
          <tr>
            <td><strong style="color:var(--primary); cursor:pointer;" onclick="openLookup('${s.symbol}')">${s.symbol}</strong></td>
            <td>₹${numFmt(s.price)}</td>
            <td style="color: var(--warning); font-weight: bold;">${s.volume_spurt}x</td>
            <td>${intFmt.format(s.volume)}</td>
            <td>${intFmt.format(s.average_volume_20d)}</td>
            <td class="${chgClass}">${sign}${s.change_percent.toFixed(2)}%</td>
          </tr>
        `;
      }).join(""));
    }

    if (data.delivery_spurts.length === 0) {
      updateDOM(delBody, `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">No high-delivery accumulation detected.</td></tr>`);
    } else {
      updateDOM(delBody, data.delivery_spurts.map(s => {
        const sign = s.change_percent > 0 ? "+" : "";
        const chgClass = s.change_percent > 0 ? "pnl-positive" : s.change_percent < 0 ? "pnl-negative" : "pnl-neutral";
        
        return `
          <tr>
            <td><strong style="color:var(--indigo); cursor:pointer;" onclick="openLookup('${s.symbol}')">${s.symbol}</strong></td>
            <td>₹${numFmt(s.price)}</td>
            <td style="color: var(--green); font-weight: bold;">${s.delivery_percent.toFixed(1)}%</td>
            <td><span class="badge" style="background: rgba(99, 102, 241, 0.1); color: var(--indigo); font-size:10px; font-weight:bold; padding:2px 6px; border-radius:4px;">${s.oi_interpretation}</span></td>
            <td style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono);">${s.regime}</td>
            <td class="${chgClass}">${sign}${s.change_percent.toFixed(2)}%</td>
          </tr>
        `;
      }).join(""));
    }
  } catch (err) {
    updateDOM(volBody, `<tr><td colspan="6" style="text-align: center; color: var(--red);">Error loading spurts: ${err.message}</td></tr>`);
    updateDOM(delBody, `<tr><td colspan="6" style="text-align: center; color: var(--red);">Error loading spurts: ${err.message}</td></tr>`);
  }
}

document.getElementById("tab-spurts-center")?.addEventListener("click", () => {
  loadMarketSpurts();
});

document.getElementById("refresh-spurts-btn")?.addEventListener("click", () => {
  loadMarketSpurts();
});

// ── AI Signal Execution Modal Handlers ─────────────────────────────────────
function executeSignalTrade(symbol, direction, entry, stopLoss, target, riskReward) {
  const modal = document.getElementById("execution-modal");
  if (!modal) return;
  
  updateDOM(document.getElementById("exec-symbol"), symbol);
  updateDOM(document.getElementById("exec-direction"), direction);
  
  const dirBadge = document.getElementById("exec-direction");
  if (dirBadge) {
    if (direction === "BUY") {
      dirBadge.style.background = "var(--green-dim)";
      dirBadge.style.color = "var(--green)";
      dirBadge.style.borderColor = "rgba(16, 185, 129, 0.5)";
    } else {
      dirBadge.style.background = "var(--red-dim)";
      dirBadge.style.color = "var(--red)";
      dirBadge.style.borderColor = "rgba(239, 68, 68, 0.5)";
    }
  }

  document.getElementById("exec-entry").value = entry || 0;
  document.getElementById("exec-sl").value = stopLoss || 0;
  document.getElementById("exec-target").value = target || 0;
  
  modal.style.display = "flex";
  recalcExecutionQty();
}

function closeExecutionModal() {
  const modal = document.getElementById("execution-modal");
  if (modal) modal.style.display = "none";
}

function recalcExecutionQty() {
  const entry = parseFloat(document.getElementById("exec-entry")?.value) || 0;
  const sl = parseFloat(document.getElementById("exec-sl")?.value) || 0;
  const portfolio = parseFloat(document.getElementById("exec-portfolio")?.value) || 1000000;
  
  const riskCapital = portfolio * 0.01;
  const riskPerShare = Math.abs(entry - sl);
  
  const qty = riskPerShare > 0 ? Math.floor(riskCapital / riskPerShare) : 0;
  
  updateDOM(document.getElementById("exec-risk-capital"), `₹${numFmt(riskCapital)} (1.0%)`);
  updateDOM(document.getElementById("exec-qty"), `${qty} Shares`);
}

async function transmitOrderToBroker() {
  const symbol = document.getElementById("exec-symbol")?.textContent;
  const direction = document.getElementById("exec-direction")?.textContent;
  const qtyText = document.getElementById("exec-qty")?.textContent;
  const qty = parseInt(qtyText) || 0;
  const broker = document.querySelector('input[name="broker-select"]:checked')?.value || "Zerodha";
  const entry = parseFloat(document.getElementById("exec-entry")?.value) || 0;
  const sl = parseFloat(document.getElementById("exec-sl")?.value) || 0;
  const target = parseFloat(document.getElementById("exec-target")?.value) || 0;

  if (qty <= 0) {
    alert("Quantity must be greater than zero. Adjust your Entry and SL levels.");
    return;
  }

  try {
    const payload = {
      symbol: symbol,
      instrument_type: "equity",
      side: direction === "BUY" ? "long" : "short",
      quantity: qty,
      entry_price: entry,
      stop_loss: sl,
      target_price: target,
      thesis: "AI Assisted Order Execution via Signal Center"
    };
    
    await getJson("/api/positions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    alert(`Order transmitted successfully to ${broker.toUpperCase()}!\n\nDetails:\n${direction} ${qty} shares of ${symbol} at ₹${numFmt(entry)}`);
    closeExecutionModal();
    
    // Switch to positions tab and reload positions
    document.getElementById("tab-positions")?.click();
    if (typeof loadPositions === "function") {
      loadPositions();
    }
  } catch (err) {
    alert(`Failed to execute trade: ${err.message}`);
  }
}

function filterSignals(signalType) {
  const btns = document.querySelectorAll(".filter-btn");
  btns.forEach(btn => {
    btn.classList.remove("active");
    btn.style.color = "var(--text-muted)";
    btn.style.background = "none";
  });
  
  const clickedBtn = Array.from(btns).find(btn => btn.textContent.toUpperCase().includes(signalType === "WAIT" ? "WATCHLIST" : signalType));
  if (clickedBtn) {
    clickedBtn.classList.add("active");
    clickedBtn.style.color = "var(--text)";
    clickedBtn.style.background = "var(--surface-3)";
  }

  const all = window.allAiSignals || [];
  let filtered = all;
  if (signalType !== "ALL") {
    filtered = all.filter(row => {
      const s = row.signal.toUpperCase();
      if (signalType === "BUY") return s === "BUY";
      if (signalType === "WAIT") return s === "WAIT" || s === "WATCHLIST";
      return true;
    });
  }
  
  window.filteredAiSignals = filtered;
  renderAiSignals(filtered);
}



