import re, os

BASE = os.path.dirname(os.path.abspath(__file__))

# ─── patch index.html ────────────────────────────────────────────────────
html_path = os.path.join(BASE, 'frontend', 'index.html')
with open(html_path, encoding='utf-8') as f:
    html = f.read()

# 1. Replace entire view-alerts section (between the comment markers)
old_start = '  <!-- VIEW: ALERTS -->'
old_end   = '  </div>\n\n  <!-- VIEW: SETTINGS'

new_alerts_view = '''  <!-- VIEW: ALERTS -->
  <div id="view-alerts" class="view hidden">
    <div class="content">
      <div class="page-header">
        <div class="page-title">
          <h1>Fraud Alerts Center</h1>
          <p>Review and manage institutional security flags across the network.</p>
        </div>
        <div class="page-actions">
          <button class="btn btn-navy" id="alert-export-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
            EXPORT REPORT
          </button>
          <button class="btn btn-outline" id="system-audit-btn">SYSTEM AUDIT</button>
        </div>
      </div>

      <!-- Alerts Tabs Bar -->
      <div class="alerts-tabs-bar card">
        <div class="alerts-tabs" id="alerts-tabs">
          <button class="alert-tab active" data-tab="all">ALL ALERTS <span class="alert-tab-count" id="atab-all-count">0</span></button>
          <button class="alert-tab" data-tab="new">NEW <span class="alert-dot-red"></span><span class="alert-tab-count" id="atab-new-count">0</span></button>
          <button class="alert-tab" data-tab="reviewed">REVIEWED <span class="alert-tab-count" id="atab-reviewed-count">0</span></button>
          <button class="alert-tab" data-tab="resolved">RESOLVED <span class="alert-tab-count" id="atab-resolved-count">0</span></button>
        </div>
        <div class="alerts-tabs-right">
          <button class="alerts-filter-toggle" id="alerts-filter-toggle">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>
            Filters
          </button>
        </div>
      </div>

      <!-- Collapsible Filter Panel -->
      <div class="alerts-filter-panel" id="alerts-filter-panel" style="display:none;">
        <div class="card" style="padding:18px 24px;">
          <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:flex-end;">
            <div>
              <label style="font-size:.72rem;font-weight:700;color:#64748b;letter-spacing:.5px;display:block;margin-bottom:6px;">RISK LEVEL</label>
              <select id="alert-risk-filter" style="padding:8px 14px;border:1.5px solid #e2e8f0;border-radius:8px;font-family:inherit;font-size:.85rem;background:#fff;outline:none;color:var(--text-primary);">
                <option value="">All Risk Levels</option>
                <option value="critical">Critical (90+)</option>
                <option value="elevated">Elevated (60-89)</option>
                <option value="low">Low (&lt;60)</option>
              </select>
            </div>
            <div>
              <label style="font-size:.72rem;font-weight:700;color:#64748b;letter-spacing:.5px;display:block;margin-bottom:6px;">ALERT TYPE</label>
              <select id="alert-type-filter" style="padding:8px 14px;border:1.5px solid #e2e8f0;border-radius:8px;font-family:inherit;font-size:.85rem;background:#fff;outline:none;color:var(--text-primary);">
                <option value="">All Types</option>
                <option value="fraud">Fraud</option>
                <option value="suspicious">Suspicious</option>
              </select>
            </div>
            <button class="btn btn-outline" id="alerts-filter-clear" style="height:38px;padding:0 16px;font-size:.82rem;">Clear Filters</button>
          </div>
        </div>
      </div>

      <!-- Alerts List (dynamically rendered) -->
      <div class="alerts-list" id="alerts-list">
        <div style="text-align:center;padding:60px;color:var(--text-muted);">Loading alerts&hellip;</div>
      </div>

      <!-- Pagination Footer -->
      <div id="alerts-pagination" style="display:none;background:#fff;border:1px solid var(--border);border-radius:var(--radius-lg);box-shadow:var(--shadow-sm);">
        <div style="display:flex;align-items:center;justify-content:space-between;padding:14px 24px;flex-wrap:wrap;gap:10px;">
          <span id="alerts-pag-info" style="font-size:.82rem;color:var(--text-muted);font-weight:500;"></span>
          <div id="alerts-pag-btns" style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;"></div>
        </div>
      </div>

      <!-- Floating Alert Button -->
      <button class="fab red-fab" id="alerts-fab" title="View critical alerts">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
      </button>
    </div>
  </div>

  <!-- VIEW: SETTINGS'''

# Find and replace
idx_start = html.find(old_start)
idx_end   = html.find(old_end)
if idx_start == -1 or idx_end == -1:
    print(f"ERROR: markers not found  start={idx_start}  end={idx_end}")
else:
    html = html[:idx_start] + new_alerts_view + html[idx_end + len('  </div>\n\n  <!-- VIEW: SETTINGS'):]
    print("OK: alerts view replaced")

# 2. Add System Audit modal before closing </div> of modal-overlay
system_audit_modal = '''
  <!-- System Audit Modal -->
  <div class="modal profile-modal-wide" id="system-audit-modal">
    <div class="modal-header">
      <h2>&#x1F50D; System Audit Log</h2>
      <button class="close-btn">&times;</button>
    </div>
    <div class="modal-body">
      <div style="display:flex;flex-direction:column;gap:14px;">
        <p style="color:#475569;font-size:.9rem;">Real-time system events and security audit trail across all modules.</p>
        <div id="audit-log-list" style="display:flex;flex-direction:column;gap:10px;max-height:420px;overflow-y:auto;">
          <div style="text-align:center;padding:30px;color:var(--text-muted);">Loading audit logs&hellip;</div>
        </div>
      </div>
    </div>
  </div>

'''

if system_audit_modal.strip() not in html:
    html = html.replace('\n</div>\n\n<script>\nfunction openSupportModal', system_audit_modal + '\n</div>\n\n<script>\nfunction openSupportModal')
    print("OK: system audit modal added")

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("index.html saved")
