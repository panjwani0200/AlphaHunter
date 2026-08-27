import glob
import re

for filepath in glob.glob('app/db/models/*.py'):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove redundant default kwargs
    content = content.replace("default=dict,\n        default=dict,", "default=dict,")
    content = content.replace("default=list,\n        default=list,", "default=list,")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

print("Done")
