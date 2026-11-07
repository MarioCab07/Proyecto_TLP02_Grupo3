"""Adaptador: corre la gramática BNF de Java (ll1.py) en el MISMO motor que el español."""
from cfg_core.engine import TopDownParser

from .lexer import tokenize
from .ll1 import load_grammar


def java_engine():
    rules, start = load_grammar()          # gramática BNF sin recursión izquierda
    return TopDownParser(rules, lexicon={}, start=start)


def parse_all(source: str):
    """Devuelve (árboles, error). Sin lexicon: los terminales son los tipos de token."""
    tokens, lex_errors = tokenize(source)
    types = [t.type for t in tokens if t.type != "EOF"]
    engine = java_engine()
    trees = list(engine.parses(types)) if not lex_errors else []
    if trees:
        return trees, None
    if lex_errors:
        return [], str(lex_errors[0])
    i = min(engine.fail_pos, len(tokens) - 1)
    tok = tokens[i]
    esperado = ", ".join(sorted(engine.fail_expected)[:6])
    return [], f"Línea {tok.line}, col {tok.col}: se esperaba {esperado}"