import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1:
# if isinstance(val, (int, float)):
#     if val == int(val):
#         row_data.append(f"{val:,.2f}")
#     else:
#         row_data.append(f"{val:,.2f}")
# else:
#     row_data.append(str(val))
pattern1 = re.compile(r"if isinstance\(val, \(int, float\)\):\s+if val == int\(val\):\s+row_data\.append\(f\"\{val:,\.2f\}\"\)\s+else:\s+row_data\.append\(f\"\{val:,\.2f\}\"\)\s+else:\s+row_data\.append\(str\(val\)\)", re.DOTALL)

replacement1 = """if type(val).__name__ in ['bool', 'bool_'] or isinstance(val, bool):
                            row_data.append(str(val))
                        elif isinstance(val, (int, float)):
                            row_data.append(f"{val:,.2f}")
                        else:
                            row_data.append(str(val))"""

content = pattern1.sub(replacement1, content)

# Pattern 2:
# if isinstance(cell, (int, float)):
#     if cell == int(cell):
#         data_row.append(f"{cell:,.2f}")
#     else:
#         data_row.append(f"{cell:,.2f}")
# else:
#     data_row.append(str(cell))
pattern2 = re.compile(r"if isinstance\(cell, \(int, float\)\):\s+if cell == int\(cell\):\s+data_row\.append\(f\"\{cell:,\.2f\}\"\)\s+else:\s+data_row\.append\(f\"\{cell:,\.2f\}\"\)\s+else:\s+data_row\.append\(str\(cell\)\)", re.DOTALL)

replacement2 = """if type(cell).__name__ in ['bool', 'bool_'] or isinstance(cell, bool):
                                        data_row.append(str(cell))
                                    elif isinstance(cell, (int, float)):
                                        data_row.append(f"{cell:,.2f}")
                                    else:
                                        data_row.append(str(cell))"""

content = pattern2.sub(replacement2, content)


# Pattern 3:
# if isinstance(val, (int, float)):
#     row[col] = f"{val:,.2f}"
# else:
#     row[col] = str(val)
pattern3 = re.compile(r"if isinstance\(val, \(int, float\)\):\s+row\[col\] = f\"\{val:,\.2f\}\"\s+else:\s+row\[col\] = str\(val\)", re.DOTALL)
replacement3 = """if type(val).__name__ in ['bool', 'bool_'] or isinstance(val, bool):
                        row[col] = str(val)
                    elif isinstance(val, (int, float)):
                        row[col] = f"{val:,.2f}"
                    else:
                        row[col] = str(val)"""
content = pattern3.sub(replacement3, content)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched main.py")
