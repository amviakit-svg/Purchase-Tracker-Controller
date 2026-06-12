import re
from collections import Counter

with open('frontend/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

matches = re.findall(r'id="([^"]+)"', html)
counts = Counter(matches)

if counts['page-upload'] > 1:
    print('Duplicate page-upload IDs found:', counts['page-upload'])
else:
    print('No duplicate page-upload ID.')

if counts['tab-upload'] > 1:
    print('Duplicate tab-upload IDs found:', counts['tab-upload'])
else:
    print('No duplicate tab-upload ID.')
