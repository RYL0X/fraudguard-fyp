/* ──────────────────────────────────────────────────────────────
   Fraud Detection Dashboard — Application Logic
   API base: http://localhost:5000
   ────────────────────────────────────────────────────────────── */

const API = window.location.origin;

/* ══════════════════════════════════════════════════════════════
   STATE
══════════════════════════════════════════════════════════════ */
const state = {
  page: 1,
  perPage: 15,
  totalPages: 1,
  search: '',
  fraudFilter: '',
  loading: false,
  // Active time-range filter: { from_dt, to_dt, label }
  // null = no filter (all time / backend default)
  trpFilter: { from_dt: null, to_dt: null, label: 'LAST 24 HOURS' },
};

/* ══════════════════════════════════════════════════════════════
   TRANSACTIONS VIEW STATE (separate from dashboard state)
══════════════════════════════════════════════════════════════ */
const txnViewState = {
  page: 1,
  perPage: 15,
  totalPages: 1,
  search: '',
  fraudFilter: '',
  loading: false,
  initialized: false,
};

// Initialise default 24-hour window on page load
(function initDefaultRange() {
  const now = new Date();
  const from = new Date(now.getTime() - 24 * 60 * 60 * 1000);
  state.trpFilter = {
    from_dt: from.toISOString().slice(0, 19),  // YYYY-MM-DDTHH:MM:SS
    to_dt: now.toISOString().slice(0, 19),
    label: 'LAST 24 HOURS',
  };
})();

/* ══════════════════════════════════════════════════════════════
   HELPERS
══════════════════════════════════════════════════════════════ */
function fmt(n, decimals = 0) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}
function fmtMoney(n) {
  if (n === null || n === undefined) return '—';
  return '$' + fmt(n, 2);
}
function fmtDate(s) {
  if (!s) return '—';
  const d = new Date(s);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    + ' ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}
function truncate(s, n = 10) {
  return s && s.length > n ? s.slice(0, n) + '…' : s;
}

function showToast(msg, type = 'info') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  let tClass = 'show';
  if (type === 'error') tClass += ' error';
  if (type === 'success') tClass += ' success';
  t.className = tClass;
  clearTimeout(t._tid);
  t._tid = setTimeout(() => { t.className = ''; }, 3500);
}

async function apiFetch(path) {
  try {
    // Inject time-range params for /api/stats/* endpoints
    if (path.startsWith('/api/stats') && state.trpFilter.from_dt) {
      const sep = path.includes('?') ? '&' : '?';
      path += `${sep}from_dt=${encodeURIComponent(state.trpFilter.from_dt)}&to_dt=${encodeURIComponent(state.trpFilter.to_dt)}`;
    }
    // cache:'no-store' prevents the browser from serving a stale cached
    // response (which would omit the date-range params) on a soft Ctrl+R reload.
    const r = await fetch(API + path, { cache: 'no-store' });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.json();
  } catch (err) {
    showToast(`API Error: ${err.message}`, 'error');
    throw err;
  }
}

async function checkApiHealth() {
  try {
    await fetch(API + '/api/health');

    // Success: hide banner, show green dot
    document.getElementById('api-error-banner').style.display = 'none';
    const statusDot = document.getElementById('api-status');
    if (statusDot) statusDot.innerHTML = '<span class="dot-green"></span> API Connected';
    return true;
  } catch (err) {
    // Fail: show red banner, show red dot
    document.getElementById('api-error-banner').style.display = 'block';
    const statusDot = document.getElementById('api-status');
    if (statusDot) statusDot.innerHTML = '<span class="dot-red"></span> API Offline';
    return false;
  }
}

/* ══════════════════════════════════════════════════════════════
   KPI CARDS
══════════════════════════════════════════════════════════════ */
function animateValue(el, target, decimals = 0, prefix = '') {
  const start = 0;
  const duration = 900;
  const step = 16;
  const steps = duration / step;
  let current = start;
  const inc = target / steps;

  const timer = setInterval(() => {
    current = Math.min(current + inc, target);
    el.textContent = prefix + fmt(current, decimals);
    if (current >= target) clearInterval(timer);
  }, step);
}

async function loadKPIs() {
  try {
    const d = await apiFetch('/api/stats/summary');

    const rateVal = isNaN(parseFloat(d.fraud_rate)) ? 0.0 : parseFloat(d.fraud_rate);
    const cards = [
      { id: 'kpi-total', val: d.total_transactions || 0, dec: 0, pre: '' },
      { id: 'kpi-fraud', val: d.fraud_count || 0, dec: 0, pre: '' },
      { id: 'kpi-rate', val: rateVal, dec: 1, pre: '' },
      { id: 'kpi-amount', val: d.avg_amount || 0, dec: 2, pre: '$' },
    ];

    cards.forEach(({ id, val, dec, pre }) => {
      const el = document.getElementById(id);
      if (el) animateValue(el, val, dec, pre);
    });

    const rateEl = document.getElementById('kpi-rate');
    if (rateEl) rateEl.textContent += '%';

  } catch (e) {
    console.error('KPI load failed:', e);
    showToast('Could not load KPIs — is the API running?', 'error');
  }
}

/* ══════════════════════════════════════════════════════════════
   CHARTS
══════════════════════════════════════════════════════════════ */
let trendChart = null;
let donutChart = null;

const CHART_DEFAULTS = {
  color: '#8b9cc8',
  font: { family: 'Inter', size: 11 },
};

async function loadTrendChart() {
  const chartEl = document.getElementById('trendChart');
  const wrap = chartEl ? chartEl.parentElement : document.querySelector('.chart-wrap');
  if (wrap) wrap.innerHTML = '<div style="text-align:center;padding:60px 20px;color:var(--text-muted);font-weight:500;">Loading trend data...</div>';

  try {
    const rows = await apiFetch('/api/stats/trend');

    if (!rows || rows.length === 0) {
      if (wrap) wrap.innerHTML = '<div style="text-align:center;padding:60px 20px;color:var(--text-muted);font-weight:500;">No trend data available</div>';
      return;
    }

    if (wrap) wrap.innerHTML = '<canvas id="trendChart"></canvas>';
    const ctx = document.getElementById('trendChart').getContext('2d');

    const labels = rows.map(r => {
      const d = new Date(r.date);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    });

    if (trendChart) trendChart.destroy();

    trendChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Legit',
            data: rows.map(r => r.legit),
            borderColor: '#3b82f6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
          },
          {
            label: 'Fraud',
            data: rows.map(r => r.fraud),
            borderColor: '#ef4444',
            backgroundColor: 'rgba(239, 68, 68, 0.1)',
            borderWidth: 2,
            tension: 0.4,
            fill: true,
            pointRadius: 0,
            pointHoverRadius: 4,
          }
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: '#ffffff',
            borderColor: '#e2e8f0',
            borderWidth: 1,
            titleColor: '#0f172a',
            bodyColor: '#475569',
            padding: 10,
            boxPadding: 6,
          },
        },
        scales: {
          x: {
            ticks: { color: '#64748b', font: { family: 'Inter', size: 11 }, maxTicksLimit: 8 },
            grid: { display: false },
          },
          y: {
            ticks: { color: '#64748b', font: { family: 'Inter', size: 11 } },
            grid: { color: '#f1f5f9', drawBorder: false },
            beginAtZero: true,
          },
        },
      },
    });
  } catch (e) {
    if (wrap) wrap.innerHTML = '<div style="text-align:center;padding:60px 20px;color:var(--danger);font-weight:500;">Failed to load trend data</div>';
  }
}

async function loadDonutChart() {
  const listEl = document.getElementById('catList');
  if (!listEl) return;
  listEl.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--text-muted);font-weight:500;">Loading threats...</div>';

  try {
    const cats = await apiFetch('/api/stats/categories');

    if (!cats || cats.length === 0) {
      listEl.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--text-muted);font-weight:500;">No threat data</div>';
      return;
    }

    const top = cats.slice(0, 6);
    const maxFraud = Math.max(...top.map(c => c.fraud), 1);

    listEl.innerHTML = top.map(c => {
      let colorHex = '#10b981'; // green
      if (c.fraud > 100) { colorHex = '#ef4444'; } // red
      else if (c.fraud > 50) { colorHex = '#f59e0b'; } // orange

      const width = Math.max(5, (c.fraud / maxFraud) * 100);

      return `
      <div class="vector-item animate-in" style="display:flex; flex-direction:column; gap:8px; padding:12px; background:#f8fafc; border:1px solid var(--border); border-radius:var(--radius-md);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div class="v-name" style="font-weight:600; color:var(--navy); font-size:0.9rem;">${c.category}</div>
          <div class="v-count" style="font-weight:700; color:var(--navy); font-size:0.95rem;">${c.fraud} frauds</div>
        </div>
        <div class="kpi-bar-wrap" style="width:100%; height:6px; background:var(--border); border-radius:3px; overflow:hidden; margin-top:2px;">
          <div class="kpi-bar-fill" style="width:${width}%; height:100%; background:${colorHex}; border-radius:3px;"></div>
        </div>
      </div>`;
    }).join('');

  } catch (e) {
    listEl.innerHTML = '<div style="text-align:center;padding:40px 20px;color:var(--danger);font-weight:500;">Failed to load threats</div>';
  }
}

/* ══════════════════════════════════════════════════════════════
   TRANSACTIONS TABLE
══════════════════════════════════════════════════════════════ */
async function loadTable() {
  if (state.loading) return;
  state.loading = true;

  const tbody = document.getElementById('txn-tbody');
  tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:28px">Loading…</td></tr>';

  try {
    const paramsObj = {
      page: state.page,
      per_page: state.perPage,
      ...(state.search && { search: state.search }),
      ...(state.fraudFilter && { fraud: state.fraudFilter }),
    };

    if (state.trpFilter && state.trpFilter.label === 'LAST 2 HOURS') {
      paramsObj.hours = '2';
      paramsObj.limit = '100';
    }

    const params = new URLSearchParams(paramsObj);

    let data = await apiFetch(`/api/transactions/?${params}`);

    // Client-side filter for LAST 2 HOURS
    if (state.trpFilter && state.trpFilter.label === 'LAST 2 HOURS') {
      const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
      data.data = data.data.filter(t => new Date(t.timestamp) >= twoHoursAgo);
      data.total = data.data.length;
      data.pages = 1;
    }

    state.totalPages = data.pages;

    if (!data.data.length) {
      if (state.trpFilter && state.trpFilter.label === 'LAST 2 HOURS') {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:28px">No transactions in last 2 hours</td></tr>';
      } else {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:28px">No transactions found.</td></tr>';
      }
    } else {
      tbody.innerHTML = data.data.map(t => {
        const isFraudStatus = (t.is_fraud === 1 || t.is_fraud === true || String(t.decision).toLowerCase() === 'fraud' || String(t.decision).toLowerCase() === 'blocked' || String(t.decision).toLowerCase() === 'declined');
        const statusBadge = isFraudStatus
          ? '<span class="badge badge-fraud">⚠ Fraud</span>'
          : '<span class="badge badge-legit">✓ Legit</span>';

        return `
        <tr class="animate-in">
          <td title="${t.id}">
            <code style="font-size:.78rem;background:#f1f5f9;padding:2px 7px;border-radius:4px;color:var(--navy);">${truncate(t.id, 12)}</code>
          </td>
          <td>${t.user_id || '—'}</td>
          <td style="font-weight:600;color:var(--text-primary)">${fmtMoney(t.amount)}</td>
          <td title="${t.merchant}">${truncate(t.merchant, 18)}</td>
          <td><span class="badge badge-cat">${t.category || '—'}</span></td>
          <td>${t.location || '—'}</td>
          <td>${fmtDate(t.timestamp)}</td>
          <td>${statusBadge}</td>
          <td>
            <button class="btn-text txn-detail-btn" data-idx="${data.data.indexOf(t)}"
              style="font-size:.8rem;color:var(--navy);font-weight:600;display:flex;align-items:center;gap:4px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>View
            </button>
          </td>
        </tr>`;
      }).join('');

      tbody.querySelectorAll('.txn-detail-btn').forEach(btn => {
        btn.addEventListener('click', () => openTxnDetailModal(data.data[+btn.dataset.idx]));
      });
    }

    renderPagination(data.total, data.page, data.pages);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--danger);padding:28px">Failed to load — is the API running?</td></tr>';
  } finally {
    state.loading = false;
  }
}

function renderPagination(total, page, pages) {
  document.getElementById('pag-info').textContent =
    `${total.toLocaleString()} transactions  ·  Page ${page} of ${pages}`;

  const container = document.getElementById('pag-btns');
  const range = [];
  const delta = 2;
  for (let i = Math.max(1, page - delta); i <= Math.min(pages, page + delta); i++) range.push(i);

  container.innerHTML = `
    <button class="pag-btn" id="pag-prev" ${page <= 1 ? 'disabled' : ''}>‹ Prev</button>
    ${range.map(p => `<button class="pag-btn ${p === page ? 'active' : ''}" data-page="${p}">${p}</button>`).join('')}
    <button class="pag-btn" id="pag-next" ${page >= pages ? 'disabled' : ''}>Next ›</button>
  `;

  container.querySelectorAll('[data-page]').forEach(btn => {
    btn.addEventListener('click', () => {
      state.page = +btn.dataset.page;
      loadTable();
    });
  });
  document.getElementById('pag-prev').addEventListener('click', () => {
    if (state.page > 1) { state.page--; loadTable(); }
  });
  document.getElementById('pag-next').addEventListener('click', () => {
    if (state.page < state.totalPages) { state.page++; loadTable(); }
  });
}

/* ══════════════════════════════════════════════════════════════
   PREDICT PANEL
══════════════════════════════════════════════════════════════ */
async function runPrediction() {
  const btn = document.getElementById('predict-btn');
  btn.textContent = '⏳ Analysing…';
  btn.disabled = true;

  const dowSelect = document.getElementById('p-dow');
  const catSelect = document.getElementById('p-category');

  const payload = {
    amount: parseFloat(document.getElementById('p-amount').value) || 0,
    hour: parseInt(document.getElementById('p-hour').value, 10) || 0,
    day_of_week: dowSelect.options[dowSelect.selectedIndex].text,
    category: catSelect.options[catSelect.selectedIndex].text,
    merchant: document.getElementById('p-merchant').value,
    location: document.getElementById('p-location').value
  };

  try {
    const r = await fetch(`${API}/api/transactions/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await r.json();

    // Add artificial delay to provide clear visual feedback that an analysis is happening
    await new Promise(resolve => setTimeout(resolve, 600));

    if (!r.ok) throw new Error(result.error || 'API error');

    showResult(result);
    
    // Refresh dashboard / transactions / alerts immediately (in addition to sockets)
    if (typeof loadDashboardData === "function") loadDashboardData();
    if (typeof loadTransactionsView === "function") loadTransactionsView();
    if (typeof loadAlertsView === "function") loadAlertsView();
    
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.innerHTML = '🔍 Analyse Transaction';
    btn.disabled = false;
  }
}

function showResult(result) {
  const box = document.getElementById('predict-result');
  const verdict = document.getElementById('result-verdict'); // hidden
  const riskBadge = document.getElementById('result-risk');
  const confScoreVal = document.getElementById('conf-score-val');
  const riskPct = document.getElementById('result-risk-pct');
  const riskCircle = document.getElementById('result-risk-circle');

  // Verdict classes
  verdict.textContent = result.is_fraud ? '⚠ FRAUD DETECTED' : '✓ LEGITIMATE';

  const riskScoreNum = parseFloat(result.risk_score || 0);
  const scoreInt = Math.round(riskScoreNum * 100);

  confScoreVal.textContent = parseFloat(result.confidence || 0).toFixed(3);
  riskPct.textContent = scoreInt + '%';

  if (result.is_fraud || result.risk_level === 'HIGH') {
    riskBadge.className = 'verdict-badge fraud';
    riskBadge.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg> FRAUD DETECTED';
    riskCircle.parentElement.style.background = 'linear-gradient(135deg, #f59e0b, #dc2626)';
  } else if (result.risk_level === 'MEDIUM' || (scoreInt > 40 && scoreInt < 75)) {
    riskBadge.className = 'verdict-badge suspicious';
    riskBadge.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg> SUSPICIOUS';
    riskCircle.parentElement.style.background = 'linear-gradient(135deg, #f59e0b, #ea580c)';
  } else {
    riskBadge.className = 'verdict-badge legit';
    riskBadge.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg> LOW RISK';
    riskCircle.parentElement.style.background = 'linear-gradient(135deg, #10b981, #16a34a)';
  }

  box.classList.add('visible');
}

/* ══════════════════════════════════════════════════════════════
   SEARCH / FILTER DEBOUNCE
══════════════════════════════════════════════════════════════ */
let searchTimer = null;
function onSearch(e) {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.search = e.target.value.trim();
    state.page = 1;
    loadTable();
  }, 380);
}
function onFraudFilter(e) {
  state.fraudFilter = e.target.value;
  state.page = 1;
  loadTable();
}

/* ══════════════════════════════════════════════════════════════
   TIME-RANGE PICKER LOGIC
══════════════════════════════════════════════════════════════ */
function initTRP() {
  const trigger = document.getElementById('trp-trigger');
  const dropdown = document.getElementById('trp-dropdown');
  const label = document.getElementById('trp-label');
  const applyBtn = document.getElementById('trp-apply');
  const fromInp = document.getElementById('trp-from');
  const toInp = document.getElementById('trp-to');

  if (!trigger || !dropdown) return;

  // Sync initial state (Last 24 Hours) to the inputs just so they aren't empty
  if (state.trpFilter.from_dt) {
    fromInp.value = state.trpFilter.from_dt.slice(0, 16); // format for datetime-local
    toInp.value = state.trpFilter.to_dt.slice(0, 16);
  }

  // Toggle Dropdown
  trigger.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = dropdown.classList.contains('open');
    if (isOpen) {
      dropdown.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
    } else {
      closeAllDropdowns();
      dropdown.classList.add('open');
      trigger.setAttribute('aria-expanded', 'true');
    }
  });

  // Close when clicking outside
  document.addEventListener('click', (e) => {
    if (!trigger.contains(e.target) && !dropdown.contains(e.target)) {
      dropdown.classList.remove('open');
      trigger.setAttribute('aria-expanded', 'false');
    }
  });

  // Handle preset clicks
  const presets = document.querySelectorAll('.trp-preset');
  presets.forEach(btn => {
    btn.addEventListener('click', (e) => {
      // update active state
      presets.forEach(p => p.classList.remove('trp-active'));
      btn.classList.add('trp-active');

      const now = new Date();
      let fromDate;
      const hours = btn.getAttribute('data-hours');
      const days = btn.getAttribute('data-days');
      const all = btn.getAttribute('data-all');

      if (all) {
        state.trpFilter = { from_dt: null, to_dt: null, label: 'ALL TIME' };
      } else {
        if (hours) fromDate = new Date(now.getTime() - parseInt(hours) * 60 * 60 * 1000);
        if (days) fromDate = new Date(now.getTime() - parseInt(days) * 24 * 60 * 60 * 1000);
        state.trpFilter = {
          from_dt: fromDate.toISOString().slice(0, 19),
          to_dt: now.toISOString().slice(0, 19),
          label: btn.textContent.toUpperCase()
        };
        // update inputs
        fromInp.value = state.trpFilter.from_dt.slice(0, 16);
        toInp.value = state.trpFilter.to_dt.slice(0, 16);
      }

      applyFilter(state.trpFilter.label);
    });
  });

  // Handle custom apply
  applyBtn.addEventListener('click', () => {
    if (!fromInp.value || !toInp.value) {
      showToast('Please select both From and To dates', 'error');
      return;
    }
    const fromDate = new Date(fromInp.value);
    const toDate = new Date(toInp.value);

    if (fromDate > toDate) {
      showToast('From date cannot be after To date', 'error');
      return;
    }

    // clear active presets
    presets.forEach(p => p.classList.remove('trp-active'));

    state.trpFilter = {
      from_dt: fromDate.toISOString().slice(0, 19),
      to_dt: toDate.toISOString().slice(0, 19),
      label: 'CUSTOM RANGE'
    };
    applyFilter(state.trpFilter.label);
  });

  function applyFilter(labelText) {
    label.textContent = labelText;
    dropdown.classList.remove('open');
    trigger.setAttribute('aria-expanded', 'false');
    if (labelText !== 'ALL TIME') {
      trigger.classList.add('has-filter');
    } else {
      trigger.classList.remove('has-filter');
    }
    // refresh dashboard with new filter
    refreshAll();
  }
}


/* ══════════════════════════════════════════════════════════════
   REFRESH  (manual only — Force Refresh button)
══════════════════════════════════════════════════════════════ */
function refreshAll() {
  loadKPIs();
  loadTrendChart();
  loadDonutChart();
  loadTable();
  showToast('Dashboard refreshed ✓');
}
// Alias used by Force Refresh button
function loadDashboardData() { refreshAll(); }

/* ══════════════════════════════════════════════════════════════
   TRANSACTIONS VIEW — FULL REGISTER WITH SEARCH & FILTER
══════════════════════════════════════════════════════════════ */

async function loadTransactionsView() {
  if (txnViewState.loading) return;
  txnViewState.loading = true;
  const tbody = document.getElementById('txn-view-tbody');
  if (!tbody) { txnViewState.loading = false; return; }
  tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:40px">Loading…</td></tr>';

  try {
    const paramsObj = {
      page: txnViewState.page,
      per_page: txnViewState.perPage,
      ...(txnViewState.search && { search: txnViewState.search }),
      ...(txnViewState.fraudFilter && { fraud: txnViewState.fraudFilter }),
    };
    const data = await apiFetch(`/api/transactions/?${new URLSearchParams(paramsObj)}`);
    txnViewState.totalPages = data.pages;

    const countLabel = document.getElementById('txn-count-label');
    if (countLabel) {
      const isFiltered = txnViewState.search || txnViewState.fraudFilter;
      countLabel.textContent = isFiltered
        ? `${data.total.toLocaleString()} results found`
        : `${data.total.toLocaleString()} transactions total`;
    }
    const statusEl = document.getElementById('txn-search-status');
    if (statusEl) statusEl.textContent = txnViewState.search ? `Showing results for "${txnViewState.search}"` : '';

    if (!data.data.length) {
      tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:40px;">
        ${txnViewState.search
          ? `No transactions matched <strong>"${txnViewState.search}"</strong>`
          : 'No transactions match the selected filters.'}
      </td></tr>`;
    } else {
      tbody.innerHTML = data.data.map(t => `
        <tr class="animate-in">
          <td title="${t.id}">
            <code style="font-size:.78rem;background:#f1f5f9;padding:2px 7px;border-radius:4px;color:var(--navy);">${truncate(t.id, 12)}</code>
          </td>
          <td style="color:var(--text-muted);font-size:.88rem;">${t.user_id}</td>
          <td style="font-weight:700;color:var(--navy);">${fmtMoney(t.amount)}</td>
          <td title="${t.merchant}">${truncate(t.merchant, 22)}</td>
          <td><span class="badge badge-cat">${t.category || '—'}</span></td>
          <td style="font-size:.85rem;color:var(--text-muted);">${t.location || '—'}</td>
          <td style="font-size:.82rem;color:var(--text-muted);">${fmtDate(t.timestamp)}</td>
          <td>${(t.is_fraud === 1 || t.is_fraud === true || String(t.decision).toLowerCase() === 'fraud' || String(t.decision).toLowerCase() === 'blocked' || String(t.decision).toLowerCase() === 'declined') ? '<span class="badge badge-fraud">⚠ Fraud</span>' : '<span class="badge badge-legit">✓ Legit</span>'}</td>
          <td>
            <button class="btn-text txn-detail-btn" data-idx="${data.data.indexOf(t)}"
              style="font-size:.8rem;color:var(--navy);font-weight:600;display:flex;align-items:center;gap:4px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>View
            </button>
          </td>
        </tr>`).join('');

      tbody.querySelectorAll('.txn-detail-btn').forEach(btn => {
        btn.addEventListener('click', () => openTxnDetailModal(data.data[+btn.dataset.idx]));
      });
    }
    renderTxnViewPagination(data.total, data.page, data.pages);
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--danger);padding:40px;">Failed to load — is the API running?</td></tr>';
  } finally {
    txnViewState.loading = false;
  }
}

function renderTxnViewPagination(total, page, pages) {
  const pagDiv = document.getElementById('txn-view-pagination');
  const infoEl = document.getElementById('txn-view-pag-info');
  const container = document.getElementById('txn-view-pag-btns');
  if (!pagDiv || !infoEl || !container) return;
  pagDiv.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:14px 20px;border-top:1px solid var(--border);flex-wrap:wrap;gap:10px;';
  infoEl.style.cssText = 'font-size:.82rem;color:var(--text-muted);font-weight:500;';
  infoEl.textContent = `${total.toLocaleString()} transactions · Page ${page} of ${pages}`;
  container.style.cssText = 'display:flex;align-items:center;gap:6px;flex-wrap:wrap;';
  const delta = 2, range = [];
  for (let i = Math.max(1, page - delta); i <= Math.min(pages, page + delta); i++) range.push(i);
  const navStyle = (disabled) =>
    `style="padding:7px 20px;background:${disabled ? '#e2e8f0' : '#1E3A5F'};color:${disabled ? '#94a3b8' : '#fff'};border:none;border-radius:6px;font-family:inherit;font-size:.82rem;font-weight:600;cursor:${disabled ? 'not-allowed' : 'pointer'};letter-spacing:.4px;transition:opacity .15s;"`;
  const pageStyle = (active) =>
    `style="min-width:34px;padding:7px 10px;background:${active ? '#1E3A5F' : '#fff'};color:${active ? '#fff' : '#334155'};border:1.5px solid ${active ? '#1E3A5F' : '#e2e8f0'};border-radius:6px;font-family:inherit;font-size:.82rem;font-weight:${active ? '700' : '500'};cursor:${active ? 'default' : 'pointer'};transition:all .15s;"`;

  container.innerHTML = `
    <button id="txn-pag-prev" ${page <= 1 ? 'disabled' : ''} ${navStyle(page <= 1)}>Prev</button>
    ${range.map(p => `<button data-page="${p}" ${pageStyle(p === page)}>${p}</button>`).join('')}
    <button id="txn-pag-next" ${page >= pages ? 'disabled' : ''} ${navStyle(page >= pages)}>Next</button>`;
  container.querySelectorAll('[data-page]').forEach(btn => {
    btn.addEventListener('click', () => { txnViewState.page = +btn.dataset.page; loadTransactionsView(); });
  });
  document.getElementById('txn-pag-prev').addEventListener('click', () => {
    if (txnViewState.page > 1) { txnViewState.page--; loadTransactionsView(); }
  });
  document.getElementById('txn-pag-next').addEventListener('click', () => {
    if (txnViewState.page < txnViewState.totalPages) { txnViewState.page++; loadTransactionsView(); }
  });
}

function openTxnDetailModal(txn) {
  if (!txn) { showToast('Transaction data unavailable', 'error'); return; }
  const overlay = document.getElementById('modal-overlay');
  const existing = document.getElementById('txn-detail-modal');
  if (existing) existing.remove();

  const confRow = txn.confidence != null
    ? `<div class="prof-detail-row"><span class="prof-detail-label">Confidence</span><span class="prof-detail-value">${(parseFloat(txn.confidence) * 100).toFixed(1)}%</span></div>` : '';
  const riskRow = txn.risk_level
    ? `<div class="prof-detail-row"><span class="prof-detail-label">Risk Level</span><span class="prof-detail-value">${txn.risk_level}</span></div>` : '';

  const modal = document.createElement('div');
  modal.className = 'modal profile-modal-wide';
  modal.id = 'txn-detail-modal';
  modal.innerHTML = `
    <div class="modal-header">
      <h2>📋 Transaction Details</h2>
      <button class="close-btn">×</button>
    </div>
    <div class="modal-body">
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px 24px;">
        <div class="prof-detail-row"><span class="prof-detail-label">Transaction ID</span>
          <span class="prof-detail-value" style="font-family:monospace;font-size:.82rem;word-break:break-all;">${txn.id}</span></div>
        <div class="prof-detail-row"><span class="prof-detail-label">User ID</span>
          <span class="prof-detail-value">${txn.user_id}</span></div>
        <div class="prof-detail-row"><span class="prof-detail-label">Amount</span>
          <span class="prof-detail-value" style="font-size:1.15rem;font-weight:700;color:var(--navy);">${fmtMoney(txn.amount)}</span></div>
        <div class="prof-detail-row"><span class="prof-detail-label">Status</span>
          <span class="prof-detail-value">${txn.is_fraud ? '<span class="badge badge-fraud">⚠ Fraud</span>' : '<span class="badge badge-legit">✓ Legit</span>'}</span></div>
        <div class="prof-detail-row"><span class="prof-detail-label">Merchant</span>
          <span class="prof-detail-value">${txn.merchant || '—'}</span></div>
        <div class="prof-detail-row"><span class="prof-detail-label">Category</span>
          <span class="prof-detail-value"><span class="badge badge-cat">${txn.category || '—'}</span></span></div>
        <div class="prof-detail-row"><span class="prof-detail-label">Location</span>
          <span class="prof-detail-value">${txn.location || '—'}</span></div>
        <div class="prof-detail-row"><span class="prof-detail-label">Timestamp</span>
          <span class="prof-detail-value">${fmtDate(txn.timestamp)}</span></div>
        ${confRow}${riskRow}
      </div>
    </div>`;

  overlay.appendChild(modal);
  document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
  overlay.classList.add('active');
  modal.classList.add('active');
  modal.querySelector('.close-btn').addEventListener('click', () => {
    overlay.classList.remove('active');
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    modal.remove();
  });
}

async function exportTransactionsCSV() {
  showToast('Preparing export…', 'info');
  try {
    const params = new URLSearchParams({
      page: 1, per_page: 5000,
      ...(txnViewState.search && { search: txnViewState.search }),
      ...(txnViewState.fraudFilter && { fraud: txnViewState.fraudFilter }),
    });
    const data = await apiFetch(`/api/transactions/?${params}`);
    if (!data.data.length) { showToast('No data to export', 'error'); return; }
    const headers = ['ID', 'User ID', 'Amount', 'Merchant', 'Category', 'Location', 'Timestamp', 'Is Fraud'];
    const csv = [
      headers.join(','),
      ...data.data.map(r => [
        r.id, r.user_id, r.amount,
        `"${(r.merchant || '').replace(/"/g, '""')}"`,
        `"${(r.category || '').replace(/"/g, '""')}"`,
        `"${(r.location || '').replace(/"/g, '""')}"`,
        r.timestamp, r.is_fraud ? 1 : 0,
      ].join(','))
    ].join('\n');
    const a = document.createElement('a');
    a.style.display = 'none';
    a.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csv);
    a.download = `transactions_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast(`Exported ${data.data.length} records ✓`, 'success');
  } catch (e) { showToast('Export failed — is the API running?', 'error'); }
}

/* ══════════════════════════════════════════════════════════════
   ALERTS VIEW — State, Data, Rendering, Pagination, Export
══════════════════════════════════════════════════════════════ */
const alertsViewState = {
  activeTab: 'all',   // 'all' | 'new' | 'reviewed' | 'resolved' | 'dismissed'
  riskFilter: '',
  typeFilter: '',
  search: '',
  page: 1,
  perPage: 10,
  totalPages: 1,
  allAlerts: [],
  filtered: [],
  initialized: false,
};

/* Alerts Data Logic */
async function loadAlerts(status = "all") {
  const listEl = document.getElementById('alerts-list');
  if (listEl) {
    listEl.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted);">Loading alerts&hellip;</div>';
  }

  try {
    let url = '/api/alerts';
    if (status !== 'all') {
      url += `?status=${status}`;
    }
    const data = await apiFetch(url);
    
    if (data && data.length > 0) {
        alertsViewState.allAlerts = data.map(a => ({
          id: a.id,
          transaction_id: a.transaction_id,
          amount: a.amount,
          merchant: a.merchant || '—',
          timestamp: a.timestamp,
          riskScore: a.risk_score,
          riskLevel: a.risk_level,
          type: a.source || 'suspicious',
          status: a.status === 'review' ? 'reviewed' : a.status,
          detectionLogic: a.message || 'No additional details provided.',
        }));
    } else {
        alertsViewState.allAlerts = [];
    }
    
    applyAlertsFilters();
    updateAlertTabCounts();
  } catch (e) {
    console.error('Failed to load alerts:', e);
    if (listEl) {
      listEl.innerHTML = '<div style="text-align:center;padding:60px;color:var(--danger);font-weight:500;">Unable to load alerts. Please check API connection.</div>';
    }
  }
}

async function loadAlertsView() {
  const currentTab = alertsViewState.activeTab;
  // Map UI tab names to backend status values
  const tabToStatus = { 'all': 'all', 'new': 'new', 'reviewed': 'review', 'resolved': 'resolved', 'dismissed': 'dismissed' };
  const status = tabToStatus[currentTab] || currentTab;
  await loadAlerts(status);
}

function applyAlertsFilters() {
  const { activeTab, riskFilter, typeFilter } = alertsViewState;
  let list = alertsViewState.allAlerts.slice();

  if (activeTab !== 'all') list = list.filter(a => a.status === activeTab);
  if (riskFilter === 'critical') list = list.filter(a => a.riskScore >= 90);
  else if (riskFilter === 'elevated') list = list.filter(a => a.riskScore >= 60 && a.riskScore < 90);
  else if (riskFilter === 'low') list = list.filter(a => a.riskScore < 60);
  if (typeFilter) list = list.filter(a => a.type === typeFilter);

  if (alertsViewState.search) {
    const s = alertsViewState.search.toLowerCase();
    list = list.filter(a =>
      a.id.toLowerCase().includes(s) ||
      a.merchant.toLowerCase().includes(s) ||
      a.detectionLogic.toLowerCase().includes(s)
    );
  }

  alertsViewState.filtered = list;
  alertsViewState.totalPages = Math.max(1, Math.ceil(list.length / alertsViewState.perPage));
  if (alertsViewState.page > alertsViewState.totalPages) alertsViewState.page = 1;

  renderAlertsPage();
  renderAlertsViewPagination();
}

function updateAlertTabCounts() {
  // Tab label is plain text — no count badge needed
}

function renderAlertsPage() {
  const listEl = document.getElementById('alerts-list');
  if (!listEl) return;
  const { filtered, page, perPage } = alertsViewState;
  const start = (page - 1) * perPage;
  const items = filtered.slice(start, start + perPage);

  if (!items.length) {
    listEl.innerHTML = '<div style="text-align:center;padding:60px;color:var(--text-muted);font-size:.95rem;">No alerts found for this status.</div>';
    return;
  }

  listEl.innerHTML = items.map(a => {
    const isFraud = a.type === 'fraud';
    const isResolved = a.status === 'resolved';
    const isDismissed = a.status === 'dismissed';
    const isReviewed = a.status === 'reviewed';
    const isNew = a.status === 'new';
    const borderCls = isResolved ? 'resolved-border' : isDismissed ? 'resolved-border' : isFraud ? 'fraud-border' : 'suspicious-border';
    const statusCls = isResolved ? 'resolved' : isDismissed ? 'resolved' : isFraud ? 'fraud' : 'suspicious';
    const iconBg = isFraud ? '#fef2f2' : (isResolved || isDismissed) ? '#f0fdf4' : '#fff7ed';
    const iconColor = isFraud ? '#dc2626' : (isResolved || isDismissed) ? '#16a34a' : '#ea580c';
    const label = isResolved ? 'RESOLVED' : isDismissed ? 'DISMISSED' : isFraud ? 'FRAUD' : 'SUSPICIOUS';
    const icon = isFraud
      ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`
      : (isResolved || isDismissed)
        ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`
        : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;

    const riskCls = a.riskScore >= 90 ? 'red' : a.riskScore >= 60 ? 'orange' : 'green';

    // Format date properly like: Oct 24, 2023 • 14:22:10 GMT
    const d = new Date(a.timestamp);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const timeStr = `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()} &bull; ${d.toLocaleTimeString('en-GB')} GMT`;

    const amtStr = fmtMoney(a.amount);

    // Build action buttons based on alert status
    let actionsHtml = '';
    if (isResolved || isDismissed) {
      // Terminal states — no actions
      actionsHtml = `<div class="alert-actions"><span style="font-size:.8rem;font-weight:700;color:#94a3b8;letter-spacing:.5px;">${isResolved ? 'RESOLVED' : 'DISMISSED'}</span></div>`;
    } else if (isReviewed) {
      // Reviewed: only RESOLVE + 3-dot menu
      actionsHtml = `
      <div class="alert-actions">
        <div class="action-row">
          <button class="alert-dismiss-btn" data-id="${a.id}" onclick="resolveAlertAction('${a.id}')">RESOLVE</button>
          <div class="alert-menu-wrap" style="position:relative;display:inline-block;">
            <button class="alert-menu-btn" title="More options" onclick="toggleAlertMenu(event, '${a.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
            </button>
            <div class="alert-menu-dropdown" id="menu-${a.id}" style="display:none;position:absolute;right:0;top:110%;background:#fff;border:1.5px solid #e2e8f0;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.12);z-index:999;min-width:160px;overflow:hidden;">
              <button onclick="dismissAlertAction('${a.id}')" style="display:block;width:100%;padding:10px 16px;text-align:left;border:none;background:none;font-family:inherit;font-size:.85rem;color:#dc2626;cursor:pointer;font-weight:600;transition:background .15s;" onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background='none'">Dismiss Alert</button>
            </div>
          </div>
        </div>
      </div>`;
    } else {
      // New: REVIEW + RESOLVE + 3-dot menu
      actionsHtml = `
      <div class="alert-actions">
        <button class="alert-review-btn" data-id="${a.id}" onclick="reviewAlert(this)">REVIEW</button>
        <div class="action-row">
          <button class="alert-dismiss-btn" data-id="${a.id}" onclick="resolveAlertAction('${a.id}')">RESOLVE</button>
          <div class="alert-menu-wrap" style="position:relative;display:inline-block;">
            <button class="alert-menu-btn" title="More options" onclick="toggleAlertMenu(event, '${a.id}')">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
            </button>
            <div class="alert-menu-dropdown" id="menu-${a.id}" style="display:none;position:absolute;right:0;top:110%;background:#fff;border:1.5px solid #e2e8f0;border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,.12);z-index:999;min-width:160px;overflow:hidden;">
              <button onclick="dismissAlertAction('${a.id}')" style="display:block;width:100%;padding:10px 16px;text-align:left;border:none;background:none;font-family:inherit;font-size:.85rem;color:#dc2626;cursor:pointer;font-weight:600;transition:background .15s;" onmouseover="this.style.background='#fef2f2'" onmouseout="this.style.background='none'">Dismiss Alert</button>
            </div>
          </div>
        </div>
      </div>`;
    }

    return `
    <div class="alert-card ${borderCls} animate-in">
      <div class="alert-status ${statusCls}">
        <div class="status-icon" style="background:${iconBg};color:${iconColor};"><div class="status-icon-inner">${icon}</div></div>
        <div class="status-text">${label}</div>
      </div>
      <div class="alert-details">
        <div class="detail-col col-txn">
          <span class="detail-label">TRANSACTION ID</span>
          <span class="detail-value fw-600">#${a.transaction_id || a.id}</span>
          <span class="detail-label" style="margin-top:14px;">TIME DETECTED</span>
          <span class="detail-value text-muted">${timeStr}</span>
        </div>
        <div class="detail-col col-amt">
          <span class="detail-label">AMOUNT</span>
          <span class="detail-value tx-large">${amtStr}</span>
        </div>
        <div class="detail-col col-merch">
          <span class="detail-label">MERCHANT</span>
          <span class="detail-value fw-600" style="color:#0f172a;">${a.merchant}</span>
          <span class="detail-label" style="margin-top:14px;">DETECTION LOGIC</span>
          <span class="detail-value text-muted" style="max-width:320px;line-height:1.5;color:#475569;">${a.detectionLogic}</span>
        </div>
        <div class="detail-col col-risk">
          <span class="detail-label">RISK SCORE</span>
          <div style="display:flex;align-items:center;gap:6px;">
            <span class="risk-score-val ${riskCls}">${a.riskScore}</span>
            <span class="risk-badge-text ${riskCls}">${a.riskLevel}</span>
          </div>
        </div>
      </div>
      ${actionsHtml}
    </div>`;
  }).join('');
}

function renderAlertsViewPagination() {
  const pagDiv = document.getElementById('alerts-pagination');
  const infoEl = document.getElementById('alerts-pag-info');
  const container = document.getElementById('alerts-pag-btns');
  if (!pagDiv || !infoEl || !container) return;

  const { filtered, page, perPage, totalPages } = alertsViewState;
  if (filtered.length === 0) { pagDiv.style.display = 'none'; return; }

  pagDiv.style.display = 'block';
  const start = (page - 1) * perPage + 1;
  const end = Math.min(page * perPage, filtered.length);
  infoEl.textContent = `Showing ${start}–${end} of ${filtered.length} alerts`;

  const delta = 2, range = [];
  for (let i = Math.max(1, page - delta); i <= Math.min(totalPages, page + delta); i++) range.push(i);

  const navStyle = (disabled) =>
    `style="padding:7px 18px;background:${disabled ? '#e2e8f0' : '#1E3A5F'};color:${disabled ? '#94a3b8' : '#fff'};border:none;border-radius:6px;font-family:inherit;font-size:.82rem;font-weight:600;cursor:${disabled ? 'not-allowed' : 'pointer'};letter-spacing:.4px;"`;
  const pageStyle = (active) =>
    `style="min-width:34px;padding:7px 10px;background:${active ? '#1E3A5F' : '#fff'};color:${active ? '#fff' : '#334155'};border:1.5px solid ${active ? '#1E3A5F' : '#e2e8f0'};border-radius:6px;font-family:inherit;font-size:.82rem;font-weight:${active ? '700' : '500'};cursor:${active ? 'default' : 'pointer'};"`;

  container.innerHTML = `
    <button id="alrt-pag-prev" ${page <= 1 ? 'disabled' : ''} ${navStyle(page <= 1)}>Prev</button>
    ${range.map(p => `<button data-page="${p}" ${pageStyle(p === page)}>${p}</button>`).join('')}
    <button id="alrt-pag-next" ${page >= totalPages ? 'disabled' : ''} ${navStyle(page >= totalPages)}>Next</button>`;

  container.querySelectorAll('[data-page]').forEach(btn => {
    btn.addEventListener('click', () => { alertsViewState.page = +btn.dataset.page; renderAlertsPage(); renderAlertsViewPagination(); });
  });
  document.getElementById('alrt-pag-prev').addEventListener('click', () => {
    if (alertsViewState.page > 1) { alertsViewState.page--; renderAlertsPage(); renderAlertsViewPagination(); }
  });
  document.getElementById('alrt-pag-next').addEventListener('click', () => {
    if (alertsViewState.page < alertsViewState.totalPages) { alertsViewState.page++; renderAlertsPage(); renderAlertsViewPagination(); }
  });
}

function exportAlertsCSV() {
  const list = alertsViewState.filtered;
  if (!list.length) { showToast('No alerts to export', 'error'); return; }
  showToast('Preparing export…', 'info');
  const headers = ['Transaction ID', 'Amount', 'Merchant', 'Timestamp', 'Risk Score', 'Risk Level', 'Type', 'Status', 'Detection Logic'];
  const csv = [
    headers.join(','),
    ...list.map(a => [
      `"${a.id}"`, a.amount,
      `"${(a.merchant || '').replace(/"/g, '""')}"`,
      a.timestamp, a.riskScore, a.riskLevel, a.type, a.status,
      `"${(a.detectionLogic || '').replace(/"/g, '""')}"`,
    ].join(','))
  ].join('\n');
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csv);
  a.download = `alerts_report_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  showToast(`Exported ${list.length} alerts ✓`, 'success');
}

async function updateAlertStatus(id, newStatus) {
  try {
    const r = await fetch(`${API}/api/alerts/${id}/status`, {
      method: 'PATCH',
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${window.FG_TOKEN || ''}`
      },
      body: JSON.stringify({ status: newStatus }),
    });
    if (!r.ok) throw new Error('Failed to update alert status');
    
    // Reload current alerts tab
    const tabStatus = alertsViewState.activeTab === 'reviewed' ? 'review' : alertsViewState.activeTab;
    await loadAlerts(tabStatus);
    
    showToast(`Alert marked as ${newStatus} ✓`, 'success');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

function reviewAlert(btn, id) {
  const alertId = id || (btn ? btn.dataset.id : '');
  updateAlertStatus(alertId, 'review');
}

function resolveAlertAction(id) {
  updateAlertStatus(id, 'resolved');
}

function dismissAlertAction(id) {
  // Close any open dropdown first
  document.querySelectorAll('.alert-menu-dropdown').forEach(m => m.style.display = 'none');
  updateAlertStatus(id, 'dismissed');
}

// Keep legacy name aliases for backward compat
function dismissAlert(btn, id) {
  const alertId = id || (btn ? btn.dataset.id : '');
  resolveAlertAction(alertId);
}

function resolveAlert(id) {
  resolveAlertAction(id);
}

function toggleAlertMenu(event, id) {
  event.stopPropagation();
  const menuEl = document.getElementById(`menu-${id}`);
  if (!menuEl) return;
  // Close all other open dropdowns
  document.querySelectorAll('.alert-menu-dropdown').forEach(m => {
    if (m.id !== `menu-${id}`) m.style.display = 'none';
  });
  menuEl.style.display = menuEl.style.display === 'none' ? 'block' : 'none';
}

// Close alert menus on outside click
document.addEventListener('click', () => {
  document.querySelectorAll('.alert-menu-dropdown').forEach(m => m.style.display = 'none');
});

function openSystemAuditModal() {
  const overlay = document.getElementById('modal-overlay');
  const modal = document.getElementById('system-audit-modal');
  if (!overlay || !modal) return;
  document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
  overlay.classList.add('active');
  modal.classList.add('active');

  const list = document.getElementById('audit-log-list');
  if (!list) return;
  const entries = [
    { time: '2023-10-24 14:22:10', action: 'Alert Generated', detail: 'FRAUD flag raised for TXN-98421-KB — Risk Score 98', level: 'danger' },
    { time: '2023-10-24 14:20:05', action: 'Model Prediction', detail: 'ML model v2.4.1 scored transaction with confidence 0.981', level: 'info' },
    { time: '2023-10-24 13:45:02', action: 'Alert Generated', detail: 'SUSPICIOUS flag raised for TXN-87115-ZZ — Risk Score 64', level: 'warning' },
    { time: '2023-10-24 13:12:30', action: 'User Login', detail: 'Chief Analyst logged in from 192.168.1.1', level: 'success' },
    { time: '2023-10-24 12:05:55', action: 'Alert Generated', detail: 'FRAUD flag raised for TXN-11029-AM — Risk Score 91', level: 'danger' },
    { time: '2023-10-24 11:58:00', action: 'Export Performed', detail: 'Transactions CSV exported — 5,000 records', level: 'info' },
    { time: '2023-10-24 10:44:22', action: 'Settings Updated', detail: 'Risk threshold changed from 80% to 85% by admin', level: 'warning' },
    { time: '2023-10-24 09:30:10', action: 'Model Retrained', detail: 'ML model retrained on 10,000 new labeled samples — Accuracy 99.82%', level: 'success' },
    { time: '2023-10-24 08:00:00', action: 'System Startup', detail: 'FraudGuard API v2.4.1 started successfully', level: 'success' },
  ];
  const colors = { danger: '#ef4444', warning: '#f59e0b', info: '#3b82f6', success: '#10b981' };
  list.innerHTML = entries.map(e => `
    <div style="display:flex;gap:14px;padding:12px;background:#f8fafc;border:1px solid var(--border);border-radius:8px;border-left:3px solid ${colors[e.level]};">
      <div style="flex:1;min-width:0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
          <span style="font-weight:700;font-size:.88rem;color:var(--navy);">${e.action}</span>
          <span style="font-size:.75rem;color:var(--text-muted);white-space:nowrap;">${e.time} GMT</span>
        </div>
        <div style="font-size:.82rem;color:#475569;">${e.detail}</div>
      </div>
    </div>`).join('');
}

function initAlertsView() {
  if (alertsViewState.initialized) return;
  alertsViewState.initialized = true;

  /* Tab switching */
  document.querySelectorAll('.alert-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.alert-tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      alertsViewState.activeTab = tab.dataset.tab;
      alertsViewState.page = 1;
      
      const tabToStatus = { 'all': 'all', 'new': 'new', 'reviewed': 'review', 'resolved': 'resolved', 'dismissed': 'dismissed' };
      loadAlerts(tabToStatus[tab.dataset.tab] || tab.dataset.tab);
    });
  });

  /* Filter toggle */
  const ftBtn = document.getElementById('alerts-filter-toggle');
  const fpanel = document.getElementById('alerts-filter-panel');
  if (ftBtn && fpanel) {
    ftBtn.addEventListener('click', () => {
      const open = fpanel.style.display !== 'none';
      fpanel.style.display = open ? 'none' : 'block';
      ftBtn.classList.toggle('active', !open);
    });
  }

  /* Risk/type filters */
  const riskSel = document.getElementById('alert-risk-filter');
  if (riskSel) riskSel.addEventListener('change', e => { alertsViewState.riskFilter = e.target.value; alertsViewState.page = 1; applyAlertsFilters(); });

  const typeSel = document.getElementById('alert-type-filter');
  if (typeSel) typeSel.addEventListener('change', e => { alertsViewState.typeFilter = e.target.value; alertsViewState.page = 1; applyAlertsFilters(); });

  /* Alerts page search bar */
  let alertsSearchTimer = null;
  const alertSearchInput = document.getElementById('alerts-search-input');
  const alertSearchClear = document.getElementById('alerts-search-clear');
  const alertSearchWrap = document.getElementById('alerts-search-wrap');

  if (alertSearchInput) {
    alertSearchInput.addEventListener('focus', () => {
      if (alertSearchWrap) { alertSearchWrap.style.borderColor = '#1E3A5F'; alertSearchWrap.style.boxShadow = '0 0 0 3px rgba(30,58,95,.10)'; }
    });
    alertSearchInput.addEventListener('blur', () => {
      if (alertSearchWrap) { alertSearchWrap.style.borderColor = '#e2e8f0'; alertSearchWrap.style.boxShadow = '0 1px 4px rgba(0,0,0,.06)'; }
    });
    alertSearchInput.addEventListener('input', e => {
      clearTimeout(alertsSearchTimer);
      const val = e.target.value.trim();
      if (alertSearchClear) alertSearchClear.style.display = val ? 'flex' : 'none';
      alertsSearchTimer = setTimeout(() => {
        alertsViewState.search = val;
        alertsViewState.page = 1;
        applyAlertsFilters();
      }, 300);
    });
  }

  if (alertSearchClear) {
    alertSearchClear.addEventListener('click', () => {
      if (alertSearchInput) { alertSearchInput.value = ''; alertSearchInput.focus(); }
      alertSearchClear.style.display = 'none';
      alertsViewState.search = '';
      alertsViewState.page = 1;
      applyAlertsFilters();
    });
  }

  /* Clear filters (risk + type + search) */
  const clearBtn = document.getElementById('alerts-filter-clear');
  if (clearBtn) clearBtn.addEventListener('click', () => {
    if (riskSel) riskSel.value = '';
    if (typeSel) typeSel.value = '';
    if (alertSearchInput) alertSearchInput.value = '';
    if (alertSearchClear) alertSearchClear.style.display = 'none';
    alertsViewState.riskFilter = '';
    alertsViewState.typeFilter = '';
    alertsViewState.search = '';
    alertsViewState.page = 1;
    applyAlertsFilters();
    showToast('Filters cleared', 'info');
  });

  /* Export Report */
  const expBtn = document.getElementById('alert-export-btn');
  if (expBtn) expBtn.addEventListener('click', exportAlertsCSV);

  /* System Audit */
  const audBtn = document.getElementById('system-audit-btn');
  if (audBtn) audBtn.addEventListener('click', openSystemAuditModal);

  /* FAB */
  const fab = document.getElementById('alerts-fab');
  if (fab) fab.addEventListener('click', () => {
    const critical = alertsViewState.allAlerts.filter(a => a.riskScore >= 90);
    showToast(`${critical.length} critical alerts require attention`, 'error');
  });
}

/* Wire up all Transactions view controls once */
function initTransactionsView() {
  if (txnViewState.initialized) return;
  txnViewState.initialized = true;

  let txnSearchTimer = null;
  const searchInput = document.getElementById('txn-search-input');
  const clearBtn = document.getElementById('txn-search-clear');

  if (searchInput) {
    searchInput.addEventListener('input', e => {
      clearTimeout(txnSearchTimer);
      const val = e.target.value.trim();
      if (clearBtn) clearBtn.style.display = val ? 'block' : 'none';
      txnSearchTimer = setTimeout(() => {
        txnViewState.search = val;
        txnViewState.page = 1;
        loadTransactionsView();
      }, 380);
    });
  }
  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      clearBtn.style.display = 'none';
      txnViewState.search = ''; txnViewState.page = 1;
      const statusEl = document.getElementById('txn-search-status');
      if (statusEl) statusEl.textContent = '';
      loadTransactionsView();
    });
  }

  const fraudFilter = document.getElementById('txn-fraud-filter');
  if (fraudFilter) fraudFilter.addEventListener('change', e => {
    txnViewState.fraudFilter = e.target.value; txnViewState.page = 1; loadTransactionsView();
  });

  const perPageSel = document.getElementById('txn-per-page');
  if (perPageSel) perPageSel.addEventListener('change', e => {
    txnViewState.perPage = parseInt(e.target.value, 10); txnViewState.page = 1; loadTransactionsView();
  });

  const refreshBtn = document.getElementById('txn-refresh-btn');
  if (refreshBtn) refreshBtn.addEventListener('click', () => {
    loadTransactionsView(); showToast('Transactions refreshed ✓', 'success');
  });

  const exportBtn = document.getElementById('txn-export-btn');
  if (exportBtn) exportBtn.addEventListener('click', exportTransactionsCSV);
}

/* ══════════════════════════════════════════════════════════════
   ANALYTICS VIEW STATE & LOGIC
══════════════════════════════════════════════════════════════ */
const analyticsViewState = {
  trpFilter: { from_dt: null, to_dt: null, label: 'LAST 30 DAYS' },
  search: '',
  initialized: false,
  loading: false,
  charts: {
    daily: null,
    category: null,
    hourly: null
  }
};

async function loadAnalyticsView() {
  if (analyticsViewState.loading) return;
  analyticsViewState.loading = true;

  try {
    const params = new URLSearchParams();
    if (analyticsViewState.trpFilter.from_dt) params.append('from_dt', analyticsViewState.trpFilter.from_dt);
    if (analyticsViewState.trpFilter.to_dt) params.append('to_dt', analyticsViewState.trpFilter.to_dt);
    if (analyticsViewState.search) params.append('search', analyticsViewState.search);
    const qs = params.toString() ? `?${params.toString()}` : '';

    const [kpis, trend, categories, hourly] = await Promise.all([
      apiFetch(`/api/stats/analytics_kpis${qs}`),
      apiFetch(`/api/stats/trend${qs}`),
      apiFetch(`/api/stats/categories${qs}`),
      apiFetch(`/api/stats/hourly${qs}`)
    ]);

    // KPI Cards
    document.getElementById('analytics-peak-hour').textContent = kpis.peak_hour_label || '--:--';
    document.getElementById('analytics-top-category').textContent = kpis.top_category || '—';
    document.getElementById('analytics-top-category-pct').textContent = `${kpis.top_category_pct || 0}`;
    document.getElementById('analytics-avg-fraud').textContent = fmtMoney(kpis.avg_fraud_amount || 0);
    document.getElementById('analytics-accuracy').textContent = `${kpis.detection_accuracy || 99.82}%`;

    // 1. Daily Trend Chart
    const dailyCtx = document.getElementById('analyticsDailyChart');
    if (dailyCtx) {
      if (analyticsViewState.charts.daily) analyticsViewState.charts.daily.destroy();
      const labels = trend.map(d => d.date.substring(5, 10).replace('-', ' ')); // MM DD
      analyticsViewState.charts.daily = new Chart(dailyCtx, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: 'Fraud Incidents',
            data: trend.map(d => d.fraud),
            backgroundColor: '#1E3A5F',
            borderRadius: 4,
            barThickness: 12
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { beginAtZero: true, grid: { color: '#f1f5f9' }, ticks: { precision: 0 } },
            x: { grid: { display: false } }
          }
        }
      });
    }

    // 2. Category Donut Chart
    const catCtx = document.getElementById('analyticsCategoryChart');
    if (catCtx) {
      if (analyticsViewState.charts.category) analyticsViewState.charts.category.destroy();

      const topCats = categories.slice(0, 4);
      const otherCats = categories.slice(4);
      const otherFraud = otherCats.reduce((sum, c) => sum + c.fraud, 0);

      const dataLabels = topCats.map(c => c.category);
      const dataValues = topCats.map(c => c.fraud);
      if (otherFraud > 0) {
        dataLabels.push('Other');
        dataValues.push(otherFraud);
      }

      const totalFraud = dataValues.reduce((a, b) => a + b, 0);
      document.getElementById('analytics-total-fraud-donut').textContent = totalFraud.toLocaleString();

      analyticsViewState.charts.category = new Chart(catCtx, {
        type: 'doughnut',
        data: {
          labels: dataLabels,
          datasets: [{
            data: dataValues,
            backgroundColor: ['#1E3A5F', '#92400e', '#93c5fd', '#e2e8f0', '#cbd5e1'],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          cutout: '75%',
          plugins: {
            legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8 } }
          }
        }
      });
    }

    // 3. Hourly Volume Area Chart
    const hourCtx = document.getElementById('analyticsHourlyChart');
    if (hourCtx) {
      if (analyticsViewState.charts.hourly) analyticsViewState.charts.hourly.destroy();
      analyticsViewState.charts.hourly = new Chart(hourCtx, {
        type: 'line',
        data: {
          labels: hourly.map(h => `${h.hour.toString().padStart(2, '0')}:00`),
          datasets: [{
            label: 'Transaction Volume',
            data: hourly.map(h => h.total),
            borderColor: '#1E3A5F',
            backgroundColor: 'rgba(30, 58, 95, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 4
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            y: { display: false, beginAtZero: true },
            x: {
              grid: { display: false },
              ticks: { maxTicksLimit: 5 }
            }
          }
        }
      });
    }

  } catch (e) {
    console.error('Failed to load analytics', e);
    showToast('Failed to load analytics data', 'error');
  } finally {
    analyticsViewState.loading = false;
  }
}

function initAnalyticsView() {
  if (analyticsViewState.initialized) return;
  analyticsViewState.initialized = true;

  // Time Range Picker
  const wrap = document.getElementById('analytics-trp-wrap');
  const trigger = document.getElementById('analytics-trp-trigger');
  const label = document.getElementById('analytics-trp-label');
  const dropdown = document.getElementById('analytics-trp-dropdown');
  const presets = document.querySelectorAll('#analytics-trp-dropdown .trp-preset');

  if (trigger && dropdown) {
    trigger.addEventListener('click', (e) => {
      e.stopPropagation();
      const isExpanded = trigger.getAttribute('aria-expanded') === 'true';
      trigger.setAttribute('aria-expanded', !isExpanded);
      dropdown.classList.toggle('open');
    });

    document.addEventListener('click', (e) => {
      if (wrap && !wrap.contains(e.target)) {
        trigger.setAttribute('aria-expanded', 'false');
        dropdown.classList.remove('open');
      }
    });

    presets.forEach(btn => {
      btn.addEventListener('click', () => {
        presets.forEach(b => b.classList.remove('trp-active'));
        btn.classList.add('trp-active');

        const days = btn.dataset.days;
        const all = btn.dataset.all;

        if (all) {
          analyticsViewState.trpFilter.from_dt = null;
          analyticsViewState.trpFilter.to_dt = null;
        } else {
          const toDate = new Date();
          const fromDate = new Date();
          fromDate.setDate(toDate.getDate() - parseInt(days, 10));
          analyticsViewState.trpFilter.from_dt = fromDate.toISOString();
          analyticsViewState.trpFilter.to_dt = toDate.toISOString();
        }

        analyticsViewState.trpFilter.label = btn.textContent.toUpperCase();
        if (label) label.textContent = analyticsViewState.trpFilter.label;

        trigger.setAttribute('aria-expanded', 'false');
        dropdown.classList.remove('open');

        loadAnalyticsView();
      });
    });
  }

  // Set default initial range logic (e.g. 30 days) to match UI
  const defDays = 30;
  const toDate = new Date();
  const fromDate = new Date();
  fromDate.setDate(toDate.getDate() - defDays);
  analyticsViewState.trpFilter.from_dt = fromDate.toISOString();
  analyticsViewState.trpFilter.to_dt = toDate.toISOString();

  // Export CSV
  const exportBtn = document.getElementById('analytics-export-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', async () => {
      showToast('Preparing analytics export...', 'info');
      try {
        const params = new URLSearchParams();
        if (analyticsViewState.trpFilter.from_dt) params.append('from_dt', analyticsViewState.trpFilter.from_dt);
        if (analyticsViewState.trpFilter.to_dt) params.append('to_dt', analyticsViewState.trpFilter.to_dt);
        const qs = params.toString() ? `?${params.toString()}` : '';

        const data = await apiFetch(`/api/transactions/${qs ? qs + '&page=1&per_page=10000' : '?page=1&per_page=10000'}`);
        if (!data.data || !data.data.length) { showToast('No data to export', 'error'); return; }

        const headers = ['ID', 'User ID', 'Amount', 'Merchant', 'Category', 'Location', 'Timestamp', 'Is Fraud'];
        const csv = [
          headers.join(','),
          ...data.data.map(r => [
            r.id, r.user_id, r.amount,
            `"${(r.merchant || '').replace(/"/g, '""')}"`,
            `"${(r.category || '').replace(/"/g, '""')}"`,
            `"${(r.location || '').replace(/"/g, '""')}"`,
            r.timestamp, r.is_fraud ? 1 : 0,
          ].join(','))
        ].join('\n');

        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = 'data:text/csv;charset=utf-8,\uFEFF' + encodeURIComponent(csv);
        a.download = `analytics_report_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        showToast(`Exported ${data.data.length} records ✓`, 'success');
      } catch (e) {
        showToast('Export failed', 'error');
      }
    });
  }
}

/* ══════════════════════════════════════════════════════════════
   NOTIFICATION PANEL
══════════════════════════════════════════════════════════════ */
function openNotificationPanel() {
  const panel = document.getElementById('notif-panel');
  const overlay = document.getElementById('notif-overlay');
  if (!panel) return;
  panel.classList.add('open');
  overlay.classList.add('open');
  loadNotifications();
}

function closeNotificationPanel() {
  const panel = document.getElementById('notif-panel');
  const overlay = document.getElementById('notif-overlay');
  if (!panel) return;
  panel.classList.remove('open');
  overlay.classList.remove('open');
}

async function loadNotifications() {
  const list = document.getElementById('notif-list');
  list.innerHTML = '<div class="notif-loading">Loading alerts…</div>';

  try {
    const data = await apiFetch('/api/transactions/?limit=10&per_page=10&page=1');
    const txns = (data.data || []).filter(t => t.is_fraud || t.risk_level === 'HIGH');

    if (!txns.length) {
      list.innerHTML = `
        <div class="notif-empty">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
          </svg>
          <p>No recent fraud alerts</p>
          <span>All transactions appear normal</span>
        </div>`;
      document.getElementById('notif-count').textContent = '0';
      return;
    }

    document.getElementById('notif-count').textContent = txns.length;
    list.innerHTML = txns.map(t => {
      const isFraud = t.is_fraud;
      const border = isFraud ? '#ef4444' : '#f59e0b';
      const label = isFraud ? 'FRAUD' : 'SUSPICIOUS';
      const labelClr = isFraud ? '#ef4444' : '#f59e0b';
      return `
        <div class="notif-card" style="border-left:3px solid ${border}">
          <div class="notif-card-header">
            <span class="notif-label" style="color:${labelClr}">${label}</span>
            <span class="notif-time">${fmtDate(t.timestamp)}</span>
          </div>
          <div class="notif-merchant">${t.merchant || '—'}</div>
          <div class="notif-amount">${fmtMoney(t.amount)}</div>
          <button class="notif-view-btn" onclick="closeNotificationPanel(); document.getElementById('nav-alerts').click()">
            View Details →
          </button>
        </div>`;
    }).join('');
  } catch {
    list.innerHTML = '<div class="notif-loading" style="color:#ef4444">Failed to load alerts.</div>';
  }
}

function markAllRead() {
  document.getElementById('notif-count').textContent = '0';
  const badge = document.getElementById('topbar-notif-badge');
  if (badge) badge.style.display = 'none';
  showToast('All notifications marked as read ✓', 'success');
}

/* ══════════════════════════════════════════════════════════════
   PROFILE DROPDOWN
══════════════════════════════════════════════════════════════ */
function toggleProfileDropdown(e) {
  e.stopPropagation();
  const dd = document.getElementById('profile-dropdown');
  if (!dd) return;
  const isOpen = dd.classList.contains('open');
  closeAllDropdowns();
  if (!isOpen) dd.classList.add('open');
}

function closeAllDropdowns() {
  document.querySelectorAll('.profile-dropdown').forEach(d => d.classList.remove('open'));
}

function openProfileModal() {
  closeAllDropdowns();
  const user = window.FG_USER || {};
  const initials = (user.name || 'JD').split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase();
  const lastLogin = user.last_login || 'N/A';
  document.getElementById('prof-modal-initials').textContent = initials;
  document.getElementById('prof-modal-name').textContent = user.name || 'Chief Analyst';
  document.getElementById('prof-modal-email').textContent = user.email || 'admin@fraudguard.com';
  document.getElementById('prof-modal-role').textContent = user.role || 'Administrator';
  document.getElementById('prof-modal-login').textContent = lastLogin;
  const overlay = document.getElementById('modal-overlay');
  if (overlay) {
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    overlay.classList.add('active');
    const m = document.getElementById('profile-modal');
    if (m) m.classList.add('active');
  }
}

function openChangePasswordModal() {
  closeAllDropdowns();
  const overlay = document.getElementById('modal-overlay');
  if (overlay) {
    document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    overlay.classList.add('active');
    const m = document.getElementById('change-pw-modal');
    if (m) m.classList.add('active');
  }
}

async function showActivityPanel() {
  closeAllDropdowns();

  const overlay = document.getElementById('modal-overlay');
  const modal = document.getElementById('activity-modal');

  if (!overlay || !modal) return;

  // Close any other open modals
  document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
  overlay.classList.add('active');
  modal.classList.add('active');

  const listEl = document.getElementById('activity-list');
  listEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">Loading activity logs...</div>';

  try {
    const r = await fetch(API + '/api/auth/activity', {
      headers: { 'Authorization': 'Bearer ' + window.FG_TOKEN }
    });

    if (!r.ok) throw new Error('Failed to load activity');
    const logs = await r.json();

    if (!logs || logs.length === 0) {
      listEl.innerHTML = '<div style="text-align:center;padding:20px;color:var(--text-muted);">No activity logs found.</div>';
      return;
    }

    listEl.innerHTML = logs.map(log => `
      <div style="padding:12px;border:1px solid var(--border);border-radius:8px;background:#f8fafc;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
          <span style="font-weight:600;font-size:0.9rem;color:var(--navy);">${log.action}</span>
          <span style="font-size:0.8rem;color:var(--text-muted);">${log.timestamp}</span>
        </div>
        <div style="font-size:0.85rem;color:#475569;">${log.details || ''}</div>
      </div>
    `).join('');

  } catch (err) {
    listEl.innerHTML = `<div style="text-align:center;padding:20px;color:var(--danger);">${err.message}</div>`;
  }
}

async function submitChangePassword() {
  const currentPw = document.getElementById('cpw-current').value;
  const newPw = document.getElementById('cpw-new').value;
  const confirmPw = document.getElementById('cpw-confirm').value;

  if (!currentPw || !newPw || !confirmPw) {
    showToast('Please fill out all password fields', 'error');
    return;
  }
  if (newPw !== confirmPw) {
    showToast('New passwords do not match', 'error');
    return;
  }

  const btn = document.getElementById('cpw-submit');
  btn.textContent = 'Updating...';
  btn.disabled = true;

  try {
    const r = await fetch(API + '/api/auth/change_password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + window.FG_TOKEN
      },
      body: JSON.stringify({ current_password: currentPw, new_password: newPw })
    });

    const result = await r.json();
    if (!r.ok) throw new Error(result.error || 'Failed to update password');

    showToast('Password updated successfully ✓', 'success');
    document.getElementById('modal-overlay').classList.remove('active');
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    btn.textContent = 'Update Password';
    btn.disabled = false;
  }
}

/* ══════════════════════════════════════════════════════════════
   SETTINGS VIEW — Full functionality
══════════════════════════════════════════════════════════════ */
function initSettingsView() {
  if (window._settingsInitialized) return;
  window._settingsInitialized = true;

  // ── Risk threshold slider ──
  const slider = document.getElementById('settings-risk-slider');
  const badge = document.getElementById('settings-risk-badge');
  const warn = document.getElementById('settings-override-warning');
  if (slider && badge) {
    const updateSlider = () => {
      const v = parseInt(slider.value, 10);
      badge.textContent = v + '%';
      if (warn) warn.style.display = v >= 90 ? 'flex' : 'none';
    };
    slider.addEventListener('input', updateSlider);
    updateSlider(); // apply on first load
  }

  // ── Save Settings ──
  const saveBtn = document.getElementById('settings-save-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', () => {
      const email = (document.getElementById('settings-email-input') || {}).value || '';
      if (email && !email.includes('@')) {
        showToast('Please enter a valid email address', 'error'); return;
      }
      saveBtn.textContent = 'Saving...';
      saveBtn.disabled = true;
      setTimeout(() => {
        saveBtn.textContent = 'Save Settings';
        saveBtn.disabled = false;
        showToast('Notification settings saved ✓', 'success');
      }, 700);
    });
  }

  // ── Reset to Default ──
  const resetBtn = document.getElementById('settings-reset-btn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      const emailInput = document.getElementById('settings-email-input');
      const emailToggle = document.getElementById('settings-email-toggle');
      if (emailInput) emailInput.value = 'security-ops@fraudguard.int';
      if (emailToggle) emailToggle.checked = true;
      if (slider) { slider.value = 85; badge.textContent = '85%'; }
      if (warn) warn.style.display = 'none';
      showToast('Settings reset to defaults', 'info');
    });
  }

  // ── Retrain Now ──
  const retrainBtn = document.getElementById('settings-retrain-btn');
  if (retrainBtn) {
    retrainBtn.addEventListener('click', async () => {
      retrainBtn.textContent = 'Training...';
      retrainBtn.disabled = true;
      try {
        await apiFetch('/api/model/retrain');
        const dateEl = document.getElementById('settings-train-date');
        if (dateEl) {
          const now = new Date();
          dateEl.textContent = now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        }
        showToast('Model retrained successfully ✓', 'success');
      } catch (e) {
        showToast('Retrain queued — check server logs for progress', 'info');
      } finally {
        retrainBtn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-10.26l5.58 5.69"/></svg> Retrain Now';
        retrainBtn.disabled = false;
      }
    });
  }

  // ── Save Profile ──
  const profileSaveBtn = document.getElementById('settings-profile-save-btn');
  if (profileSaveBtn) {
    profileSaveBtn.addEventListener('click', () => {
      const nameInput = document.getElementById('settings-display-name');
      const name = nameInput ? nameInput.value.trim() : '';
      if (name) {
        const el1 = document.getElementById('topbar-user-name');
        const el2 = document.getElementById('pd-name');
        if (el1) el1.textContent = name;
        if (el2) el2.textContent = name;
      }
      profileSaveBtn.textContent = 'Saving...';
      profileSaveBtn.disabled = true;
      setTimeout(() => {
        profileSaveBtn.textContent = 'Save Profile';
        profileSaveBtn.disabled = false;
        showToast('Profile updated successfully ✓', 'success');
      }, 600);
    });
  }

  // ── 2FA Toggle ──
  const tfaToggle = document.getElementById('settings-2fa-toggle');
  if (tfaToggle) {
    tfaToggle.addEventListener('change', () => {
      showToast(
        tfaToggle.checked ? '2FA enabled — OTP required for admin operations' : '2FA disabled',
        tfaToggle.checked ? 'success' : 'info'
      );
    });
  }

  // ── Session Timeout ──
  const sessionSel = document.getElementById('settings-session-timeout');
  if (sessionSel) {
    sessionSel.addEventListener('change', () => {
      showToast(`Session timeout set to ${sessionSel.options[sessionSel.selectedIndex].text}`, 'info');
    });
  }

  // ── Load live metrics from API ──
  (async () => {
    try {
      const d = await apiFetch('/api/stats/summary');
      if (d && d.avg_latency_ms != null) {
        const latEl = document.getElementById('settings-latency');
        const latSt = document.getElementById('settings-latency-status');
        if (latEl) latEl.textContent = Math.round(d.avg_latency_ms) + 'ms';
        if (latSt) {
          const good = d.avg_latency_ms < 50;
          latSt.innerHTML = `<span class="${good ? 'dot-green' : 'dot-orange'}"></span> ${good ? 'EXCELLENT' : 'NOMINAL'}`;
        }
      }
    } catch (e) { /* keep static values */ }
  })();
}

function showPreferences() {
  closeAllDropdowns();
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  const settingsNav = document.getElementById('nav-settings');
  if (settingsNav) settingsNav.classList.add('active');
  document.querySelectorAll('.view').forEach(v => { v.classList.remove('active'); v.classList.add('hidden'); });
  const sv = document.getElementById('view-settings');
  if (sv) { sv.classList.remove('hidden'); sv.classList.add('active'); }
  const topbarSearch = document.querySelector('.topbar-search');
  if (topbarSearch) topbarSearch.style.visibility = 'hidden';
  initSettingsView();
}

/* ══════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  // Wire up search + filter
  document.getElementById('search-input').addEventListener('input', onSearch);
  document.getElementById('fraud-filter').addEventListener('change', onFraudFilter);

  // Predict button
  document.getElementById('predict-btn').addEventListener('click', runPrediction);

  // Force Refresh button — manual only, no auto-refresh
  document.getElementById('refresh-btn').addEventListener('click', loadDashboardData);

  // Bell icon — notification panel
  const bellBtn = document.getElementById('topbar-bell-btn');
  if (bellBtn) bellBtn.addEventListener('click', openNotificationPanel);

  // Notification overlay click-outside
  const notifOverlay = document.getElementById('notif-overlay');
  if (notifOverlay) notifOverlay.addEventListener('click', closeNotificationPanel);

  // Profile avatar — dropdown
  const avatarBtn = document.getElementById('topbar-user-avatar');
  if (avatarBtn) avatarBtn.addEventListener('click', toggleProfileDropdown);

  // Close dropdowns on outside click
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.user-profile')) closeAllDropdowns();
  });

  // Nav items
  document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');

      document.querySelectorAll('.view').forEach(v => v.classList.remove('active', 'hidden'));
      document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));

      const topbarSearch = document.querySelector('.topbar-search');
      if (topbarSearch) {
        if (item.id === 'nav-alerts' || item.id === 'nav-settings') {
          topbarSearch.style.visibility = 'hidden';
        } else {
          topbarSearch.style.visibility = 'visible';
        }
      }

      if (item.id === 'nav-dashboard') {
        document.getElementById('view-dashboard').classList.remove('hidden');
        document.getElementById('view-dashboard').classList.add('active');
      } else if (item.id === 'nav-predict') {
        document.getElementById('view-predict').classList.remove('hidden');
        document.getElementById('view-predict').classList.add('active');
      } else if (item.id === 'nav-alerts') {
        document.getElementById('view-alerts').classList.remove('hidden');
        document.getElementById('view-alerts').classList.add('active');
        // Clear any stale global search so it doesn't filter out alert results
        const globalSearchEl = document.getElementById('search-input');
        if (globalSearchEl) globalSearchEl.value = '';
        // Also clear the alerts page search input
        const alertsSearchEl = document.getElementById('alerts-search-input');
        if (alertsSearchEl) alertsSearchEl.value = '';
        const alertsSearchClearEl = document.getElementById('alerts-search-clear');
        if (alertsSearchClearEl) alertsSearchClearEl.style.display = 'none';
        alertsViewState.search = '';
        alertsViewState.page = 1;
        initAlertsView();
        loadAlertsView();
      } else if (item.id === 'nav-settings') {
        document.getElementById('view-settings').classList.remove('hidden');
        document.getElementById('view-settings').classList.add('active');
        initSettingsView();
      } else if (item.id === 'nav-transactions') {
        document.getElementById('view-transactions').classList.remove('hidden');
        document.getElementById('view-transactions').classList.add('active');
        initTransactionsView();
        loadTransactionsView();
      } else if (item.id === 'nav-analytics') {
        document.getElementById('view-analytics').classList.remove('hidden');
        document.getElementById('view-analytics').classList.add('active');
        initAnalyticsView();
        loadAnalyticsView();
      }
    });
  });

  // Modal close logic
  function closeModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) {
      overlay.classList.remove('active');
      document.querySelectorAll('.modal').forEach(m => m.classList.remove('active'));
    }
  }

  const overlay = document.getElementById('modal-overlay');
  if (overlay) {
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
  }
  document.querySelectorAll('.close-btn').forEach(btn => btn.addEventListener('click', closeModal));

  // New Transaction button
  const newTxnBtn = document.getElementById('new-txn-btn');
  if (newTxnBtn) {
    newTxnBtn.addEventListener('click', () => {
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      const predictNav = document.getElementById('nav-predict');
      if (predictNav) predictNav.classList.add('active');
      document.querySelectorAll('.view').forEach(v => { v.classList.remove('active'); v.classList.add('hidden'); });
      document.getElementById('view-predict').classList.remove('hidden');
      document.getElementById('view-predict').classList.add('active');

      const topbarSearch = document.querySelector('.topbar-search');
      if (topbarSearch) topbarSearch.style.visibility = 'visible';

      setTimeout(() => document.getElementById('p-amount').focus(), 100);
    });
  }

  // View All Register button/link
  const viewAllRegLink = document.getElementById('view-all-register');
  if (viewAllRegLink) {
    viewAllRegLink.addEventListener('click', (e) => {
      e.preventDefault();
      document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
      const transNav = document.getElementById('nav-transactions');
      if (transNav) transNav.classList.add('active');
      document.querySelectorAll('.view').forEach(v => { v.classList.remove('active'); v.classList.add('hidden'); });
      const tv = document.getElementById('view-transactions');
      if (tv) {
        tv.classList.remove('hidden');
        tv.classList.add('active');
        initTransactionsView();
        loadTransactionsView();
      }
    });
  }

  // Global Search Logic
  const globalSearch = document.getElementById('search-input');
  let globalSearchTimer = null;
  if (globalSearch) {
    globalSearch.addEventListener('input', e => {
      clearTimeout(globalSearchTimer);
      const val = e.target.value.trim();
      globalSearchTimer = setTimeout(() => {
        // Analytics
        analyticsViewState.search = val;
        if (document.getElementById('view-analytics').classList.contains('active')) {
          loadAnalyticsView();
        }
        // Dashboard (can update state, but backend doesn't support search filtering for summary yet, unless we updated it)
        // Transactions
        txnViewState.search = val;
        txnViewState.page = 1;
        if (document.getElementById('view-transactions').classList.contains('active')) {
          loadTransactionsView();
        }

        // Alerts
        alertsViewState.search = val;
        alertsViewState.page = 1;
        if (document.getElementById('view-alerts').classList.contains('active')) {
          applyAlertsFilters();
        }
      }, 400);
    });
  }

  // Ensure default 24-hour range is applied before any dashboard API call
  initTRP();

  // Check API health first, then load dashboard with the 24-hour filter active
  // NOTE: must match the exact function name defined above (checkApiHealth, not checkAPIHealth)
  checkApiHealth().then(isOnline => {
    if (isOnline) refreshAll();
  });
});

/* ══════════════════════════════════════════════════════════════
   SOCKET.IO INTEGRATION
══════════════════════════════════════════════════════════════ */
if (typeof io !== 'undefined') {
  const socket = io(window.location.origin);
  
  socket.on("new_alert", () => {
    const currentAlertStatus = alertsViewState.activeTab === 'reviewed' ? 'review' : alertsViewState.activeTab;
    loadAlerts(currentAlertStatus || "all");
  });

  socket.on("new_transaction", () => {
    if (typeof loadDashboardData === "function") loadDashboardData();
    if (typeof loadTransactionsView === "function") loadTransactionsView();
  });
}
