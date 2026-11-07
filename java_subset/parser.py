"""Parser descendente recursivo (LL(1)) del subconjunto de Java.

Gramática (EBNF; en ll1.py está la versión BNF pura con FIRST/FOLLOW):

    Program   → Stmt*
    Stmt      → Decl | Assign | If | While | Block | Print
    Decl      → Type ID ( '=' Expr )? ';'
    Assign    → ID '=' Expr ';'
    If        → 'if' '(' Expr ')' Stmt ( 'else' Stmt )?
    While     → 'while' '(' Expr ')' Stmt
    Block     → '{' Stmt* '}'
    Print     → 'System.out.println' '(' Expr ')' ';'
    Expr      → AndExpr ( '||' AndExpr )*
    AndExpr   → RelExpr ( '&&' RelExpr )*
    RelExpr   → AddExpr ( ('<'|'>'|'=='|'!=') AddExpr )?
    AddExpr   → Term ( ('+'|'-') Term )*
    Term      → Factor ( ('*'|'/') Factor )*
    Factor    → NUM | ID | STRING | 'true' | 'false'
              | '(' Expr ')' | '-' Factor | '!' Factor

Cada no terminal es un método; se decide qué producción usar mirando
solamente el token actual (1 token de lookahead): eso es LL(1).
"""
from dataclasses import dataclass
from typing import List

from cfg_core.tree import Node
from .lexer import Token, tokenize

from .lexer import Token, tokenize

TYPES = ("int", "boolean", "String")
REL_OPS = ("<", ">", "==", "!=")
STMT_START = set(TYPES) | {"ID", "if", "while", "{", "System.out.println"}

@dataclass
class ParseError(Exception):
    message: str
    token: Token

    def __str__(self):
        return f"Línea {self.token.line}, col {self.token.col}: {self.message}"


# ---------------------------------------------------------------- parser
class Parser:
    def __init__(self, source: str):
        self.tokens, self.lex_errors = tokenize(source)
        self.pos = 0
        self.errors: List[ParseError] = []

    # --- utilidades -----------------------------------------------------
    @property
    def cur(self) -> Token:
        return self.tokens[self.pos]

    def at(self, *types: str) -> bool:
        return self.cur.type in types

    def advance(self) -> Token:
        tok = self.cur
        if tok.type != "EOF":
            self.pos += 1
        return tok

    def leaf(self) -> Node:
        tok = self.advance()
        return Node(tok.type, token=tok)

    def expect(self, ttype: str) -> Node:
        if self.cur.type == ttype:
            return self.leaf()
        found = "fin de archivo" if self.cur.type == "EOF" else f"'{self.cur.value}'"
        raise ParseError(f"se esperaba '{ttype}' pero se encontró {found}", self.cur)

    def synchronize(self):
        """Modo pánico: descarta tokens hasta un punto seguro (';', '}' o inicio de sentencia)."""
        while not self.at("EOF"):
            if self.at(";"):
                self.advance()
                return
            if self.at("}") or self.cur.type in STMT_START:
                return
            self.advance()

    # --- sentencias -----------------------------------------------------
    def parse(self) -> Node:
        root = Node("Program")
        while not self.at("EOF"):
            self._stmt_with_recovery(root)
        return root

    def _stmt_with_recovery(self, parent: Node):
        start = self.pos
        try:
            parent.add(self.stmt())
        except ParseError as e:
            self.errors.append(e)
            self.synchronize()
            if self.pos == start:      # garantiza progreso (evita bucle infinito)
                self.advance()

    def stmt(self) -> Node:
        t = self.cur.type
        if t in TYPES:
            return self.decl()
        if t == "ID":
            return self.assign()
        if t == "if":
            return self.if_stmt()
        if t == "while":
            return self.while_stmt()
        if t == "{":
            return self.block()
        if t == "System.out.println":
            return self.print_stmt()
        found = "fin de archivo" if t == "EOF" else f"'{self.cur.value}'"
        raise ParseError(f"se esperaba una sentencia pero se encontró {found}", self.cur)

    def decl(self) -> Node:
        n = Node("Decl")
        n.add(Node("Type", [self.leaf()]))
        n.add(self.expect("ID"))
        if self.at("="):
            n.add(self.leaf())
            n.add(self.expr())
        n.add(self.expect(";"))
        return n

    def assign(self) -> Node:
        n = Node("Assign")
        n.add(self.expect("ID"))
        n.add(self.expect("="))
        n.add(self.expr())
        n.add(self.expect(";"))
        return n

    def if_stmt(self) -> Node:
        n = Node("If")
        n.add(self.expect("if"))
        n.add(self.expect("("))
        n.add(self.expr())
        n.add(self.expect(")"))
        n.add(self.stmt())
        # Dangling else: el 'else' se asocia al 'if' MÁS CERCANO porque este
        # método lo consume de inmediato (resuelve el conflicto de la tabla LL(1)).
        if self.at("else"):
            n.add(self.leaf())
            n.add(self.stmt())
        return n

    def while_stmt(self) -> Node:
        n = Node("While")
        n.add(self.expect("while"))
        n.add(self.expect("("))
        n.add(self.expr())
        n.add(self.expect(")"))
        n.add(self.stmt())
        return n

    def block(self) -> Node:
        n = Node("Block")
        n.add(self.expect("{"))
        while not self.at("}", "EOF"):
            self._stmt_with_recovery(n)
        n.add(self.expect("}"))
        return n

    def print_stmt(self) -> Node:
        n = Node("Print")
        n.add(self.expect("System.out.println"))
        n.add(self.expect("("))
        n.add(self.expr())
        n.add(self.expect(")"))
        n.add(self.expect(";"))
        return n

    # --- expresiones (precedencia: || < && < relacional < +- < */ < unario) ---
    def expr(self) -> Node:
        n = Node("Expr").add(self.and_expr())
        while self.at("||"):
            n.add(self.leaf()).add(self.and_expr())
        return n

    def and_expr(self) -> Node:
        n = Node("AndExpr").add(self.rel_expr())
        while self.at("&&"):
            n.add(self.leaf()).add(self.rel_expr())
        return n

    def rel_expr(self) -> Node:
        n = Node("RelExpr").add(self.add_expr())
        if self.at(*REL_OPS):          # no asociativo: a < b < c es inválido
            n.add(self.leaf()).add(self.add_expr())
        return n

    def add_expr(self) -> Node:
        n = Node("AddExpr").add(self.term())
        while self.at("+", "-"):
            n.add(self.leaf()).add(self.term())
        return n

    def term(self) -> Node:
        n = Node("Term").add(self.factor())
        while self.at("*", "/"):
            n.add(self.leaf()).add(self.factor())
        return n

    def factor(self) -> Node:
        n = Node("Factor")
        if self.at("NUM", "ID", "STRING", "true", "false"):
            return n.add(self.leaf())
        if self.at("("):
            n.add(self.leaf()).add(self.expr()).add(self.expect(")"))
            return n
        if self.at("-", "!"):
            n.add(self.leaf()).add(self.factor())
            return n
        found = "fin de archivo" if self.at("EOF") else f"'{self.cur.value}'"
        raise ParseError(f"se esperaba una expresión pero se encontró {found}", self.cur)


# ------------------------------------------------------------------ API
def parse(source: str):
    """Devuelve (árbol, lista_de_errores_como_texto). Sin errores ⇒ entrada válida."""
    p = Parser(source)
    tree = p.parse()
    errors = [str(e) for e in p.lex_errors] + [str(e) for e in p.errors]
    return tree, errors
