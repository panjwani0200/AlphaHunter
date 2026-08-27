import re

path = 'd:/AlphaHunter/frontend/dashboard/public/app.js'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.startswith('// ── AlphaHunter Native Charting Engine'):
        skip = True
    
    # We want to stop skipping after line 390: })();
    if skip and line.strip() == '})();' and i < 400:
        skip = False
        continue
    
    if not skip:
        new_lines.append(line)

content = "".join(new_lines)

# Remove the fallback to V2 logic
content = re.sub(
    r'\} else if \(window\.AlphaChartManager && sorted\.length > 0\) \{.*?window\.AlphaChartManager\.renderChart[^}]*\}',
    r'}',
    content,
    flags=re.DOTALL
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Done app.js")
