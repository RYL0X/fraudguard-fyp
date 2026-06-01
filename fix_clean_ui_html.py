import os

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, 'frontend', 'index.html'), 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the tabs and FAB
new_tabs = '''<!-- Alerts Tabs Bar -->
      <div class="alerts-tabs-bar" style="border-bottom: 1px solid var(--border); margin-bottom: 20px;">
        <div class="alerts-tabs" id="alerts-tabs">
          <button class="alert-tab active" data-tab="all" id="atab-all">ALL ALERTS (0)</button>
          <button class="alert-tab" data-tab="new" id="atab-new">NEW <span class="alert-dot-red"></span></button>
          <button class="alert-tab" data-tab="reviewed" id="atab-reviewed">REVIEWED</button>
          <button class="alert-tab" data-tab="resolved" id="atab-resolved">RESOLVED</button>
        </div>
        <div class="alerts-tabs-right">
          <button class="alerts-filter-toggle" id="alerts-filter-toggle">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/><line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/><line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/><line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/><line x1="17" y1="16" x2="23" y2="16"/></svg>
            Filters
          </button>
        </div>
      </div>'''

start_tabs = html.find('<!-- Alerts Tabs Bar -->')
end_tabs = html.find('<!-- Collapsible Filter Panel -->')
if start_tabs != -1 and end_tabs != -1:
    html = html[:start_tabs] + new_tabs + '\n\n      ' + html[end_tabs:]

new_fab = '''<!-- Floating Alert Button -->
      <button class="fab red-fab-square" id="alerts-fab" title="View critical alerts">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
      </button>'''

start_fab = html.find('<!-- Floating Alert Button -->')
end_fab = html.find('</div>\n  </div>\n\n  <!-- VIEW: SETTINGS')
if start_fab != -1 and end_fab != -1:
    html = html[:start_fab] + new_fab + '\n    ' + html[end_fab:]

with open(os.path.join(BASE, 'frontend', 'index.html'), 'w', encoding='utf-8') as f:
    f.write(html)
    print("HTML updated successfully.")
