"""Intenta construir la tabla LL(1) para la gramática del español (usa ll1.py de Java).

Uso:  python -m spanish.conflictos_ll1
Cada celda M[no terminal, categoría] con más de una producción es un conflicto LL(1).
"""
from java_subset.ll1 import build_table
from spanish.grammar_es import RULES

table, conflicts, first, follow = build_table(RULES, "O")
print(f"Celdas de la tabla LL(1) con más de una producción: {len(conflicts)}")
print(f"No terminales afectados: {len({nt for nt, _ in conflicts})} de {len(RULES)}\n")
for (nt, t), prods in sorted(conflicts.items()):
    alts = "  |  ".join(f"{nt} → {' '.join(p)}" for p in prods)
    print(f"  M[{nt}, {t}]: {alts}")