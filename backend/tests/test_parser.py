from src.infrastructure.parsing.python_parser import PythonParser

def test_python_parser_extracts_classes_and_functions():
    code = '''
import os
from sys import path

class MyService:
    def __init__(self):
        pass

def helper_function():
    return True
'''
    parser = PythonParser()
    symbols = parser.parse_symbols(code, "test.py")
    imports = parser.extract_imports(code)
    
    assert len(imports) == 2
    assert "os" in imports
    assert "sys" in imports
    
    names = [s.name for s in symbols]
    assert "MyService" in names
    assert "helper_function" in names
