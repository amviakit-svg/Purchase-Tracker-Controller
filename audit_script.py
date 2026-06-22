import os
import re
import ast

def scan_python_files(directory):
    print(f"Scanning Python files in {directory}...")
    for root, _, files in os.walk(directory):
        if 'venv' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for SQL injection (conn.execute(f"..."))
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'conn.execute(f' in line or 'execute(f' in line:
                        print(f"[SQL INJECTION] {path}:{i+1} -> {line.strip()}")
                
def scan_js_files(directory):
    print(f"Scanning JS files in {directory}...")
    for root, _, files in os.walk(directory):
        if 'venv' in root or '.git' in root:
            continue
        for file in files:
            if file.endswith('.js') or file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    # Check for apiCall without await (excluding definitions or inside promise chains)
                    if 'apiCall(' in line and 'await' not in line and '.then' not in line and 'return apiCall' not in line and 'function apiCall' not in line:
                        if line.strip().startswith('//') or 'window.apiCall' in line:
                            continue
                        print(f"[UNHANDLED PROMISE] {path}:{i+1} -> {line.strip()}")

scan_python_files('backend')
scan_js_files('frontend')
