import os

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, 'frontend', 'app.js'), 'r', encoding='utf-8') as f:
    app_js = f.read()

# Update updateAlertTabCounts
old_update = '''function updateAlertTabCounts() {
  const all      = alertsViewState.allAlerts;
  const setText  = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  setText('atab-all-count',      all.length);
  setText('atab-new-count',      all.filter(a => a.status === 'new').length);
  setText('atab-reviewed-count', all.filter(a => a.status === 'reviewed').length);
  setText('atab-resolved-count', all.filter(a => a.status === 'resolved').length);
}'''

new_update = '''function updateAlertTabCounts() {
  const all = alertsViewState.allAlerts;
  const el = document.getElementById('atab-all');
  if (el) el.innerHTML = 'ALL ALERTS (' + all.length + ')';
}'''

if old_update in app_js:
    app_js = app_js.replace(old_update, new_update)
else:
    print('Could not find updateAlertTabCounts')

# Update renderAlertsPage
old_render_start = '''  listEl.innerHTML = items.map(a => {
    const isFraud  = a.type === 'fraud';'''
old_render_end = '''    </div>`;
  }).join('');
}'''

new_render = '''  listEl.innerHTML = items.map(a => {
    const isFraud  = a.type === 'fraud';
    const isResolved = a.status === 'resolved';
    const borderCls = isResolved ? 'resolved-border' : isFraud ? 'fraud-border' : 'suspicious-border';
    const statusCls = isResolved ? 'resolved' : isFraud ? 'fraud' : 'suspicious';
    const iconBg    = isFraud ? '#fef2f2' : isResolved ? '#f0fdf4' : '#fff7ed';
    const iconColor = isFraud ? '#dc2626' : isResolved ? '#16a34a' : '#ea580c';
    const label     = isResolved ? 'RESOLVED' : isFraud ? 'FRAUD' : 'SUSPICIOUS';
    const icon      = isFraud
      ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`
      : isResolved
      ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`
      : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;

    const riskCls   = a.riskScore >= 90 ? 'red' : a.riskScore >= 60 ? 'orange' : 'green';
    
    // Format date properly like: Oct 24, 2023 • 14:22:10 GMT
    const d = new Date(a.timestamp);
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const timeStr = `${months[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()} &bull; ${d.toLocaleTimeString('en-GB')} GMT`;
    
    const amtStr    = fmtMoney(a.amount);

    return `
    <div class="alert-card ${borderCls} animate-in">
      <div class="alert-status ${statusCls}">
        <div class="status-icon" style="background:${iconBg};color:${iconColor};"><div class="status-icon-inner">${icon}</div></div>
        <div class="status-text">${label}</div>
      </div>
      <div class="alert-details">
        <div class="detail-col col-txn">
          <span class="detail-label">TRANSACTION ID</span>
          <span class="detail-value fw-600">#${a.id}</span>
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
      <div class="alert-actions">
        <button class="alert-review-btn" data-id="${a.id}" onclick="openAlertReviewModal(this)">REVIEW</button>
        <div class="action-row">
          <button class="alert-dismiss-btn" data-id="${a.id}" onclick="dismissAlert(this)">DISMISS</button>
          <button class="alert-menu-btn" title="More options">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
          </button>
        </div>
      </div>
    </div>`;
  }).join('');
}'''

start_idx = app_js.find(old_render_start)
end_idx = app_js.find(old_render_end) + len(old_render_end)

if start_idx != -1 and end_idx != -1:
    app_js = app_js[:start_idx] + new_render + app_js[end_idx:]
else:
    print('Could not find renderAlertsPage block')

with open(os.path.join(BASE, 'frontend', 'app.js'), 'w', encoding='utf-8') as f:
    f.write(app_js)

# Read style.css and update it
with open(os.path.join(BASE, 'frontend', 'style.css'), 'r', encoding='utf-8') as f:
    css = f.read()

new_css = '''/* ── Alert Tabs Bar ── */
.alerts-tabs-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0;
  overflow: hidden;
  flex-shrink: 0;
  background: transparent;
}
.alerts-tabs {
  display: flex;
  align-items: stretch;
}
.alert-tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 16px 24px;
  font-size: 0.85rem;
  font-weight: 500;
  letter-spacing: 0.02em;
  color: var(--text-secondary);
  cursor: pointer;
  border: none;
  background: none;
  border-bottom: 2px solid transparent;
  transition: all 0.18s ease;
  white-space: nowrap;
}
.alert-tab:hover { color: var(--navy); }
.alert-tab.active {
  color: var(--navy);
  border-bottom-color: var(--navy);
  font-weight: 600;
}
.alert-dot-red {
  display: inline-block;
  width: 6px; height: 6px;
  background: var(--danger);
  border-radius: 50%;
  flex-shrink: 0;
  margin-left: 2px;
}
.alerts-tabs-right {
  display: flex;
  align-items: center;
  padding: 0 16px;
}
.alerts-filter-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.85rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.18s;
}
.alerts-filter-toggle:hover { color: var(--navy); }
.alerts-filter-toggle.active { color: var(--navy); }

/* ── Filter Panel ── */
.alerts-filter-panel { flex-shrink: 0; margin-top: -10px; margin-bottom: 20px; }

/* ── Alerts List ── */
.alerts-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Alert Card ── */
.alert-card {
  display: flex;
  flex-direction: row;
  align-items: stretch;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  transition: box-shadow 0.18s, transform 0.15s;
}
.alert-card:hover {
  box-shadow: 0 6px 16px rgba(0,0,0,0.06);
}
.alert-card.fraud-border { border: 1px solid var(--border); }
.alert-card.suspicious-border { border: 1px solid #fbd38d; border-left: 4px solid var(--warning); box-shadow: 0 4px 6px rgba(234, 88, 12, 0.05); }
.alert-card.resolved-border { border-left: none; opacity: 0.8; }

/* Left: status icon + label */
.alert-status {
  width: 110px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px 16px;
}
.status-icon {
  width: 44px; height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.status-text {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.alert-status.fraud .status-text { color: var(--danger); }
.alert-status.suspicious .status-text { color: var(--warning); }
.alert-status.resolved .status-text { color: var(--success); }

/* Middle: detail columns */
.alert-details {
  flex: 1;
  display: flex;
  align-items: flex-start;
  padding: 24px;
  gap: 32px;
  min-width: 0;
}
.detail-col {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  min-width: 0;
}
.detail-col.col-txn   { min-width: 140px; }
.detail-col.col-amt   { min-width: 110px; }
.detail-col.col-merch { flex: 1.5; min-width: 180px; }
.detail-col.col-risk  { min-width: 110px; }

.detail-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: #94a3b8;
  letter-spacing: 0.05em;
  margin-bottom: 6px;
  white-space: nowrap;
  text-transform: uppercase;
}
.detail-value {
  font-size: 0.95rem;
  color: var(--navy);
  line-height: 1.3;
}
.detail-value.fw-600 { font-weight: 600; color: #0f172a; }
.detail-value.text-muted { color: #475569; font-size: 0.85rem; }
.tx-large {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}
.risk-score-val {
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1;
}
.risk-score-val.red { color: var(--danger); }
.risk-score-val.orange { color: var(--warning); }
.risk-score-val.green { color: var(--success); }
.risk-badge-text {
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.risk-badge-text.red { color: var(--danger); }
.risk-badge-text.orange { color: var(--warning); }
.risk-badge-text.green { color: var(--success); }

/* Right: action buttons */
.alert-actions {
  width: 150px;
  flex-shrink: 0;
  padding: 24px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 12px;
}
.action-row {
  display: flex;
  gap: 8px;
}
.alert-review-btn {
  width: 100%;
  padding: 10px;
  background: var(--navy);
  color: white;
  border: none;
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  cursor: pointer;
  transition: background 0.18s;
  border-radius: 4px;
}
.alert-review-btn:hover { background: #0a1628; }
.alert-dismiss-btn {
  flex: 1;
  padding: 8px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  font-family: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s;
  text-transform: uppercase;
  border-radius: 4px;
}
.alert-dismiss-btn:hover { border-color: var(--danger); color: var(--danger); }
.alert-menu-btn {
  padding: 8px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.18s;
  border-radius: 4px;
}
.alert-menu-btn:hover { border-color: var(--navy); color: var(--navy); }

/* Pagination */
.pagination-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
}
.pag-controls {
  display: flex;
  gap: 8px;
}
.pag-btn {
  min-width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
  font-weight: 500;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.15s;
}
.pag-btn:hover { border-color: var(--navy); color: var(--navy); }
.pag-btn.active {
  background: var(--navy);
  color: white;
  border-color: var(--navy);
  cursor: default;
}
.pag-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.fab.red-fab-square {
  position: fixed;
  bottom: 40px; right: 40px;
  width: 56px; height: 56px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  background: var(--danger);
  box-shadow: 0 10px 20px -5px rgba(220, 38, 38, 0.4);
  cursor: pointer;
  transition: transform var(--transition);
  z-index: 50;
}
.fab.red-fab-square:hover { transform: translateY(-3px) scale(1.02); }'''

start_css = css.find('/* ── Alert Tabs Bar ── */')
end_css = css.find('.fab:hover { transform: scale(1.05); }') + len('.fab:hover { transform: scale(1.05); }\n.red-fab { background: var(--danger); }\n.navy-fab { background: var(--navy); }\n')

if start_css != -1 and end_css != -1:
    css = css[:start_css] + new_css + '\n' + css[end_css:]
else:
    print('Could not find CSS block')

with open(os.path.join(BASE, 'frontend', 'style.css'), 'w', encoding='utf-8') as f:
    f.write(css)
