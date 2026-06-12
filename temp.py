import re
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    content = f.read()
print('Occurrences of page-upload:', content.count('page-upload'))
