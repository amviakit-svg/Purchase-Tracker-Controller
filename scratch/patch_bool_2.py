import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1 (Lines 8344-8347):
pattern1 = re.compile(r"if isinstance\(val, \(int, float\)\):\s+row_data\.append\(f\"\{val:,\.2f\}\"\)\s+else:\s+row_data\.append\(str\(val\)\)", re.DOTALL)
replacement1 = """if type(val).__name__ in ['bool', 'bool_'] or isinstance(val, bool):
                            row_data.append(str(val))
                        elif isinstance(val, (int, float)):
                            row_data.append(f"{val:,.2f}")
                        else:
                            row_data.append(str(val))"""
content = pattern1.sub(replacement1, content)

# Pattern 3 (Line 8806):
pattern3 = re.compile(r"if isinstance\(val, \(int, float\)\):\s+row\[col\] = f\"\{val:,\.2f\}\"", re.DOTALL)
replacement3 = """if type(val).__name__ in ['bool', 'bool_'] or isinstance(val, bool):
                        row[col] = str(val)
                    elif isinstance(val, (int, float)):
                        row[col] = f"{val:,.2f}\""""
content = pattern3.sub(replacement3, content)

# Also check line 8410 for 'cell' summary:
pattern4 = re.compile(r"if isinstance\(cell, \(int, float\)\):\s+data_row\.append\(f\"\{cell:,\.2f\}\"\)\s+else:\s+data_row\.append\(str\(cell\)\)", re.DOTALL)
replacement4 = """if type(cell).__name__ in ['bool', 'bool_'] or isinstance(cell, bool):
                                            data_row.append(str(cell))
                                        elif isinstance(cell, (int, float)):
                                            data_row.append(f"{cell:,.2f}")
                                        else:
                                            data_row.append(str(cell))"""
content = pattern4.sub(replacement4, content)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched main.py")
