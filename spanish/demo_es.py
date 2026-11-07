"""Demo Fase 1: intento de extender la CFG al español y puntos de falla.

Uso:  python -m spanish.demo_es [--arboles]

Cada caso tiene: oración, si ES gramatical en español real (esperado),
el fenómeno y el nivel teórico asociado. Se compara contra lo que la
gramática hace. Resultado:
  OK                 la CFG coincide con el español
  FALSO NEGATIVO     el español la admite y la CFG la rechaza (subgeneración)
  FALSO POSITIVO     el español la rechaza y la CFG la acepta (sobregeneración)
"""
import itertools
import sys

from .grammar_es import LEXICON, RULES, grammar_growth, grammar_stats, tokenize_es
from cfg_core.engine import TopDownParser

# (oración, ¿gramatical en español?, fenómeno, comentario formal)
CASOS = [
    # --- Lo que la CFG sí resuelve ---------------------------------------
    ("el gato duerme", True, "SVO básico", "regla O → SNx_s SV_s"),
    ("las niñas pequeñas leen los libros", True, "concordancia N-Adj y S-V", "no terminales multiplicados (SN_fp, SV_p)"),
    ("el niño come bien", True, "adverbio", "SV_s → V_s Adv"),
    ("María dice que los niños corren", True, "subordinada completiva", "recursión centrada: O → ... Vdec que O"),
    ("las niñas que leen el libro están cansadas", True, "concordancia a distancia", "funciona, pero Rel_n y Nom_gn duplican reglas"),
    ("el hombre vio el gato con el telescopio", True, "ambigüedad de adjunción de SP", "2 árboles: la CFG enumera, no desambigua"),
    ("el gatos duerme", False, "error de número Det-N", "rechazada: Det_ms no combina con N_mp"),
    ("la niño pequeño duerme", False, "error de género Det-N", "rechazada correctamente"),
    ("los niños corre", False, "error de número S-V", "rechazada: SNx_p exige SV_p"),
    ("las niñas que lee el libro están cansadas", False, "error de concordancia dentro de la relativa", "rechazada: Rel_p → que SV_p"),
    ("las niñas están cansados", False, "género del atributo", "rechazada: Adj_fp ≠ Adj_mp"),
    # --- Puntos de falla --------------------------------------------------
    ("duerme el gato", True, "orden libre (VS)", "FALLA: cada orden exige reglas nuevas; el español es de orden flexible"),
    ("canta bien", True, "sujeto nulo (pro-drop)", "FALLA: el sujeto no está en la superficie; la CFG exige un SN explícito"),
    ("el gato duerme el libro", False, "subcategorización", "FALLA: no distingue verbos transitivos/intransitivos; V_s acepta cualquier objeto"),
    ("las niñas que Juan vio están cansadas", True, "relativa de objeto (hueco/gap)", "FALLA: requiere dependencia a distancia con hueco; en CFG exige categorías X/SN (slash)"),
    ("maría lo vio", True, "clítico", "FALLA: el pronombre aparece fuera de su posición argumental (movimiento)"),
    ("el niño vio al hombre", True, "contracción 'al' = a + el", "FALLA: fenómeno morfológico; 'al' no es ni Prep ni Det"),
]


def main():
    show_trees = "--arboles" in sys.argv
    parser = TopDownParser(RULES, LEXICON, "O")
    nt, nr = grammar_stats()
    print(f"Gramática del español: {nt} no terminales, {nr} producciones, "
          f"{sum(len(v) for v in LEXICON.values())} categorías léxicas x palabras\n")

    resumen = {"OK": 0, "FALSO NEGATIVO": 0, "FALSO POSITIVO": 0}
    for oracion, gramatical, fenomeno, nota in CASOS:
        tokens = tokenize_es(oracion)
        arboles = list(parser.parses(tokens))
        aceptada = bool(arboles)
        if aceptada == gramatical:
            res = "OK"
        else:
            res = "FALSO NEGATIVO" if gramatical else "FALSO POSITIVO"
        resumen[res] += 1
        print(f"[{res}] «{oracion}»")
        print(f"    fenómeno : {fenomeno}")
        print(f"    CFG      : {'acepta, %d árbol(es)' % len(arboles) if aceptada else 'rechaza'}"
              f"{'' if aceptada else ' — ' + parser.diagnose(tokens)}")
        print(f"    nota     : {nota}")
        if show_trees and arboles:
            for k, a in enumerate(arboles, 1):
                print(f"    --- árbol {k} ---")
                print("\n".join("    " + ln for ln in a.pretty().splitlines()))
        print()

    print("Resumen:", resumen, "\n")

    print("Crecimiento de la gramática al codificar más rasgos (versiones por categoría):")
    for desc, n in grammar_growth():
        print(f"  {desc:<42} → x{n}")

    formal_limit_experiment()


def formal_limit_experiment():
    """aⁿbⁿcⁿ (modelo de dependencias cruzadas): la mejor CFG 'natural' sobregenera.

    Ninguna CFG genera exactamente aⁿbⁿcⁿ (lema de bombeo para CFL). Mostramos
    el intento más directo y contamos cuántas cadenas acepta de más.
    """
    rules = {"S": [["X", "C"]], "X": [["a", "X", "b"], []], "C": [["c", "C"], []]}
    p = TopDownParser(rules, {}, "S")
    def en_L(w):
        n = len(w) // 3
        return w == "a" * n + "b" * n + "c" * n
    aceptadas = falsos = 0
    for L in range(0, 10):
        for w in itertools.product("abc", repeat=L):
            w = "".join(w)
            if any(True for _ in p.parses(list(w))):
                aceptadas += 1
                if not en_L(w):
                    falsos += 1
    print("\nLímite formal: intento de CFG para aⁿbⁿcⁿ (cadenas de longitud ≤ 9)")
    print("  gramática: S → X C ; X → a X b | ε ; C → c C | ε")
    print(f"  cadenas aceptadas: {aceptadas}, de las cuales NO pertenecen a aⁿbⁿcⁿ: {falsos}")
    print("  (genera aⁿbⁿcᵐ: la CFG no puede contar tres series a la vez → nivel 1, sensible al contexto)")


if __name__ == "__main__":
    main()
