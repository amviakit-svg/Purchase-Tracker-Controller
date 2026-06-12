# -*- coding: utf-8 -*-
with open('frontend/index.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Insert </div> at line 342
lines.insert(341, '        </div>\n')

# The lines shifted by 1. So line 718 is now 719.
# We want to remove the extra </div>.
# Let's verify line 719 has </div>
assert '</div>' in lines[718]
del lines[718]

with open('frontend/index.html', 'w', encoding='utf-8') as f:
    f.writelines(lines)
print('Fixed DOM nesting successfully!')
