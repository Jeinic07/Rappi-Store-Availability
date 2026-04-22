// ══════════════════════════════════════════
// CONFIG & THEME
// ══════════════════════════════════════════
const API = 'http://localhost:5000/api';
const DAYS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

let chatHistory = [];
let tsChart, hourChart, dayChart, heatChart, healthChart;

const savedTheme = localStorage.getItem('theme') || 'light';
if (savedTheme === 'dark') document.body.setAttribute('data-theme', 'dark');

function updateChartDefaults() {
  const isDark = document.body.getAttribute('data-theme') === 'dark';
  Chart.defaults.color = isDark ? '#6b6b8a' : '#667085';
  Chart.defaults.borderColor = isDark ? '#2a2a3d' : '#eaecf0';
  Chart.defaults.font.family = "'DM Sans', sans-serif";
  document.getElementById('themeIcon').textContent = isDark ? '☀️' : '🌙';
}

async function toggleTheme() {
  const isDark = document.body.getAttribute('data-theme') === 'dark';
  const newTheme = isDark ? 'light' : 'dark';
  document.body.setAttribute('data-theme', newTheme);
  localStorage.setItem('theme', newTheme);
  document.getElementById('loadingOverlay').style.display = 'flex';
  await init();
}

// ══════════════════════════════════════════
// LOADER
// ══════════════════════════════════════════
function setLoader(pct, msg) {
  document.getElementById('loaderFill').style.width = pct + '%';
  document.getElementById('loaderMsg').textContent = msg;
}

async function init() {
  updateChartDefaults();
  setLoader(5,  'Conectando con la base de datos...');
  await loadSummary();
  setLoader(18, 'Calculando índice de salud...');
  await loadHealthScore();
  setLoader(32, 'Cargando serie de tiempo...');
  await loadTimeseries();
  setLoader(50, 'Procesando datos por hora...');
  await loadByHour();
  setLoader(65, 'Calculando tendencias diarias...');
  await loadByDay();
  setLoader(78, 'Generando heatmap...');
  await loadHeatmap();
  setLoader(90, 'Detectando anomalías e impacto...');
  await loadAnomalies();
  setLoader(100, 'Listo.');
  await sleep(400);
  document.getElementById('loadingOverlay').style.display = 'none';
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

// ══════════════════════════════════════════
// SUMMARY / KPIs
// ══════════════════════════════════════════
async function loadSummary() {
  const d = await fetchJSON(`${API}/summary`);
  const from = d.date_from?.slice(0, 10) || '—';
  const to = d.date_to?.slice(0, 10) || '—';
  document.getElementById('kpiPeriod').textContent = `${from} → ${to}`;
  document.getElementById('kpiAvg').textContent = fmt(d.avg_stores);
  document.getElementById('kpiMax').textContent = fmt(d.max_stores);
  document.getElementById('kpiMin').textContent = fmt(d.min_stores);
}


// ══════════════════════════════════════════
// SERIE DE TIEMPO
// ══════════════════════════════════════════
async function loadTimeseries() {
  const from = document.getElementById('filterFrom').value;
  const to = document.getElementById('filterTo').value;
  let url = `${API}/timeseries`;
  const params = [];
  if (from) params.push(`date_from=${from} 00:00:00`);
  if (to) params.push(`date_to=${to} 23:59:59`);
  if (params.length) url += '?' + params.join('&');

  const rows = await fetchJSON(url);
  const labels = rows.map(r => r.minute?.slice(0, 16) || '');
  const data = rows.map(r => r.avg_stores);

  const ctx = document.getElementById('timeseriesChart').getContext('2d');
  const isDark = document.body.getAttribute('data-theme') === 'dark';

  const grad = ctx.createLinearGradient(0, 0, 0, 280);
  grad.addColorStop(0, isDark ? 'rgba(255,69,0,0.3)' : 'rgba(255,69,0,0.15)');
  grad.addColorStop(1, 'rgba(255,69,0,0)');

  if (tsChart) tsChart.destroy();
  tsChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Tiendas visibles',
        data,
        borderColor: '#ff4500',
        backgroundColor: grad,
        borderWidth: 1.5,
        pointRadius: 0,
        fill: true,
        tension: 0.3,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false }, tooltip: {
          callbacks: { label: ctx => ' ' + fmt(ctx.parsed.y) + ' tiendas' }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, maxRotation: 0, font: { size: 10 } } },
        y: { grid: { display: false }, ticks: { callback: v => fmt(v), font: { size: 10 } } }
      }
    }
  });
}

function updateDayLabel(days) {
  document.getElementById('dayBadge').textContent = days == 1 ? '1 día' : `${days} días`;
}

/**
 * Calcula date_from como (date_to - days + 1) usando la fecha máxima
 * disponible en los KPIs o hoy si aún no se ha cargado.
 */
function applyDayRange(days) {
  const toRaw = document.getElementById('filterTo').value;
  const base  = toRaw ? new Date(toRaw) : new Date();
  const from  = new Date(base);
  from.setDate(base.getDate() - Number(days) + 1);
  document.getElementById('filterFrom').value = from.toISOString().slice(0, 10);
  loadTimeseries();
}

/**
 * Cuando el usuario cambia los campos de fecha manualmente,
 * sincroniza el slider con el rango resultante (si cae en 1-10 días).
 */
function syncRangeFromDates() {
  const from = document.getElementById('filterFrom').value;
  const to   = document.getElementById('filterTo').value;
  if (from && to) {
    const diff = Math.round((new Date(to) - new Date(from)) / 86400000) + 1;
    const clamped = Math.max(1, Math.min(10, diff));
    document.getElementById('dayRange').value = clamped;
    updateDayLabel(clamped);
  }
}

function resetFilters() {
  document.getElementById('dayRange').value = '10';
  updateDayLabel(10);
  // Resetear a rango completo (sin filtro de fecha)
  document.getElementById('filterFrom').value = '';
  document.getElementById('filterTo').value = '';
  loadTimeseries();
}


// ══════════════════════════════════════════
// POR HORA DEL DÍA
// ══════════════════════════════════════════
async function loadByHour() {
  const rows = await fetchJSON(`${API}/by_hour`);
  const labels = rows.map(r => `${String(r.hour_of_day).padStart(2, '0')}h`);
  const data = rows.map(r => r.avg_stores);

  const maxVal = Math.max(...data);
  const colors = data.map(v => {
    const ratio = v / maxVal;
    return `rgba(255,${Math.round(69 + (200 - 69) * ratio)},${Math.round(ratio * 50)},0.8)`;
  });

  if (hourChart) hourChart.destroy();
  hourChart = new Chart(document.getElementById('byHourChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Promedio tiendas',
        data,
        backgroundColor: colors,
        borderRadius: 3,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false }, tooltip: {
          callbacks: { label: ctx => ' ' + fmt(ctx.parsed.y) }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 9 } } },
        y: { grid: { display: false }, ticks: { callback: v => fmtK(v), font: { size: 9 } } }
      }
    }
  });
}


// ══════════════════════════════════════════
// TENDENCIA DIARIA
// ══════════════════════════════════════════
async function loadByDay() {
  const rows = await fetchJSON(`${API}/by_day`);
  const labels = rows.map(r => r.day?.slice(5) || '');
  const avg = rows.map(r => r.avg_stores);
  const min = rows.map(r => r.min_stores);
  const max = rows.map(r => r.max_stores);

  const style = getComputedStyle(document.body);
  const cGreen = style.getPropertyValue('--green').trim();
  const cAccent = style.getPropertyValue('--accent').trim();
  const cRed = style.getPropertyValue('--red').trim();

  if (dayChart) dayChart.destroy();
  dayChart = new Chart(document.getElementById('byDayChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: 'Máx', data: max, borderColor: cGreen, borderWidth: 1, borderDash: [3, 3], pointRadius: 0, fill: false },
        { label: 'Prom', data: avg, borderColor: cAccent, borderWidth: 2, pointRadius: 3, pointBackgroundColor: cAccent, fill: false },
        { label: 'Mín', data: min, borderColor: cRed, borderWidth: 1, borderDash: [3, 3], pointRadius: 0, fill: false },
      ]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { font: { size: 10 }, boxWidth: 12 } }, tooltip: {
          callbacks: { label: ctx => ` ${ctx.dataset.label}: ${fmt(ctx.parsed.y)}` }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { font: { size: 9 } } },
        y: { grid: { display: false }, ticks: { callback: v => fmtK(v), font: { size: 9 } } }
      }
    }
  });
}


// ══════════════════════════════════════════
// HEATMAP (Canvas custom)
// ══════════════════════════════════════════
async function loadHeatmap() {
  const rows = await fetchJSON(`${API}/heatmap`);

  // Build matrix[weekday][hour]
  const matrix = Array.from({ length: 7 }, () => Array(24).fill(null));
  rows.forEach(r => { matrix[r.weekday][r.hour_of_day] = r.avg_stores; });

  const allVals = rows.map(r => r.avg_stores).filter(Boolean);
  const minV = Math.min(...allVals), maxV = Math.max(...allVals);

  const canvas = document.getElementById('heatmapChart');
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.offsetWidth || 800;
  const H = 160;
  canvas.width = W * dpr;
  canvas.height = H * dpr;
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);

  const labelW = 32, labelH = 20;
  const cellW = (W - labelW) / 24;
  const cellH = (H - labelH) / 7;

  // Draw cells
  for (let d = 0; d < 7; d++) {
    for (let h = 0; h < 24; h++) {
      const val = matrix[d][h];
      const ratio = val != null ? (val - minV) / (maxV - minV) : 0;
      const isDark = document.body.getAttribute('data-theme') === 'dark';

      if (isDark) {
        const r = Math.round(20 + ratio * 235);
        const g = Math.round(20 + ratio * 49);
        const b = Math.round(30 + ratio * (ratio > 0.5 ? 0 : 20));
        ctx.fillStyle = val != null ? `rgb(${r},${g},${b})` : '#1a1a26';
      } else {
        const maxR = 255, maxG = 69, maxB = 0;
        const minR = 255, minG = 236, minB = 229;
        const rc = Math.round(minR + ratio * (maxR - minR));
        const gc = Math.round(minG + ratio * (maxG - minG));
        const bc = Math.round(minB + ratio * (maxB - minB));
        ctx.fillStyle = val != null ? `rgb(${rc},${gc},${bc})` : '#eaecf0';
      }
      ctx.fillRect(labelW + h * cellW, labelH + d * cellH, cellW - 1, cellH - 1);
    }
  }

  // Hour labels
  ctx.fillStyle = '#6b6b8a';
  ctx.font = '9px Space Mono, monospace';
  ctx.textAlign = 'center';
  for (let h = 0; h < 24; h += 3) {
    ctx.fillText(`${String(h).padStart(2, '0')}h`, labelW + h * cellW + cellW / 2, labelH - 5);
  }

  // Day labels
  ctx.textAlign = 'right';
  ctx.font = '9px Space Mono, monospace';
  for (let d = 0; d < 7; d++) {
    ctx.fillText(DAYS[d], labelW - 4, labelH + d * cellH + cellH / 2 + 3);
  }
}


// ══════════════════════════════════════════
// ANOMALÍAS
// ══════════════════════════════════════════
async function loadAnomalies() {
  const rows = await fetchJSON(`${API}/anomalies`);
  // Guardar para el simulador de impacto
  window.anomalyData = rows;
  recalcImpact();

  const tbody = document.getElementById('anomalyBody');
  if (!rows.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--muted);padding:1rem">No se detectaron anomalías significativas.</td></tr>';
    return;
  }
  tbody.innerHTML = rows.slice(0, 30).map(r => {
    const pct = r.pct_diff;
    const cls = pct < -30 ? 'red' : 'yellow';
    return `<tr>
      <td>${r.recorded_at_local}</td>
      <td>${fmt(r.visible_stores)}</td>
      <td>${fmt(r.avg_hour)}</td>
      <td><span class="badge ${cls}">${pct}%</span></td>
    </tr>`;
  }).join('');
}


// ══════════════════════════════════════════
// CHATBOT
// ══════════════════════════════════════════
function sendSuggestion(btn) {
  document.getElementById('chatInput').value = btn.textContent;
  document.getElementById('suggestedQueries').style.display = 'none';
  sendChat();
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const text = input.value.trim();
  if (!text) return;

  const apiKey = document.getElementById('apiKeyInput').value.trim();
  if (!apiKey) {
    appendMsg('assistant', '⚠️ Por favor ingresa tu API key de Anthropic en la parte superior para usar el chatbot.');
    return;
  }

  appendMsg('user', text);
  input.value = '';
  input.style.height = '48px';

  chatHistory.push({ role: 'user', content: text });

  const sendBtn = document.getElementById('sendBtn');
  sendBtn.disabled = true;

  // Thinking indicator
  const thinkId = 'think_' + Date.now();
  const thinkEl = document.createElement('div');
  thinkEl.id = thinkId;
  thinkEl.className = 'msg assistant';
  thinkEl.innerHTML = `<div class="msg-role">ASISTENTE</div>
    <div class="msg-bubble"><div class="thinking"><span></span><span></span><span></span></div></div>`;
  document.getElementById('chatMessages').appendChild(thinkEl);
  scrollChat();

  try {
    const resp = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey, messages: chatHistory })
    });
    const data = await resp.json();

    thinkEl.remove();

    if (data.error) {
      appendMsg('assistant', `❌ Error: ${data.error}`);
    } else {
      appendMsg('assistant', data.reply);
      chatHistory.push({ role: 'assistant', content: data.reply });
    }
  } catch (e) {
    thinkEl.remove();
    appendMsg('assistant', '❌ No se pudo conectar con el servidor. ¿Está corriendo app.py?');
  }

  sendBtn.disabled = false;
}

function appendMsg(role, text) {
  const div = document.createElement('div');
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="msg-role">${role === 'user' ? 'TÚ' : 'ASISTENTE'}</div>
    <div class="msg-bubble">${escapeHtml(text)}</div>`;
  document.getElementById('chatMessages').appendChild(div);
  scrollChat();
}

function scrollChat() {
  const el = document.getElementById('chatMessages');
  el.scrollTop = el.scrollHeight;
}

function escapeHtml(t) {
  return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}


// ══════════════════════════════════════════
// UTILS
// ══════════════════════════════════════════
function fmt(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('es-CO');
}

function fmtK(n) {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
  if (n >= 1_000) return (n / 1_000).toFixed(0) + 'K';
  return n;
}

async function fetchJSON(url) {
  const r = await fetch(url);
  return r.json();
}


// ══════════════════════════════════════════
// ÍNDICE DE SALUD OPERACIONAL
// ══════════════════════════════════════════
async function loadHealthScore() {
  const d = await fetchJSON(`${API}/health_score`);
  const score = d.score;
  const isDark = document.body.getAttribute('data-theme') === 'dark';

  let color, label;
  if (score >= 75) { color = '#00d084'; label = 'SALUDABLE'; }
  else if (score >= 50) { color = '#ffc857'; label = 'MODERADO'; }
  else { color = '#ff3b5c'; label = 'CRÍTICO'; }

  const trackColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)';

  const ctx = document.getElementById('healthGauge').getContext('2d');
  if (healthChart) healthChart.destroy();
  healthChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      datasets: [{
        data: [score, 100 - score],
        backgroundColor: [color, trackColor],
        borderWidth: 0,
        borderRadius: score < 100 ? 5 : 0,
      }]
    },
    options: {
      cutout: '74%',
      rotation: -90,
      circumference: 180,
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      animation: { duration: 900, easing: 'easeOutQuart' }
    }
  });

  document.getElementById('healthNumber').textContent = score;
  document.getElementById('healthNumber').style.color = color;
  document.getElementById('healthLabel').textContent = label;
  document.getElementById('healthLabel').style.color = color;

  setBar('barStability',   'pctStability',   d.stability);
  setBar('barReliability', 'pctReliability', d.reliability);
  setBar('barCoverage',    'pctCoverage',    d.coverage);

  document.getElementById('healthMeta').textContent =
    `${fmt(d.total_records)} registros analizados · ${fmt(d.anomaly_count)} eventos de caída`;
}

function setBar(barId, pctId, value) {
  const bar = document.getElementById(barId);
  const pct = document.getElementById(pctId);
  // Pequeño delay para que la animación se vea
  setTimeout(() => { bar.style.width = value + '%'; }, 80);
  pct.textContent = value + '%';
  if (value >= 75) bar.style.background = 'var(--green)';
  else if (value >= 50) bar.style.background = 'var(--yellow)';
  else bar.style.background = 'var(--red)';
}


// ══════════════════════════════════════════
// SIMULADOR DE IMPACTO DE NEGOCIO
// ══════════════════════════════════════════
function recalcImpact() {
  const rows = window.anomalyData || [];
  const ticket = Number(document.getElementById('simTicket').value);
  const ordersPerHour = Number(document.getElementById('simOrders').value);
  const ordersPerMin = ordersPerHour / 60;

  document.getElementById('simTicketVal').textContent =
    '$' + ticket.toLocaleString('es-CO');
  document.getElementById('simOrdersVal').textContent =
    ordersPerHour.toFixed(1);

  let totalRevenue = 0;
  let totalLostStores = 0;

  rows.forEach(r => {
    const lostStores = Math.max(0, (r.avg_hour || 0) - (r.visible_stores || 0));
    totalRevenue   += lostStores * ordersPerMin * ticket;
    totalLostStores += lostStores;
  });

  const avgLost = rows.length ? Math.round(totalLostStores / rows.length) : 0;

  document.getElementById('impactRevenue').textContent = formatCOP(totalRevenue);
  document.getElementById('impactEvents').textContent  = fmt(rows.length);
  document.getElementById('impactStores').textContent  = fmt(avgLost);
  document.getElementById('impactMinutes').textContent = fmt(rows.length);
}

function formatCOP(n) {
  if (n >= 1_000_000_000) return '$' + (n / 1_000_000_000).toFixed(2) + 'B';
  if (n >= 1_000_000)     return '$' + (n / 1_000_000).toFixed(1) + 'M';
  return '$' + Math.round(n).toLocaleString('es-CO');
}


// ══════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════
window.addEventListener('load', init);
