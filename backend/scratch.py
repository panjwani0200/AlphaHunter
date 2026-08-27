import glob
import re

for filepath in glob.glob('app/db/models/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Replace JSONB import with standard JSON if not already imported
    content = re.sub(r'from sqlalchemy\.dialects\.postgresql import (.*?)JSONB(.*?)', 
                     r'from sqlalchemy.dialects.postgresql import \1\2\nfrom sqlalchemy import JSON', 
                     content)
    
    # 2. If UUID was part of it, fix dangling comma
    content = content.replace('import , UUID', 'import UUID')
    
    # 3. Replace Mapped column usage of JSONB with JSON
    content = content.replace('JSONB,', 'JSON,').replace('JSONB', 'JSON')
    
    # 4. Replace server_default postgres syntax with python defaults
    content = content.replace('server_default=text("\'{}\'::jsonb")', 'default=dict')
    content = content.replace('server_default=text("\'[]\'::jsonb")', 'default=list')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done")
