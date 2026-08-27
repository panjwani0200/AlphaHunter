// ==========================================
// OUTPERFORM TODAY MODULE
// ==========================================

let opDashboardData = null;
let opRefreshInterval = null;

// ── DOM Helpers ──
function getEl(id) { return document.getElementById(id); }
function setHtml(id, html) { const el = getEl(id); if (el) el.innerHTML = html; }
function valClass(val) {
  if (typeof val === 'string') {
    const upper = val.toUpperCase();
    if (upper.includes("BULLISH") || upper.includes("STRONG") || upper.includes("UPTREND") || upper.includes("OUTPERFORMING")) return "val-bullish";
    if (upper.includes("BEARISH") || upper.includes("WEAK") || upper.includes("UNDERPERFORMING")) return "val-bearish";
    return "val-neutral";
  }
  if (typeof val === 'number') {
    return val > 0 ? "val-bullish" : (val < 0 ? "val-bearish" : "val-neutral");
  }
  return "";
}

// ── Dashboard Logic ──
async function loadOutperformDashboard() {
  setHtml("outperform-picks-grid", `<div style="color:var(--text-muted);"><i class="lucide-loader animate-spin"></i> Fetching AI Rankings...</div>`);
  try {
    const res = await fetch("/api/outperform/dashboard");
    if (!res.ok) throw new Error("Failed to load Outperform Dashboard");
    const data = await res.json();
    opDashboardData = data;
    renderOutperformDashboard();
  } catch (err) {
    console.error(err);
    setHtml("outperform-picks-grid", `<div style="color:var(--red);">Error loading dashboard. Ensure backend is running.</div>`);
  }
}

function renderOutperformDashboard() {
  if (!opDashboardData) return;
  const h = opDashboardData.market_health;
  
  // Render Health
  setHtml("op-market-health", `
    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
      <span>Sentiment</span><span class="${valClass(h.sentiment)}">${h.sentiment}</span>
    </div>
    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
      <span>AI Market Score</span><strong style="color:#f59e0b;">${h.overall_market_score}/100</strong>
    </div>
    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
      <span>Nifty Trend</span><span class="${valClass(h.nifty_trend)}">${h.nifty_trend}</span>
    </div>
    <div style="display:flex; justify-content:space-between;">
      <span>FII Activity</span><span>${h.fii_activity}</span>
    </div>
  `);
  
  // Render Sector Rotation Heatmap
  let heatmapHtml = '<div style="display:grid; grid-template-columns: 1fr 1fr; gap: 4px; margin-top: 4px;">';
  if (h.sector_heatmap) {
    for (const [sector, change] of Object.entries(h.sector_heatmap)) {
        const bg = change > 0 ? "rgba(16, 185, 129, 0.1)" : (change < 0 ? "rgba(239, 68, 68, 0.1)" : "rgba(255,255,255,0.05)");
        const color = change > 0 ? "var(--green)" : (change < 0 ? "var(--red)" : "var(--text-muted)");
        const sign = change > 0 ? "+" : "";
        heatmapHtml += `
          <div style="background: ${bg}; padding: 4px 6px; border-radius: 4px; display: flex; justify-content: space-between; font-size: 11px;">
            <span>${sector}</span>
            <strong style="color: ${color};">${sign}${change.toFixed(2)}%</strong>
          </div>
        `;
    }
  }
  heatmapHtml += '</div>';

  setHtml("op-sector-rotation", heatmapHtml);
  
  // Render Breadth
  setHtml("op-market-breadth", `
    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
      <span>A/D Ratio</span><strong class="${valClass(h.advance_decline_ratio - 1)}">${h.advance_decline_ratio}</strong>
    </div>
    <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
      <span>India VIX</span><strong>${h.india_vix}</strong>
    </div>
  `);
  
  // Render AI Picks
  let html = "";
  for (const pick of opDashboardData.top_picks) {
    html += `
      <div class="pick-card" onclick="openOutperformDetail('${pick.symbol}')">
        <div class="pick-card-header">
          <div class="pick-card-symbol">${pick.symbol}</div>
          <div class="pick-card-score">${pick.overall_score}/100</div>
        </div>
        <div class="pick-card-prob">${pick.outperform_probability_pct}% Probability</div>
        <div class="pick-card-metrics">
          <div>Price: ₹${pick.current_price.toFixed(2)}</div>
          <div class="${valClass(pick.today_change_pct)}">Chg: ${pick.today_change_pct.toFixed(2)}%</div>
          <div>Vol: ${(pick.volume/100000).toFixed(1)}L</div>
          <div>VWAP: <span class="${valClass(pick.vwap_status)}">${pick.vwap_status}</span></div>
        </div>
        <div class="pick-card-rec">${pick.ai_recommendation}</div>
      </div>
    `;
  }
  setHtml("outperform-picks-grid", html);
}

// ── Detail View Logic ──
async function openOutperformDetail(symbol) {
  getEl("outperform-dashboard-view").style.display = "none";
  getEl("outperform-detail-view").style.display = "block";
  
  getEl("op-detail-title").textContent = symbol;
  getEl("op-detail-score").textContent = "...";
  getEl("op-detail-prob").textContent = "...";
  setHtml("op-detail-summary", "Loading deep analysis engines...");
  setHtml("op-engines-container", "");
  
  try {
    const res = await fetch(`/api/outperform/analysis/${symbol}`);
    if (!res.ok) throw new Error("Failed to fetch detailed analysis");
    const data = await res.json();
    renderOutperformDetail(data);
  } catch (err) {
    console.error(err);
    setHtml("op-detail-summary", `<span style="color:var(--red);">Failed to load detailed analysis.</span>`);
  }
}

function closeOutperformDetail() {
  getEl("outperform-detail-view").style.display = "none";
  getEl("outperform-dashboard-view").style.display = "block";
}

function renderEngineCard(title, icon, metricsObj) {
  let html = `<div class="engine-card">
    <h4 class="engine-title"><i class="lucide-${icon}" style="width:16px;height:16px;"></i> ${title}</h4>`;
  for (const [key, val] of Object.entries(metricsObj)) {
    const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    let displayVal = val;
    if (typeof val === 'boolean') displayVal = val ? "YES" : "NO";
    if (typeof val === 'number') {
      if (key.includes("pct") || key.includes("percent")) displayVal = val.toFixed(2) + "%";
      else if (val > 1000) displayVal = (val/100000).toFixed(2) + "L";
      else displayVal = val.toFixed(2);
    }
    
    html += `
      <div class="engine-metric">
        <span class="engine-metric-label">${label}</span>
        <span class="engine-metric-value ${valClass(displayVal)}">${displayVal}</span>
      </div>
    `;
  }
  html += `</div>`;
  return html;
}

function renderOutperformDetail(data) {
  getEl("op-detail-score").textContent = `${data.overall_score}/100`;
  getEl("op-detail-prob").textContent = `${data.probability_score}% Probability`;
  setHtml("op-detail-summary", data.ai_summary);
  
  let gridHtml = "";
  
  gridHtml += renderEngineCard("Trend Engine", "trending-up", data.trend);
  gridHtml += renderEngineCard("Price Action Engine", "bar-chart-2", data.price_action);
  gridHtml += renderEngineCard("Volume Engine", "bar-chart", data.volume);
  gridHtml += renderEngineCard("Futures Engine", "fast-forward", data.futures);
  gridHtml += renderEngineCard("Options Engine", "layers", data.option_chain);
  gridHtml += renderEngineCard("Smart Money", "briefcase", data.smart_money);
  gridHtml += renderEngineCard("Momentum Engine", "activity", data.momentum);
  gridHtml += renderEngineCard("Relative Strength", "dumbbell", data.relative_strength);
  gridHtml += renderEngineCard("Liquidity Engine", "droplet", data.liquidity);
  gridHtml += renderEngineCard("Volatility Engine", "zap", data.volatility);
  gridHtml += renderEngineCard("Sector Engine", "pie-chart", data.sector);
  gridHtml += renderEngineCard("Risk Engine", "shield-alert", data.risk);
  
  // Trade Plan gets a special wider card
  gridHtml += `
    <div class="engine-card" style="grid-column: 1 / -1; background: rgba(16,185,129,0.05); border-color: rgba(16,185,129,0.2);">
      <h4 class="engine-title" style="color:var(--green);"><i class="lucide-crosshair"></i> Actionable Trade Plan</h4>
      <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:16px;">
        <div><span class="engine-metric-label">Breakout Entry</span><br><strong style="font-size:18px;">₹${data.trade_plan.breakout_entry}</strong></div>
        <div><span class="engine-metric-label">Pullback Entry</span><br><strong style="font-size:18px;">₹${data.trade_plan.pullback_entry}</strong></div>
        <div><span class="engine-metric-label">Stoploss</span><br><strong style="font-size:18px; color:var(--red);">₹${data.trade_plan.suggested_stoploss}</strong></div>
        <div><span class="engine-metric-label">Target 1</span><br><strong style="font-size:18px; color:var(--green);">₹${data.trade_plan.target_1}</strong></div>
        <div><span class="engine-metric-label">Target 2</span><br><strong style="font-size:18px; color:var(--green);">₹${data.trade_plan.target_2}</strong></div>
        <div><span class="engine-metric-label">R:R Ratio</span><br><strong style="font-size:18px;">${data.trade_plan.risk_reward_ratio}</strong></div>
      </div>
    </div>
  `;
  
  setHtml("op-engines-container", gridHtml);
}

// ── Auto Refresh Hook ──
document.querySelector('.tab[data-panel="outperform"]')?.addEventListener("click", () => {
  if (!opDashboardData) {
    loadOutperformDashboard();
  }
  
  // Setup isolated background loop
  if (!opRefreshInterval) {
    opRefreshInterval = setInterval(() => {
      if (document.getElementById("outperform").classList.contains("is-active")) {
        if (document.getElementById("outperform-dashboard-view").style.display !== "none") {
          loadOutperformDashboard(); // silently refresh
        }
      }
    }, 60000); // refresh every 1 min
  }
});
