Corpus: 60 oraciones (38 aceptadas, 22 rechazadas). Referencia de la gramática: decisión del log 'cfg'. Los corchetes son intervalos de confianza 95 % (Wilson).

**Tabla 1. Métricas por enfoque (%)**

| Enfoque | Precisión | Recall | Rechazo correcto | Exactitud | F1 |
|---|---|---|---|---|---|
| cfg | 100.0 [87.5–100.0] | 71.1 [55.2–83.0] | 100.0 [85.1–100.0] | 81.7 [70.1–89.4] | 83.1 |
| spacy | 94.3 [81.4–98.4] | 86.8 [72.7–94.2] | 90.9 [72.2–97.5] | 88.3 [77.8–94.2] | 90.4 |
| hf | 78.4 [62.8–88.6] | 76.3 [60.8–87.0] | 63.6 [43.0–80.3] | 71.7 [59.2–81.5] | 77.3 |
| llm_zero | 100.0 [89.0–100.0] | 81.6 [66.6–90.8] | 100.0 [85.1–100.0] | 88.3 [77.8–94.2] | 89.9 |
| llm_few | 100.0 [89.0–100.0] | 81.6 [66.6–90.8] | 100.0 [85.1–100.0] | 88.3 [77.8–94.2] | 89.9 |

**Tabla 2. Clasificación de errores**

| Enfoque | TP | FP | TN | FN | Sin decisión | Errores de estructura |
|---|---|---|---|---|---|---|
| cfg | 27 | 0 | 22 | 11 | 0 | 0 |
| spacy | 33 | 2 | 20 | 5 | 0 | n/a |
| hf | 29 | 8 | 14 | 9 | 0 | n/a |
| llm_zero | 31 | 0 | 22 | 7 | 0 | 6 |
| llm_few | 31 | 0 | 22 | 7 | 0 | 6 |

**Tabla 3. Exactitud por nivel (%)**

| Enfoque | Nivel 1 | Nivel 2 | Nivel 3 |
|---|---|---|---|
| cfg | 100.0 [67.6–100.0] | 95.5 [78.2–99.2] | 66.7 [48.8–80.8] |
| spacy | 100.0 [67.6–100.0] | 95.5 [78.2–99.2] | 80.0 [62.7–90.5] |
| hf | 87.5 [52.9–97.8] | 77.3 [56.6–89.9] | 63.3 [45.5–78.1] |
| llm_zero | 100.0 [67.6–100.0] | 100.0 [85.1–100.0] | 76.7 [59.1–88.2] |
| llm_few | 100.0 [67.6–100.0] | 100.0 [85.1–100.0] | 76.7 [59.1–88.2] |

**Tabla 4. Fidelidad a la gramática en oraciones donde la etiqueta y la CFG difieren**

| Enfoque | Acuerdo con la referencia (%) | Oraciones discrepantes | Sigue a la gramática | Sigue a la etiqueta |
|---|---|---|---|---|
| spacy | 83.3 | 11 | 4 | 7 |
| hf | 63.3 | 11 | 3 | 8 |
| llm_zero | 93.3 | 11 | 7 | 4 |
| llm_few | 93.3 | 11 | 7 | 4 |

**Tabla 5. McNemar exacto entre pares (p-valor)**

| A | B | A acierta / B falla | B acierta / A falla | p |
|---|---|---|---|---|
| cfg | spacy | 3 | 7 | 0.3438 |
| cfg | hf | 14 | 8 | 0.2863 |
| cfg | llm_zero | 0 | 4 | 0.125 |
| cfg | llm_few | 0 | 4 | 0.125 |
| spacy | hf | 15 | 5 | 0.0414 |
| spacy | llm_zero | 5 | 5 | 1.0 |
| spacy | llm_few | 5 | 5 | 1.0 |
| hf | llm_zero | 6 | 16 | 0.0525 |
| hf | llm_few | 6 | 16 | 0.0525 |
| llm_zero | llm_few | 0 | 0 | 1.0 |

**Tabla 6. Estructuras (verdaderos positivos con árbol de referencia)**

| Enfoque | TP con árbol | Completos | Parciales | Otras diferencias | Errores estructura | Errores formato | Etiquetas no permitidas |
|---|---|---|---|---|---|---|---|
| cfg | 27 | 27 | 0 | 0 | 0 | 0 | 0 |
| spacy |  |  |  | n/a |  |  |  |
| hf |  |  |  | n/a |  |  |  |
| llm_zero | 31 | 25 | 2 | 4 | 6 | 0 | 0 |
| llm_few | 31 | 22 | 2 | 4 | 6 | 3 | 3 |
