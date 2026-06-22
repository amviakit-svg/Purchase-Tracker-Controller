import ast
import sys

def check_leaks(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            has_connect = False
            has_close = False
            has_finally = False
            for child in ast.walk(node):
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                    if child.func.attr == 'connect' or child.func.attr == 'get_db_connection':
                        has_connect = True
                    if child.func.attr == 'close':
                        has_close = True
                if isinstance(child, ast.Call) and isinstance(child.func, ast.Name):
                    if child.func.id == 'get_db_connection':
                        has_connect = True
                if isinstance(child, ast.Try):
                    if len(child.finalbody) > 0:
                        for fin_node in ast.walk(child.finalbody[0]):
                            if isinstance(fin_node, ast.Call) and isinstance(fin_node.func, ast.Attribute) and fin_node.func.attr == 'close':
                                has_finally = True
                                
            if has_connect and not has_finally:
                print(f"Potential connection leak in {filepath} function: {node.name}")

check_leaks('backend/main.py')
check_leaks('backend/database.py')
