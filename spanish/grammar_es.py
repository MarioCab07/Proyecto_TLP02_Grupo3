"""CFG para un subconjunto del español con concordancia de género y número.

Estrategia: una CFG no tiene variables ni rasgos, así que la concordancia se
codifica MULTIPLICANDO los no terminales: SN_fs = sintagma nominal femenino
singular, SN_mp = masculino plural, etc. Es válido (los rasgos son finitos)
pero la gramática crece con cada rasgo nuevo (ver grammar_growth).

Fenómenos cubiertos:
  * concordancia determinante-sustantivo-adjetivo (género y número)
  * concordancia sujeto-verbo (número, 3.ª persona)
  * atributo con 'ser/estar' (el adjetivo concuerda con el sujeto)
  * modificadores: adjetivos, adverbios, frases preposicionales
  * cláusulas subordinadas: relativa con sujeto relativizado ('que corre')
    y completiva ('dice que ...')
"""
from collections import defaultdict

GENDERS = ("m", "f")
NUMBERS = ("s", "p")
GN = [g + n for g in GENDERS for n in NUMBERS]

LEXICON_RAW = {
    "Det_ms": "el un", "Det_fs": "la una", "Det_mp": "los unos", "Det_fp": "las unas",
    "N_ms": "gato niño libro perro parque telescopio hombre",
    "N_fs": "gata niña casa mesa mujer manzana",
    "N_mp": "gatos niños libros perros parques telescopios hombres",
    "N_fp": "gatas niñas casas mesas mujeres manzanas",
    "Adj_ms": "pequeño rojo grande cansado feliz",
    "Adj_fs": "pequeña roja grande cansada feliz",
    "Adj_mp": "pequeños rojos grandes cansados felices",
    "Adj_fp": "pequeñas rojas grandes cansadas felices",
    "PropN_ms": "juan", "PropN_fs": "maría",
    # verbos transitivos/intransitivos en presente y pretérito (2 tiempos)
    "V_s": "duerme lee ve corre come canta durmió leyó vio corrió comió cantó",
    "V_p": "duermen leen ven corren comen cantan durmieron leyeron vieron corrieron comieron cantaron",
    "Vdec_s": "dice dijo piensa pensó", "Vdec_p": "dicen dijeron piensan pensaron",
    "Cop_s": "está estaba es fue", "Cop_p": "están estaban son fueron",
    "Adv": "bien mucho rápidamente ayer",
    "Prep": "con en de sobre para",
}
LEXICON = {k: set(v.split()) for k, v in LEXICON_RAW.items()}


def build_rules():
    R = defaultdict(list)
    for n in NUMBERS:
        # Oración: sujeto + predicado verbal, concordando en número
        R["O"].append([f"SNx_{n}", f"SV_{n}"])
        for g in GENDERS:
            R[f"SNx_{n}"].append([f"SN_{g}{n}"])
            R["SNobj"].append([f"SN_{g}{n}"])
    for g in GENDERS:
        for n in NUMBERS:
            gn = g + n
            # Oración copulativa: el adjetivo atributo concuerda con el sujeto (g y n)
            R["O"].append([f"SN_{gn}", f"Cop_{n}", f"Adj_{gn}"])
            # Sintagma nominal: Det y núcleo concuerdan
            R[f"SN_{gn}"].append([f"Det_{gn}", f"Nom_{gn}"])
            # Nominal con modificadores (sin recursión izquierda)
            R[f"Nom_{gn}"] += [
                [f"N_{gn}"],
                [f"N_{gn}", f"Adj_{gn}"],
                [f"N_{gn}", "SP"],
                [f"N_{gn}", f"Adj_{gn}", "SP"],
                [f"N_{gn}", f"Rel_{n}"],   # relativa: su verbo concuerda con el antecedente
            ]
    R["SN_ms"].append(["PropN_ms"])
    R["SN_fs"].append(["PropN_fs"])
    for n in NUMBERS:
        R[f"Rel_{n}"].append(["que", f"SV_{n}"])
        R[f"SV_{n}"] += [
            [f"V_{n}"],
            [f"V_{n}", "SNobj"],
            [f"V_{n}", "SNobj", "SP"],      # SP adjunta al verbo
            [f"V_{n}", "SP"],
            [f"V_{n}", "Adv"],
            [f"V_{n}", "SNobj", "Adv"],
            [f"Vdec_{n}", "que", "O"],      # completiva
        ]
    R["SP"].append(["Prep", "SNobj"])
    return dict(R)


RULES = build_rules()


def tokenize_es(sentence: str):
    for ch in ".,;¿?¡!":
        sentence = sentence.replace(ch, " ")
    return sentence.lower().split()


def grammar_stats():
    n_rules = sum(len(v) for v in RULES.values())
    return len(RULES), n_rules


def grammar_growth():
    """Cuántas versiones de cada categoría necesita una CFG según los rasgos que se codifiquen."""
    dims = [("género (2)", 2), ("número (2)", 2), ("persona (3)", 3), ("tiempo (2)", 2), ("modo (3)", 3)]
    rows, total, names = [], 1, []
    for name, size in dims:
        total *= size
        names.append(name.split()[0])
        rows.append((" × ".join(names), total))
    return rows
