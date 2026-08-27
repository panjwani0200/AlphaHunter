import re
import os

electron_app_js = r"d:\AlphaHunter\electron-app\frontend\app.js"
dashboard_app_js = r"d:\AlphaHunter\frontend\dashboard\public\app.js"

with open(electron_app_js, "r", encoding="utf-8") as f:
    electron_content = f.read()

# Extract AlphaChartManager block
chart_manager_match = re.search(r'(window\.AlphaChartManager = \(function\(\) \{.*?\n\}\)\(\);)', electron_content, re.DOTALL)
if not chart_manager_match:
    print("Could not find AlphaChartManager in electron app.js")
    exit(1)

chart_manager_code = chart_manager_match.group(1)

with open(dashboard_app_js, "r", encoding="utf-8") as f:
    dashboard_content = f.read()

# Inject AlphaChartManager right before API endpoints if not present
if "window.AlphaChartManager =" not in dashboard_content:
    dashboard_content = dashboard_content.replace("// ── API endpoints", chart_manager_code + "\n\n// ── API endpoints")
    with open(dashboard_app_js, "w", encoding="utf-8") as f:
        f.write(dashboard_content)
    print("Injected AlphaChartManager!")
else:
    print("AlphaChartManager already exists in dashboard app.js")
