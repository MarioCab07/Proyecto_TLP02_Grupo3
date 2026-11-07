"""Cálculo de FIRST, FOLLOW y tabla LL(1) para la gramática BNF pura.

Sirve para el informe: muestra la gramática sin recursión izquierda y
factorizada, y detecta automáticamente el conflicto del *dangling else*.

Uso:  python -m java_subset.ll1
"""
import sys
import textwrap
from collections import defaultdict

EPS = "ε"
END = "$"

GRAMMAR_TEXT = """
Program   → StmtList
StmtList  → Stmt StmtList | ε
Stmt      → Decl | Assign | If | While | Block | Print
Decl      → Type ID DeclInit ;
DeclInit  → = Expr | ε
Type      → int | boolean | String
Assign    → ID = Expr ;
If        → if ( Expr ) Stmt ElsePart
ElsePart  → else Stmt | ε
While     → while ( Expr ) Stmt
Block     → { StmtList }
Print     → System.out.println ( Expr ) ;
Expr      → AndExpr ExprP
ExprP     → || AndExpr ExprP | ε
AndExpr   → RelExpr AndExprP
AndExprP  → && RelExpr AndExprP | ε
RelExpr   → AddExpr RelOpt
RelOpt    → RelOp AddExpr | ε
RelOp     → < | > | == | !=
AddExpr   → Term AddExprP
AddExprP  → + Term AddExprP | - Term AddExprP | ε
Term      → Factor TermP
TermP     → * Factor TermP | / Factor TermP | ε
Factor    → NUM | ID | STRING | true | false | ( Expr ) | - Factor | ! Factor
"""


def load_grammar(text: str = GRAMMAR_TEXT):
    """Devuelve (reglas, símbolo_inicial). reglas: dict NT → lista de producciones (listas de símbolos)."""
    rules, start = {}, None
    for line in text.strip().splitlines():
        lhs, rhs = line.split("→")
        lhs = lhs.strip()
        start = start or lhs
        rules[lhs] = [alt.split() for alt in rhs.split(" | ")]
    return rules, start


def compute_first(rules):
    first = {nt: set() for nt in rules}

    def first_of_seq(seq):
        out = set()
        for sym in seq:
            f = first[sym] if sym in rules else {sym}
            out |= f - {EPS}
            if EPS not in f:
                return out
        out.add(EPS)
        return out

    changed = True
    while changed:
        changed = False
        for nt, prods in rules.items():
            for prod in prods:
                new = {EPS} if prod == [EPS] else first_of_seq(prod)
                if not new <= first[nt]:
                    first[nt] |= new
                    changed = True
    return first, first_of_seq


def compute_follow(rules, start, first):
    follow = {nt: set() for nt in rules}
    follow[start].add(END)
    changed = True
    while changed:
        changed = False
        for nt, prods in rules.items():
            for prod in prods:
                for i, sym in enumerate(prod):
                    if sym not in rules:
                        continue
                    trailer, nullable = set(), True
                    for nxt in prod[i + 1:]:
                        f = first[nxt] if nxt in rules else {nxt}
                        trailer |= f - {EPS}
                        if EPS not in f:
                            nullable = False
                            break
                    if nullable:
                        trailer |= follow[nt]
                    if not trailer <= follow[sym]:
                        follow[sym] |= trailer
                        changed = True
    return follow


def build_table(rules, start):
    """Devuelve (tabla, conflictos). tabla[(NT, terminal)] = lista de producciones."""
    first, first_of_seq = compute_first(rules)
    follow = compute_follow(rules, start, first)
    table = defaultdict(list)
    for nt, prods in rules.items():
        for prod in prods:
            f = first_of_seq(prod) if prod != [EPS] else {EPS}
            for t in f - {EPS}:
                table[(nt, t)].append(prod)
            if EPS in f:
                for t in follow[nt]:
                    table[(nt, t)].append(prod)
    conflicts = {k: v for k, v in table.items() if len(v) > 1}
    return table, conflicts, first, follow


# ----------------------------------------------------------------- presentación
SHORT = {"System.out.println": "println"}   # solo para encabezados de la matriz


def _q(t):
    """Entrecomilla los símbolos de puntuación para que '{' y '}' no se confundan con las llaves del conjunto."""
    if t in (EPS, END) or t.replace(".", "").isalnum():
        return t
    return f"'{t}'"


def _fmt(s):
    return "{" + ", ".join(_q(t) for t in sorted(s, key=lambda t: (t in (EPS, END), t))) + "}"


def _alias(sets_by_nt, kind):
    """Un conjunto largo que ya apareció se imprime como '= FIRST(otro NT)' para no repetirlo."""
    seen, out = {}, {}
    for nt, s in sets_by_nt.items():
        key = frozenset(s)
        if len(key) >= 5 and key in seen:
            out[nt] = f"= {kind}({seen[key]})"
        else:
            if len(key) >= 5:
                seen[key] = nt
            out[nt] = _fmt(s)
    return out


def _print_sets(title, texts):
    print(title)
    for nt, txt in texts.items():
        print(textwrap.fill(txt, width=100, initial_indent=f"  {nt:<10} ", subsequent_indent=" " * 13))
    print()


def number_productions(rules):
    nums, n = {}, 0
    for nt, prods in rules.items():
        for p in prods:
            n += 1
            nums[(nt, tuple(p))] = n
    return nums


def print_ll1_table(rules, table, conflicts, first, follow):
    """Tabla LL(1) en forma compacta: cada producción y los tokens para los que M[NT, token] la elige."""
    nums = number_productions(rules)
    select = defaultdict(set)
    for (nt, t), prods in table.items():
        for p in prods:
            select[(nt, tuple(p))].add(t)
    names = {}
    for nt in rules:
        if EPS not in first[nt]:       # los NT anulables (con ε) no sirven de nombre
            names.setdefault(frozenset(first[nt]), f"FIRST({nt})")
    for nt in rules:
        names.setdefault(frozenset(follow[nt]), f"FOLLOW({nt})")

    print("TABLA LL(1)  M[no terminal, token]: tokens que seleccionan cada producción")
    print(f"{'#':>3}  {'Producción':<38} Se elige si el siguiente token está en")
    for nt, prods in rules.items():
        for p in prods:
            key = (nt, tuple(p))
            sel = frozenset(select[key])
            if p == [EPS]:
                label = f"FOLLOW({nt})"
            elif len(sel) >= 5 and sel in names:
                label = names[sel]
            else:
                label = _fmt(sel)
            bad = sorted(t for (n2, t) in conflicts if n2 == nt and key in {(nt, tuple(q)) for q in conflicts[(n2, t)]})
            if bad:
                label += "   <-- CONFLICTO en " + ", ".join(_q(t) for t in bad)
            line = f"{nums[key]:>3}  {nt + ' → ' + ' '.join(p):<38} "
            print(textwrap.fill(label, width=110, initial_indent=line, subsequent_indent=" " * 43))
    print()


def print_matrix(rules, table, chunk=16):
    """Matriz completa M[NT, token] con el número de producción en cada celda ('.' = error)."""
    nums = number_productions(rules)
    terms = []
    for prods in rules.values():
        for p in prods:
            for sym in p:
                if sym not in rules and sym != EPS and sym not in terms:
                    terms.append(sym)
    terms.append(END)
    print("MATRIZ LL(1)  (número = producción de la lista anterior, '.' = error sintáctico, 'a/b' = conflicto)")
    for i in range(0, len(terms), chunk):
        cols = terms[i:i + chunk]
        widths = [max(len(SHORT.get(t, t)), 5) + 1 for t in cols]   # 5 = ancho de un conflicto 'a/b'
        print()
        print(f"{'':<10}" + "".join(f"{SHORT.get(t, t):>{w}}" for t, w in zip(cols, widths)))
        for nt, prods in rules.items():
            cells = []
            for t, w in zip(cols, widths):
                entries = table.get((nt, t), [])
                txt = "/".join(str(nums[(nt, tuple(p))]) for p in entries) if entries else "."
                cells.append(f"{txt:>{w}}")
            print(f"{nt:<10}" + "".join(cells))
    print()


def main():
    rules, start = load_grammar()
    table, conflicts, first, follow = build_table(rules, start)

    print("Gramática BNF (sin recursión izquierda, factorizada)")
    for nt, prods in rules.items():
        print(textwrap.fill(" | ".join(" ".join(p) for p in prods), width=100,
                            initial_indent=f"  {nt:<10} → ", subsequent_indent=" " * 15))
    print()
    _print_sets("CONJUNTOS FIRST", _alias({nt: first[nt] for nt in rules}, "FIRST"))
    _print_sets("CONJUNTOS FOLLOW", _alias({nt: follow[nt] for nt in rules}, "FOLLOW"))
    print_ll1_table(rules, table, conflicts, first, follow)
    if "--matriz" in sys.argv:
        print_matrix(rules, table)

    print("Conflictos LL(1):")
    if not conflicts:
        print("  ninguno")
    for (nt, t), prods in conflicts.items():
        alts = "  |  ".join(f"{nt} → {' '.join(p)}" for p in prods)
        print(f"  M[{nt}, {_q(t)}]: {alts}")
    if conflicts:
        print("\nResolución: se prefiere 'ElsePart → else Stmt' (el else se une al if más cercano),")
        print("que es lo que hace if_stmt() en parser.py al consumir el 'else' de inmediato.")


if __name__ == "__main__":
    main()
