import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Reverse Pattern 1 & 4 (which are the same replacement block)
replacement1 = r"if type\(val\)\.__name__ in \['bool', 'bool_'\] or isinstance\(val, bool\):\s+row_data\.append\(str\(val\)\)\s+elif isinstance\(val, \(int, float\)\):\s+row_data\.append\(f\"\{val:,\.2f\}\"\)\s+else:\s+row_data\.append\(str\(val\)\)"
original1 = """if isinstance(val, (int, float)):
                            row_data.append(f"{val:,.2f}")
                        else:
                            row_data.append(str(val))"""
content = re.sub(replacement1, original1, content)

replacement4 = r"if type\(cell\)\.__name__ in \['bool', 'bool_'\] or isinstance\(cell, bool\):\s+data_row\.append\(str\(cell\)\)\s+elif isinstance\(cell, \(int, float\)\):\s+data_row\.append\(f\"\{cell:,\.2f\}\"\)\s+else:\s+data_row\.append\(str\(cell\)\)"
original4 = """if isinstance(cell, (int, float)):
                                            data_row.append(f"{cell:,.2f}")
                                        else:
                                            data_row.append(str(cell))"""
content = re.sub(replacement4, original4, content)

# Reverse Pattern 3
replacement3 = r"if type\(val\)\.__name__ in \['bool', 'bool_'\] or isinstance\(val, bool\):\s+row\[col\] = str\(val\)\s+elif isinstance\(val, \(int, float\)\):\s+row\[col\] = f\"\{val:,\.2f\}\"\s+else:\s+row\[col\] = str\(val\)"
original3 = """if isinstance(val, (int, float)):
                        row[col] = f"{val:,.2f}"
                    else:
                        row[col] = str(val)"""
content = re.sub(replacement3, original3, content)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Unpatched main.py")
