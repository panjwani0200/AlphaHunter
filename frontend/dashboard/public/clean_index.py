import re

path = 'd:/AlphaHunter/frontend/dashboard/public/index.html'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = re.sub(
    r'<div class="card advanced-only"[^>]*?id="ah_chart_wrapper">.*?<!-- ── Backtest Analytics Panel',
    r'<div class="card advanced-only" style="margin-bottom:16px; display:flex; flex-direction:column; height: 800px; padding: 0; overflow: hidden; background: #0B0E14; border: 1px solid #1E222D;" id="ah_chart_wrapper"></div>\n\n      <!-- ── Backtest Analytics Panel',
    content,
    flags=re.DOTALL
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done")
