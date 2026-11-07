"""Pruebas del parser de Java. Ejecutar:  python -m unittest discover -s tests -v"""
import unittest

from java_subset.lexer import tokenize
from java_subset.ll1 import build_table, load_grammar
from java_subset.parser import parse

VALIDOS = {
    "declaracion simple": "int x;",
    "declaracion con valor": "int x = 5;",
    "boolean y string": 'boolean b = true; String s = "hola";',
    "asignacion": "x = x + 1;",
    "precedencia": "int r = 1 + 2 * 3 - 4 / 2;",
    "logicos y relacionales": "boolean ok = (a < b) && !(c == d) || e != f;",
    "unarios": "int n = -(-x); boolean t = !!flag;",
    "if": "if (x > 0) x = 1;",
    "if else": "if (x > 0) x = 1; else x = 2;",
    "while": "while (i < 10) i = i + 1;",
    "bloque": "{ int a = 1; { a = 2; } }",
    "println": 'System.out.println("x = " + x);',
    "dangling else": "if (a) if (b) x = 1; else x = 2;",
    "comentarios": "// linea\nint x = 1; /* bloque\nmultilinea */ x = 2;",
    "programa vacio": "",
    "programa completo": """
        int i = 0;
        int suma = 0;
        while (i < 5) {
            if (i != 3) suma = suma + i; else suma = suma - 1;
            i = i + 1;
        }
        System.out.println(suma);
    """,
}

INVALIDOS = {
    "falta ;": ("int x = 5", "se esperaba ';'"),
    "expresion vacia": ("int x = ;", "se esperaba una expresión"),
    "falta )": ("while (x < 3 { x = 1; }", "se esperaba ')'"),
    "falta (": ("if x > 0) x = 1;", "se esperaba '('"),
    "llave sin cerrar": ("{ int a = 1;", "se esperaba '}'"),
    "llave suelta": ("}", "se esperaba una sentencia"),
    "relacional encadenado": ("boolean b = a < b < c;", "se esperaba ';'"),
    "declaracion sin ID": ("int = 5;", "se esperaba 'ID'"),
    "operador sin operando": ("x = 3 + ;", "se esperaba una expresión"),
    "else huerfano": ("else x = 1;", "se esperaba una sentencia"),
    "caracter ilegal": ("int x = 3 @ 4;", "carácter ilegal"),
    "cadena sin cerrar": ('String s = "hola;', "cadena sin cerrar"),
    "comentario sin cerrar": ("int x; /* hola", "comentario /* sin cerrar"),
    "palabra reservada como ID": ("int if = 3;", "se esperaba 'ID'"),
    "println incompleto": ("System.out.println(x)", "se esperaba ';'"),
}


class TestValidos(unittest.TestCase):
    def test_validos(self):
        for nombre, src in VALIDOS.items():
            with self.subTest(nombre):
                tree, errors = parse(src)
                self.assertEqual(errors, [], f"{nombre}: {errors}")
                self.assertEqual(tree.label, "Program")


class TestInvalidos(unittest.TestCase):
    def test_invalidos(self):
        for nombre, (src, fragmento) in INVALIDOS.items():
            with self.subTest(nombre):
                _, errors = parse(src)
                self.assertTrue(errors, f"{nombre}: debía rechazarse")
                self.assertTrue(any(fragmento in e for e in errors),
                                f"{nombre}: esperaba '{fragmento}' en {errors}")

    def test_posicion_del_error(self):
        _, errors = parse("int a = 1;\nint b = ;")
        self.assertIn("Línea 2", errors[0])

    def test_recuperacion_reporta_varios_errores(self):
        _, errors = parse("int x = ;\ny = 3 +;\nint z = 1;")
        self.assertEqual(len(errors), 2)


class TestEstructuraDelArbol(unittest.TestCase):
    def test_precedencia(self):
        # 1 + 2 * 3  → el * queda DENTRO de un Term, más profundo que el +
        tree, _ = parse("x = 1 + 2 * 3;")
        add = tree.children[0].children[2].children[0].children[0].children[0]
        self.assertEqual(add.label, "AddExpr")
        self.assertEqual([c.label for c in add.children], ["Term", "+", "Term"])
        self.assertEqual([c.label for c in add.children[2].children], ["Factor", "*", "Factor"])

    def test_dangling_else_se_une_al_if_mas_cercano(self):
        tree, errors = parse("if (a) if (b) x = 1; else x = 2;")
        self.assertEqual(errors, [])
        outer = tree.children[0]
        inner = outer.children[4]
        self.assertEqual(inner.label, "If")
        self.assertNotIn("else", [c.label for c in outer.children])   # el if externo NO tiene else
        self.assertIn("else", [c.label for c in inner.children])      # el interno SÍ

    def test_lexer_println_y_keywords(self):
        toks, errs = tokenize("System.out.println(true)")
        self.assertEqual(errs, [])
        self.assertEqual([t.type for t in toks], ["System.out.println", "(", "true", ")", "EOF"])


class TestTablaLL1(unittest.TestCase):
    def test_unico_conflicto_es_dangling_else(self):
        rules, start = load_grammar()
        _, conflicts, _, _ = build_table(rules, start)
        self.assertEqual(list(conflicts), [("ElsePart", "else")])


if __name__ == "__main__":
    unittest.main()
