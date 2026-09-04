import tree_sitter_python as tspython
from tree_sitter import Language, Parser
from typing import List
from src.domain.interfaces.parser_interface import IParser
from src.domain.models.repository import CodeSymbol

class PythonParser(IParser):
    def __init__(self):
        self.language = Language(tspython.language())
        self.parser = Parser(self.language)
        
    def parse_symbols(self, content: str, file_path: str) -> List[CodeSymbol]:
        tree = self.parser.parse(bytes(content, "utf8"))
        symbols = []
        
        def traverse(node):
            if node.type in ['class_definition', 'function_definition']:
                name_node = next((n for n in node.children if n.type == 'identifier'), None)
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    sym_type = "class" if node.type == 'class_definition' else "function"
                    symbols.append(CodeSymbol(
                        name=name,
                        symbol_type=sym_type,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1
                    ))
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return symbols

    def extract_imports(self, content: str) -> List[str]:
        tree = self.parser.parse(bytes(content, "utf8"))
        imports = []
        
        def traverse(node):
            if node.type in ['import_statement', 'import_from_statement']:
                dotted = next((n for n in node.children if n.type == 'dotted_name'), None)
                if dotted:
                    imports.append(content[dotted.start_byte:dotted.end_byte])
            for child in node.children:
                traverse(child)
                
        traverse(tree.root_node)
        return imports
