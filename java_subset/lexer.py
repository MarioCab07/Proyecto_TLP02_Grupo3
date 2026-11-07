"""Analizador léxico (lexer) del subconjunto de Java.

El lexer reconoce tokens con expresiones regulares, es decir, vive en el
nivel 3 de la jerarquía de Chomsky (lenguajes regulares). El parser, en
cambio, necesita el nivel 2 (libres de contexto).
"""
import re
from dataclasses import dataclass

KEYWORDS = {"int", "boolean", "String", "if", "else", "while", "true", "false"}

# El orden importa: COMMENT antes de OP (para que '//' no sea dos '/'),
# PRINTLN antes de ID (para que 'System' no se lea como identificador).
TOKEN_SPEC = [
    ("SKIP", r"[ \t\r]+"),
    ("NEWLINE", r"\n"),
    ("COMMENT", r"//[^\n]*|/\*.*?\*/"),
    ("BADCOMMENT", r"/\*.*"),
    ("PRINTLN", r"System\.out\.println\b"),
    ("NUM", r"\d+"),
    ("STRING", r'"(?:[^"\\\n]|\\.)*"'),
    ("BADSTRING", r'"[^"\n]*'),
    ("ID", r"[A-Za-z_]\w*"),
    ("OP", r"\|\||&&|==|!=|[<>+\-*/!=(){};]"),
    ("MISMATCH", r"."),
]
MASTER = re.compile(
    "|".join(f"(?P<{n}>{p})" for n, p in TOKEN_SPEC), re.DOTALL
)


@dataclass(frozen=True)
class Token:
    type: str    # 'ID', 'NUM', 'STRING', 'EOF' o el lexema literal ('if', '+', ...)
    value: str
    line: int
    col: int

    def __str__(self):
        return f"{self.type}({self.value!r})@{self.line}:{self.col}"


@dataclass(frozen=True)
class LexError:
    message: str
    line: int
    col: int

    def __str__(self):
        return f"Línea {self.line}, col {self.col}: {self.message}"


def tokenize(source: str):
    """Devuelve (tokens, errores_léxicos). Siempre termina con un token EOF."""
    tokens, errors = [], []
    line, line_start = 1, 0
    for m in MASTER.finditer(source):
        kind, text = m.lastgroup, m.group()
        col = m.start() - line_start + 1
        if kind in ("SKIP", "COMMENT"):
            pass
        elif kind == "NEWLINE":
            pass
        elif kind == "ID":
            tokens.append(Token(text if text in KEYWORDS else "ID", text, line, col))
        elif kind == "PRINTLN":
            tokens.append(Token("System.out.println", text, line, col))
        elif kind in ("NUM", "STRING"):
            tokens.append(Token(kind, text, line, col))
        elif kind == "OP":
            tokens.append(Token(text, text, line, col))
        elif kind == "BADSTRING":
            errors.append(LexError("cadena sin cerrar", line, col))
        elif kind == "BADCOMMENT":
            errors.append(LexError("comentario /* sin cerrar", line, col))
        else:
            errors.append(LexError(f"carácter ilegal {text!r}", line, col))
        # actualizar posición de línea (los comentarios pueden tener saltos)
        nl = text.count("\n")
        if nl:
            line += nl
            line_start = m.start() + text.rfind("\n") + 1
    tokens.append(Token("EOF", "", line, len(source) - line_start + 1))
    return tokens, errors
