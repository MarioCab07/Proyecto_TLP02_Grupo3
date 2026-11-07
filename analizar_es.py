"""Analiza oraciones propias del español con la CFG de spanish/grammar_es.py.
Es el equivalente de `python demo_java.py archivo.java`, pero para español.
Uso:
    python analizar_es.py                        # modo interactivo (línea vacía o 'salir' termina)
    python analizar_es.py "el gato duerme"       # una oración
    python analizar_es.py oraciones.txt          # archivo con una oración por línea (# = comentario)
    python analizar_es.py --todos  ...           # imprime TODOS los árboles si hay ambigüedad
    python analizar_es.py --spacy  ...           # agrega el análisis de spaCy de la misma oración
    python analizar_es.py --lexico               # muestra las palabras que conoce la gramática
"""
import os
import sys
from cfg_core.engine import TopDownParser
from spanish.grammar_es import LEXICON, RULES, tokenize_es
CONOCIDAS = set().union(*LEXICON.values()) | {"que"}
def categorias(palabra):
    return sorted(cat for cat, palabras in LEXICON.items() if palabra in palabras)
def mostrar_lexico():
    print(f"Léxico cerrado: {len(CONOCIDAS)} palabras en {len(LEXICON)} categorías\n")
    for cat, palabras in LEXICON.items():
        print(f"  {cat:<9} {' '.join(sorted(palabras))}")
    print("  que       (terminal literal: relativas y completivas)")
def analizar_spacy(oracion):
    try:
        import spacy
        nlp = spacy.load("es_core_news_sm")
    except (ImportError, OSError):
        print("  [spaCy no está instalado: pip install spacy && python -m spacy download es_core_news_sm]")
        return
    doc = nlp(oracion)
    print("  spaCy:")
    print(f"    {'palabra':<12}{'POS':<7}{'dep':<10}{'cabeza':<12}rasgos")
    for t in doc:
        rasgos = "/".join(t.morph.get("Gender") + t.morph.get("Number")) or "-"
        print(f"    {t.text:<12}{t.pos_:<7}{t.dep_:<10}{t.head.text:<12}{rasgos}")
def analizar(parser, oracion, todos=False, con_spacy=False):
    tokens = tokenize_es(oracion)
    print("=" * 70)
    print(f"«{oracion}»")
    if not tokens:
        print("  (oración vacía)")
        return
    # Léxico cerrado: una palabra desconocida falla antes que cualquier regla.
    desconocidas = [t for t in tokens if t not in CONOCIDAS]
    if desconocidas:
        print(f"  RECHAZADA (léxico): la gramática no conoce {', '.join('«' + d + '»' for d in desconocidas)}")
        print("  (el léxico es cerrado a propósito; usa --lexico para ver las palabras disponibles)")
    else:
        arboles = list(parser.parses(tokens))
        if arboles:
            print(f"  ACEPTADA — {len(arboles)} árbol(es) de análisis")
            for i, a in enumerate(arboles if todos else arboles[:1], 1):
                if len(arboles) > 1 and todos:
                    print(f"  --- árbol {i} ---")
                print("\n".join("  " + ln for ln in a.pretty().splitlines()))
            if len(arboles) > 1 and not todos:
                print("  (ambigua: usa --todos para ver los demás árboles)")

        else:
            print(f"  RECHAZADA — {parser.diagnose(tokens)}")
    if con_spacy:
        analizar_spacy(oracion)
    print()
def main():
    args = sys.argv[1:]
    todos, con_spacy = "--todos" in args, "--spacy" in args
    if "--lexico" in args:
        mostrar_lexico()
        return
    args = [a for a in args if not a.startswith("--")]
    parser = TopDownParser(RULES, LEXICON, "O")
    if not args:                                   # modo interactivo
        print("Escribe una oración (línea vacía para salir).")
        while True:
            try:
                oracion = input("oración> ").strip()
            except EOFError:
                break
            if not oracion or oracion.lower() == "salir":
                break
            analizar(parser, oracion, todos, con_spacy)
    elif os.path.isfile(args[0]):                  # archivo, una oración por línea
        with open(args[0], encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea and not linea.startswith("#"):
                    analizar(parser, linea, todos, con_spacy)
    else:                                          # oración(es) en la línea de comandos
        for oracion in args:
            analizar(parser, oracion, todos, con_spacy)
if __name__ == "__main__":
    main()
