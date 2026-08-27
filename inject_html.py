import re

electron_html = r"d:\AlphaHunter\electron-app\frontend\index.html"
dashboard_html = r"d:\AlphaHunter\frontend\dashboard\public\index.html"

with open(electron_html, "r", encoding="utf-8") as f:
    e_content = f.read()

with open(dashboard_html, "r", encoding="utf-8") as f:
    d_content = f.read()

# Extract ah_chart_wrapper from electron_html
# We can use regex to grab the div and its contents up until the next section
# The next section in electron_html is <!--  Backtest Analytics Panel  -->
match = re.search(r'(<div class="card advanced-only"[^>]*id="ah_chart_wrapper">.*?)<!--  Backtest Analytics Panel  -->', e_content, re.DOTALL)
if not match:
    # Try alternate match if the comment is different
    match = re.search(r'(<div class="card advanced-only"[^>]*id="ah_chart_wrapper">.*?)</section>', e_content, re.DOTALL)

if not match:
    print("Could not extract ah_chart_wrapper from electron HTML")
    exit(1)

chart_wrapper_html = match.group(1).strip()
# In case it captured too much, let's just make sure it's valid
# But actually, looking at the previous output, the chart wrapper div closes right before <!--  Backtest Analytics Panel  -->

# Now we need to replace the empty ah_chart_wrapper in dashboard_html with this full one
# The empty one looks like: <div class="card advanced-only" style="margin-bottom:16px; display:flex; flex-direction:column; height: 800px; padding: 0; overflow: hidden; background: #0B0E14; border: 1px solid #1E222D;" id="ah_chart_wrapper"></div>

# We will regex replace the empty div
new_d_content = re.sub(r'<div class="card advanced-only"[^>]*id="ah_chart_wrapper"></div>', chart_wrapper_html, d_content, flags=re.DOTALL)

with open(dashboard_html, "w", encoding="utf-8") as f:
    f.write(new_d_content)

print("Injected HTML successfully!")
