"""Enfoque 1: parser propio con retroceso sobre la CFG (G2).

Decisión: 'aceptada' si el parser devuelve al menos un árbol que consuma toda la
oración; 'rechazada' si no. Se enumeran hasta MAX_PARSES árboles para contar lecturas.
Además de la decisión se guarda cada árbol en notación gruesa (la misma de
estructura_esperada del corpus) y, si se rechaza, el diagnóstico del parser.
"""
import itertools
import time

from common import load_corpus, now_iso, write_run

# >>> AJUSTA estas dos líneas a las rutas de tu repositorio <<<
from spanish.grammar_es import RULES, LEXICON, tokenize_es
from cfg_core.engine import TopDownParser

MAX_PARSES = 50


def _lab(n):
    return getattr(n, "label", None) or getattr(n, "sym", None) or getattr(n, "name", None)


def _kids(n):
    return getattr(n, "children", None) or []


def _coarse(n):
    """Árbol -> lista de tokens en la notación gruesa del corpus (SN, SV, SP, Rel, Comp, Atr, Adv)."""
    lab, ks = _lab(n), _kids(n)
    if not ks:                                   # hoja: palabra o 'que'; un no terminal vacío (ε) no aporta nada
        return [] if lab in RULES else [lab]
    flat = lambda xs: [t for k in xs for t in _coarse(k)]
    if lab == "O":
        return ["[O"] + flat(ks) + ["]"]
    if lab.startswith("SN_"):
        return ["[SN"] + flat(ks) + ["]"]
    if lab == "SP":
        return ["[SP"] + flat(ks) + ["]"]
    if lab.startswith("Rel_"):
        return ["[Rel"] + flat(ks) + ["]"]
    if lab == "Adv":
        return ["[Adv"] + flat(ks) + ["]"]
    if lab.startswith("SV_"):
        if len(ks) == 3 and _lab(ks[1]) == "que":           # Vdec que O
            return ["[SV"] + _coarse(ks[0]) + ["[Comp"] + _coarse(ks[1]) + _coarse(ks[2]) + ["]", "]"]
        return ["[SV"] + flat(ks) + ["]"]
    if lab.startswith("Pred_") and len(ks) == 2:             # Cop Adj -> [SV cop [Atr adj]]
        return ["[SV"] + _coarse(ks[0]) + ["[Atr"] + _coarse(ks[1]) + ["]", "]"]
    return flat(ks)                                          # preterminales y auxiliares: transparentes


def coarse(tree):
    return " ".join(_coarse(tree)).replace(" ]", "]")


def main(corpus_path="corpus/corpus_tlp02_v2.csv"):
    parser = TopDownParser(RULES, LEXICON)
    records = []
    for row in load_corpus(corpus_path):
        tokens = tokenize_es(row["oracion"])
        t0 = time.perf_counter()
        trees = list(itertools.islice(parser.parses(tokens), MAX_PARSES))
        ms = (time.perf_counter() - t0) * 1000
        raw = {"tokens": tokens, "n_parses": len(trees), "ms": round(ms, 3),
               "estructuras": [coarse(t) for t in trees]}
        if not trees:
            raw["diagnostico"] = parser.diagnose(tokens)
        records.append({"id": row["id"], "oracion": row["oracion"],
                        "decision": "aceptada" if trees else "rechazada",
                        "timestamp": now_iso(), "raw": raw})
    write_run("cfg", records, {"enfoque": "parser propio (retroceso) sobre CFG G2",
                               "max_parses": MAX_PARSES})


if __name__ == "__main__":
    main()
