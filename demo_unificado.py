"""Un solo motor (cfg_core.engine.TopDownParser) para Java y para español."""
import sys

from cfg_core.engine import TopDownParser
from java_subset.engine_adapter import parse_all
from spanish.grammar_es import LEXICON, RULES, tokenize_es

sys.setrecursionlimit(10000)

print("=== Java (gramática BNF de ll1.py) ===")
for src in ["int x = 1 + 2 * 3;",
            "if (a) if (b) x = 1; else x = 2;",
            "int x = ;"]:
    trees, err = parse_all(src)
    print(f"{src!r}: {len(trees)} árbol(es)" + (f" — {err}" if err else ""))

print("\n=== Español (gramática de grammar_es.py) ===")
es = TopDownParser(RULES, LEXICON, "O")
for s in ["el gato duerme",
          "el hombre vio el gato con el telescopio",
          "el gatos duerme"]:
    n = len(list(es.parses(tokenize_es(s))))
    print(f"{s!r}: {n} árbol(es)")