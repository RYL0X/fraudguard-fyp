import os

BASE = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(BASE, 'frontend', 'index.html')

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Find the settings view block boundaries
start_marker = '  <!-- VIEW: SETTINGS -->'
end_marker = '  <!-- VIEW: TRANSACTIONS -->'

start_idx = html.find(start_marker)
end_idx = html.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Could not find markers. start={start_idx}, end={end_idx}")
    exit(1)

new_settings = '''  <!-- VIEW: SETTINGS -->
  <div id="view-settings" class="view hidden">
    <div class="content">
      <div class="page-header">
        <div class="page-title">
          <h1>System Configuration</h1>
          <p>Manage infrastructure parameters and institutional security protocols.</p>
        </div>
      </div>

      <div class="settings-layout">
        <!-- LEFT COLUMN -->
        <div class="settings-col-left">
          <div class="card p-24">
            <div class="status-header">
              <h3>System Status</h3>
              <div class="status-badge green" id="settings-overall-status"><span class="dot-green"></span> All Systems Operational</div>
            </div>
            <div class="status-list">
              <div class="status-item">
                <div class="status-name">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg>
                  ML Model Active
                </div>
                <div class="status-val green" id="settings-ml-status">STABLE</div>
              </div>
              <div class="status-item">
                <div class="status-name">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path></svg>
                  Database Connected
                </div>
                <div class="status-val green" id="settings-db-status">CONNECTED</div>
              </div>
              <div class="status-item">
                <div class="status-name">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>
                  API Running
                </div>
                <div class="status-val green" id="settings-api-status">v2.4.1 LIVE</div>
              </div>
            </div>
            <div class="training-date mt-4">
              <span class="detail-label">LAST TRAINING DATE</span>
              <div class="date-row">
                <span class="date-val" id="settings-train-date">Oct 24, 2023</span>
                <button class="btn-text" id="settings-retrain-btn">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.92-10.26l5.58 5.69"/></svg>
                  Retrain Now
                </button>
              </div>
            </div>
          </div>

          <div class="infrastructure-card mt-4">
            <div class="infra-bg"></div>
            <div class="infra-content">
              <h3>Infrastructure Security</h3>
              <p>Global surveillance nodes are encrypted and monitoring real-time flow.</p>
            </div>
          </div>

          <div class="metrics-row mt-4">
            <div class="card p-24 flex-1">
              <span class="detail-label">UPTIME RATIO</span>
              <div class="metric-val" id="settings-uptime">99.998%</div>
              <div class="metric-bar mt-2"></div>
            </div>
            <div class="card p-24 flex-1">
              <span class="detail-label">API LATENCY</span>
              <div class="metric-val" id="settings-latency">12ms</div>
              <div class="metric-status mt-2" id="settings-latency-status"><span class="dot-green"></span> EXCELLENT</div>
            </div>
          </div>
        </div>

        <!-- RIGHT COLUMN -->
        <div class="settings-col-right" style="display:flex;flex-direction:column;gap:20px;">

          <!-- Notification Settings -->
          <div class="card p-24">
            <h3>Notification Settings</h3>

            <div class="setting-block mt-4">
              <div class="setting-info">
                <h4>Email alerts toggle</h4>
                <p>Send automated summaries and critical failure warnings.</p>
              </div>
              <label class="switch"><input type="checkbox" id="settings-email-toggle" checked><span class="slider"></span></label>
            </div>

            <div class="setting-block-vertical mt-4">
              <label>PRIMARY NOTIFICATION EMAIL</label>
              <input type="email" id="settings-email-input" value="security-ops@fraudguard.int" placeholder="Enter email address" />
            </div>

            <div class="setting-block-vertical mt-4">
              <div class="flex-between">
                <div>
                  <label class="text-dark">Risk threshold slider</label>
                  <p class="text-sm text-muted">Define the sensitivity for real-time fraud detection triggers.</p>
                </div>
                <div class="badge-dark" id="settings-risk-badge">85%</div>
              </div>
              <input type="range" class="range-slider mt-2" min="0" max="100" value="85" id="settings-risk-slider" />
              <div class="slider-labels">
                <span>Conservative</span>
                <span>Institutional Standard</span>
                <span>Aggressive</span>
              </div>
            </div>

            <div class="warning-box mt-4" id="settings-override-warning" style="display:none;">
              <div class="warning-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg></div>
              <div class="warning-text">
                <strong>Manual Override Enabled</strong>
                <p>Thresholds above 90% require secondary authentication from the Chief Security Officer.</p>
              </div>
            </div>

            <div class="settings-footer mt-auto pt-4">
              <button class="btn btn-outline" id="settings-reset-btn">Reset to Default</button>
              <button class="btn btn-navy" id="settings-save-btn">Save Settings</button>
            </div>
          </div>

          <!-- Security & Access -->
          <div class="card p-24">
            <h3>Security &amp; Access</h3>

            <div class="setting-block-vertical mt-4">
              <label>DISPLAY NAME</label>
              <input type="text" id="settings-display-name" value="Chief Analyst" placeholder="Your display name" />
            </div>

            <div class="setting-block-vertical mt-4">
              <label>ROLE / ACCESS LEVEL</label>
              <input type="text" value="Tier-3 Investigator" disabled style="opacity:0.55;cursor:not-allowed;background:#f8fafc;" />
            </div>

            <div class="setting-block mt-4">
              <div class="setting-info">
                <h4>Two-Factor Authentication</h4>
                <p>Require OTP verification for all admin-level operations.</p>
              </div>
              <label class="switch"><input type="checkbox" id="settings-2fa-toggle"><span class="slider"></span></label>
            </div>

            <div class="setting-block mt-4" style="border-top:1px solid var(--border);padding-top:16px;margin-top:4px;">
              <div class="setting-info">
                <h4>Session Timeout</h4>
                <p>Automatically log out after a period of inactivity.</p>
              </div>
              <select id="settings-session-timeout" style="padding:8px 12px;border:1.5px solid #e2e8f0;border-radius:8px;font-family:inherit;font-size:.85rem;color:var(--text-primary);background:#fff;outline:none;cursor:pointer;">
                <option value="15">15 minutes</option>
                <option value="30" selected>30 minutes</option>
                <option value="60">1 hour</option>
                <option value="240">4 hours</option>
              </select>
            </div>

            <div class="settings-footer pt-4" style="margin-top:16px;">
              <button class="btn btn-outline" id="settings-change-pw-btn" onclick="openChangePasswordModal()">Change Password</button>
              <button class="btn btn-navy" id="settings-profile-save-btn">Save Profile</button>
            </div>
          </div>

        </div>
      </div>
    </div>
  </div>

'''

html = html[:start_idx] + new_settings + html[end_idx:]

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Settings HTML updated successfully.")
