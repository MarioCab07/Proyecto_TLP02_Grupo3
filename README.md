# Proyecto TLP02-2026 · Fase 1

Parser LL(1)/descendente recursivo para un subconjunto de Java, intento de
extender la CFG al español y comparación con spaCy.

## Estructura

```
fase1/
├── README.md
├── requirements.txt
├── demo_java.py                 Demo del parser LL(1) de Java
├── demo_unificado.py            Demo del motor único (Java y español)
├── cfg_core/
│   ├── __init__.py
│   ├── tree.py                  Node: árbol de análisis compartido
│   └── engine.py                Motor descendente con retroceso (todas las derivaciones)
├── java_subset/
│   ├── __init__.py
│   ├── lexer.py                 Lexer (tokens, línea y columna)
│   ├── parser.py                Parser descendente recursivo LL(1) + recuperación de errores
│   ├── ll1.py                   FIRST, FOLLOW, tabla LL(1) y detección de conflictos
│   └── engine_adapter.py        Corre la gramática BNF de Java en cfg_core/engine.py
├── spanish/
│   ├── __init__.py
│   ├── grammar_es.py            CFG del español y léxico
│   ├── demo_es.py               Casos de prueba, fallas y experimento aⁿbⁿcⁿ
│   └── demo_spacy.py            Las mismas oraciones procesadas con spaCy
└── tests/
    ├── __init__.py
    ├── test_java_parser.py      8 pruebas: parser de Java
    ├── test_motor_unico.py      4 pruebas: motor único frente al parser LL(1)
    └── test_espanol.py          2 pruebas: casos del español y fallas conocidas
```

## Comandos

### Parser de Java
 
# --- Instalación (solo para spaCy) ---
1. python -m venv venv 
2. venv\Scripts\activate (Windows) / source venv/bin/activate (Linux, Mac)
3. pip install -r requirements.txt
4. python -m spacy download es_core_news_sm

# --- Parser de Java ---
- python demo_java.py                         # demo con casos integrados
- python demo_java.py archivo.java            # analiza un archivo Java propio
- python -m java_subset.ll1                   # FIRST, FOLLOW, tabla LL(1) y conflictos
- python -m java_subset.ll1 --matriz          # agrega la matriz completa M[no terminal, token]

# --- Motor único (Java y español en el mismo motor) ---
- python demo_unificado.py

# --- Gramática del español ---
- python -m spanish.demo_es                   # 17 oraciones, fallas, crecimiento y experimento a^n b^n c^n
- python -m spanish.demo_es --arboles         # agrega el árbol de cada oración aceptada
- python -m spanish.demo_spacy                # las mismas 17 oraciones con spaCy

# --- Analizar oraciones propias en español ---
- python analizar_es.py                       # modo interactivo (línea vacía o "salir" termina)
- python analizar_es.py "el gato duerme"      # una oración
- python analizar_es.py "oración 1" "oración 2"   # varias oraciones
- python analizar_es.py demo/oraciones.txt    # archivo con una oración por línea (# = comentario)
- python analizar_es.py --todos "..."         # si es ambigua, imprime todos los árboles
- python analizar_es.py --spacy "..."         # agrega el análisis de spaCy
- python analizar_es.py --lexico              # muestra las palabras que conoce la gramática

# --- Pruebas ---
- python -m unittest discover -s tests -v     # las 14 pruebas
- python -m unittest tests.test_java_parser -v    # 8 pruebas del parser
- python -m unittest tests.test_motor_unico -v    # 4 pruebas del motor único
- python -m unittest tests.test_espanol -v        # 2 pruebas del español

### Pruebas

| Comando | Qué se espera |
|---|---|
| `python -m unittest discover -s tests -v` | Las 14 pruebas, terminando en `Ran 14 tests` y `OK`. |
| `python -m unittest tests.test_java_parser -v` | `Ran 8 tests` y `OK`. |
| `python -m unittest tests.test_motor_unico -v` | `Ran 4 tests` y `OK`. |
| `python -m unittest tests.test_espanol -v` | `Ran 2 tests` y `OK`. |

## Oraciones del español analizadas

1. el gato duerme
2. las niñas pequeñas leen los libros
3. el niño come bien
4. María dice que los niños corren
5. las niñas que leen el libro están cansadas
6. el hombre vio el gato con el telescopio
7. el gatos duerme
8. la niño pequeño duerme
9. los niños corre
10. las niñas que lee el libro están cansadas
11. las niñas están cansados
12. duerme el gato
13. canta bien
14. el gato duerme el libro
15. las niñas que Juan vio están cansadas
16. maría lo vio
17. el niño vio al hombre
