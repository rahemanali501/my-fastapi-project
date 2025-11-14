# fix_git.py
import os

content = """venv/
.env
__pycache__/
*.pyc
"""

# Force write .gitignore with correct encoding
with open(".gitignore", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ .gitignore file fixed successfully!")