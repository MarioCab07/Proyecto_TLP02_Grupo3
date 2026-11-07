"""Demo Fase 1: las MISMAS oraciones de demo_es.py procesadas con spaCy.

Requisitos:
    pip install spacy
    python -m spacy download es_core_news_sm

Uso:  python -m spanish.demo_spacy

Qué observar:
  * spaCy SIEMPRE devuelve un análisis (no "rechaza"): es un modelo estadístico
    que elige la estructura más probable, incluso para oraciones agramaticales.
  * Maneja orden libre, sujeto nulo, clíticos, contracciones y relativas de objeto,
    justo donde la CFG falla.
  * Desambigua la adjunción del SP eligiendo UN solo árbol (la CFG daba dos).
  * Costo: no hay regla que explique el porqué; el análisis es opaco.
"""
import sys

from .demo_es import CASOS

try:
    import spacy
    nlp = spacy.load("es_core_news_sm")
except (ImportError, OSError):
    sys.exit("Falta spaCy o el modelo. Ejecuta:\n  pip install spacy\n  python -m spacy download es_core_news_sm")


def rasgos(tok):
    g, n = tok.morph.get("Gender"), tok.morph.get("Number")
    return "/".join(g + n) or "-"


def main():
    for oracion, gramatical, fenomeno, _ in CASOS:
        doc = nlp(oracion)
        print(f"\n«{oracion}»   [español real: {'gramatical' if gramatical else 'agramatical'}; fenómeno: {fenomeno}]")
        print(f"  {'palabra':<12}{'POS':<7}{'dep':<10}{'cabeza':<12}rasgos")
        for t in doc:
            print(f"  {t.text:<12}{t.pos_:<7}{t.dep_:<10}{t.head.text:<12}{rasgos(t)}")

        # Chequeos puntuales ligados a los fenómenos de la demo
        for t in doc:
            if t.text.lower() == "con":
                print(f"  → adjunción del SP: 'con' cuelga de '{t.head.text}' ({t.head.pos_}); "
                      f"spaCy elige UNA lectura, la CFG enumeraba 2")
        for t in doc:
            if t.dep_ == "det" and t.head.pos_ in ("NOUN", "PROPN"):
                if set(t.morph.get("Number")) != set(t.head.morph.get("Number")) and t.morph.get("Number") and t.head.morph.get("Number"):
                    print(f"  → ojo: '{t.text}' y '{t.head.text}' no concuerdan en número, y aun así spaCy produce un árbol")


if __name__ == "__main__":
    main()
