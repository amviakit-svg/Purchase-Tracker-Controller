t = open('frontend/index.html', encoding='utf-8').read()
lines = t.split('\n')

# Print openFormulaModal (line 8699) and what follows
for i in range(8699-1, 8780):
    print(f'{i+1}: {lines[i]}')