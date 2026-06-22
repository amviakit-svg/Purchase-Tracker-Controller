import re

def patch_js(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    out_lines = []
    for line in lines:
        stripped = line.strip()
        if 'apiCall(' in stripped and 'await ' not in stripped and '.then' not in stripped and '.catch' not in stripped and 'return ' not in stripped and 'function apiCall' not in stripped and not stripped.startswith('//') and 'window.apiCall' not in stripped:
            # We have a floating apiCall.
            # Example: apiCall('/api/notifications/log', { ... });
            # Wait, if it spans multiple lines like:
            # apiCall('/api/...', {
            #    method: 'POST'
            # });
            # Then replacing just 'apiCall(' might be tricky.
            # It's better to just skip multi-line patching automatically and do it manually if needed.
            if stripped.endswith(');'):
                line = line.replace(');', ').catch(e => console.warn("Background API error:", e));')
            elif stripped.endswith(')'):
                line = line.replace(')', ').catch(e => console.warn("Background API error:", e))')
                
        out_lines.append(line)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(out_lines)

patch_js('frontend/index.html')
patch_js('frontend/activities.js')
