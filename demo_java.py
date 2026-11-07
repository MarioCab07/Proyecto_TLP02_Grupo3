"""Demo Fase 1: el parser de Java funcionando y manejando errores.

Uso:
    python demo_java.py                 # demo con ejemplos integrados
    python demo_java.py archivo.java    # analiza un archivo propio
"""
import sys

from java_subset.parser import parse

VALIDO = """\
int i = 0;
int suma = 0;
while (i < 5) {
    if (i != 3) suma = suma + i; else suma = suma - 1;
    i = i + 1;
}
System.out.println("suma = " + suma);
"""

INVALIDOS = [
    ("falta punto y coma", "int x = 5\nx = x + 1;"),
    ("expresión vacía", "int y = ;"),
    ("falta paréntesis", "while (x < 3 { x = x + 1; }"),
    ("varios errores (modo pánico)", "int a = ;\nb = 3 +;\nint c = 1;\n}"),
    ("carácter ilegal", "int z = 3 @ 4;"),
]

DANGLING = "if (a) if (b) x = 1; else x = 2;"


def run(titulo, src, mostrar_arbol=True):
    print("=" * 70)
    print(titulo)
    print("-" * 70)
    print(src.rstrip())
    tree, errors = parse(src)
    print("-" * 70)
    if errors:
        print(f"RECHAZADO ({len(errors)} error/es):")
        for e in errors:
            print("  ✗", e)
    else:
        print("ACEPTADO")
        if mostrar_arbol:
            print(tree.pretty())
    print()


def main():
    if len(sys.argv) > 1:
        src = open(sys.argv[1], encoding="utf-8").read()
        run(f"Archivo: {sys.argv[1]}", src)
        return
    run("1) Programa válido", VALIDO, mostrar_arbol=False)
    run("2) Árbol de una expresión (precedencia: * antes que +)", "int r = 1 + 2 * 3;")
    run("3) Dangling else: el else se une al if más cercano", DANGLING)
    for nombre, src in INVALIDOS:
        run(f"4) Entrada inválida: {nombre}", src)


if __name__ == "__main__":
    main()
