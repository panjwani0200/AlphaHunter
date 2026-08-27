import glob
import re

for filepath in glob.glob('app/db/models/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove dangling imports
    content = content.replace("from sqlalchemy.dialects.postgresql import \n", "")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done")
