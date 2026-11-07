"""El motor genérico debe coincidir con el parser LL(1) de Java y con el del español."""
import unittest

from cfg_core.engine import TopDownParser
from java_subset.engine_adapter import parse_all
from spanish.grammar_es import LEXICON, RULES, tokenize_es
from tests.test_java_parser import INVALIDOS, VALIDOS


class TestMotorUnico(unittest.TestCase):
    def test_mismo_veredicto_que_el_parser_ll1(self):
        for nombre, src in VALIDOS.items():
            with self.subTest("valido: " + nombre):
                trees, _ = parse_all(src)
                self.assertGreaterEqual(len(trees), 1)
        for nombre, (src, _) in INVALIDOS.items():
            with self.subTest("invalido: " + nombre):
                trees, err = parse_all(src)
                self.assertEqual(trees, [])
                self.assertIsNotNone(err)

    def test_dangling_else_son_dos_arboles(self):
        trees, _ = parse_all("if (a) if (b) x = 1; else x = 2;")
        self.assertEqual(len(trees), 2)

    def test_sin_ambiguedad_un_arbol(self):
        trees, _ = parse_all("int x = 1 + 2 * 3;")
        self.assertEqual(len(trees), 1)

    def test_espanol_en_el_mismo_motor(self):
        p = TopDownParser(RULES, LEXICON, "O")
        self.assertEqual(len(list(p.parses(tokenize_es("el hombre vio el gato con el telescopio")))), 2)
        self.assertEqual(len(list(p.parses(tokenize_es("el gatos duerme")))), 0)


if __name__ == "__main__":
    unittest.main()