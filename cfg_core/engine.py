"""Parser descendente genérico con retroceso (backtracking) para una CFG.

A diferencia del parser LL(1) de Java, el español es ambiguo, así que aquí
necesitamos devolver TODAS las derivaciones posibles (un generador).

Limitaciones deliberadas (son parte del experimento):
  * No admite recursión izquierda: se detecta y se lanza LeftRecursionError.
  * Registra el punto más lejano alcanzado para diagnosticar dónde falla.
"""
from .tree import Node


class LeftRecursionError(Exception):
    pass


class TopDownParser:
    def __init__(self, rules, lexicon, start="O"):
        """rules: NT -> lista de producciones (listas de símbolos).
        lexicon: preterminal -> conjunto de palabras. Todo símbolo que no sea
        NT ni preterminal se trata como terminal literal (p. ej. 'que')."""
        self.rules = {nt: [[] if p == ["ε"] else p for p in prods] for nt, prods in rules.items()}
        self.lexicon, self.start = lexicon, start

    # -------------------------------------------------------------- API
    def parses(self, tokens):
        """Genera todos los árboles que consumen exactamente `tokens`."""
        self.fail_pos, self.fail_expected = -1, set()
        for node, j in self._expand(self.start, 0, tokens, frozenset()):
            if j == len(tokens):
                yield node

    def diagnose(self, tokens):
        """Texto con el punto más lejano alcanzado al fallar."""
        i = self.fail_pos
        if i >= len(tokens):
            return "la oración termina antes de lo que la gramática espera"
        exp = ", ".join(sorted(self.fail_expected)[:6])
        return f"falla en la palabra {i + 1} «{tokens[i]}»; la gramática esperaba: {exp}"

    # --------------------------------------------------------- interno
    def _miss(self, i, sym):
        if i > self.fail_pos:
            self.fail_pos, self.fail_expected = i, {sym}
        elif i == self.fail_pos:
            self.fail_expected.add(sym)

    def _expand(self, sym, i, tokens, active):
        if sym in self.lexicon:                      # preterminal → palabra
            if i < len(tokens) and tokens[i] in self.lexicon[sym]:
                yield Node(sym, [Node(tokens[i])]), i + 1
            else:
                self._miss(i, sym)
        elif sym in self.rules:                      # no terminal → producciones
            if (sym, i) in active:
                raise LeftRecursionError(f"recursión izquierda en {sym}")
            active = active | {(sym, i)}
            for prod in self.rules[sym]:
                for children, j in self._seq(prod, i, tokens, active):
                    yield Node(sym, children), j
        else:                                        # terminal literal
            if i < len(tokens) and tokens[i] == sym:
                yield Node(sym), i + 1
            else:
                self._miss(i, repr(sym))

    def _seq(self, prod, i, tokens, active):
        if not prod:
            yield [], i
            return
        for node, j in self._expand(prod[0], i, tokens, active):
            for rest, k in self._seq(prod[1:], j, tokens, active):
                yield [node] + rest, k
