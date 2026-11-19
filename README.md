# Proyecto TLP02-2026 · Fases 1 y 2

**Teoría de Lenguajes de Programación** — Gramáticas formales, analizadores sintácticos y comparación experimental sobre un subconjunto del español.

> **Directorio de trabajo:** los comandos de esta guía se ejecutan desde la **raíz del proyecto**, es decir, la carpeta donde están `run_cfg.py`, `run_spacy.py`, `run_hf.py`, `run_llm.py` y `evaluar_fase2_v3.py`. No se ejecutan desde `corpus/` ni `logs/`.
>

---

## Fase 1 · Parsers y gramáticas

Parser LL(1)/descendente recursivo para un subconjunto de Java, intento de extender una CFG al español y comparación inicial con spaCy.

### 1.1. Estructura de la Fase 1

```text
fase1/
├── README.md
├── requirements.txt
├── demo_java.py                  Demo del parser LL(1) de Java
├── demo_unificado.py             Demo del motor único (Java y español)
├── analizar_es.py                Analizador interactivo del español
├── cfg_core/
│   ├── __init__.py
│   ├── tree.py                   Node: árbol de análisis compartido
│   └── engine.py                 Motor descendente con retroceso
├── java_subset/
│   ├── __init__.py
│   ├── lexer.py                  Tokens, línea y columna
│   ├── parser.py                 Parser descendente recursivo LL(1) y recuperación
│   ├── ll1.py                    FIRST, FOLLOW, tabla LL(1) y conflictos
│   └── engine_adapter.py         Gramática BNF de Java en el motor genérico
├── spanish/
│   ├── __init__.py
│   ├── grammar_es.py             CFG del español y léxico
│   ├── demo_es.py                Oraciones y experimento aⁿbⁿcⁿ
│   ├── demo_spacy.py             Análisis con spaCy
│   └── conflictos_ll1.py        Conflictos de la gramática
└── tests/
    ├── __init__.py
    ├── test_java_parser.py       8 pruebas
    ├── test_motor_unico.py      4 pruebas
    └── test_espanol.py          2 pruebas
```

### 1.2. Instalación básica (Fase 1)

Desde PowerShell en Windows:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m spacy download es_core_news_sm
python -m pip install matplotlib
```

Si utilizas `cmd.exe`, activa con `.venv\Scripts\activate.bat`. En Linux o macOS, usa `source .venv/bin/activate`.

### 1.3. Comandos de la Fase 1

**Java:**

```powershell
python demo_java.py
python demo_java.py archivo.java
python -m java_subset.ll1
python -m java_subset.ll1 --matriz
```

**Motor genérico y gramática del español:**

```powershell
python demo_unificado.py
python -m spanish.demo_es
python -m spanish.demo_es --arboles
python -m spanish.demo_spacy
python -m spanish.conflictos_ll1
```

**Oraciones propias:**

```powershell
python analizar_es.py
python analizar_es.py "las niñas que leen el libro están cansadas"
python analizar_es.py "el gato duerme"
python analizar_es.py demo/oraciones.txt
python analizar_es.py --todos "el hombre vio el gato con el telescopio"
python analizar_es.py --spacy "el gato duerme"
python analizar_es.py --lexico
```

> Corrección respecto al comando anterior: para ejecutar un módulo se usa `python -m spanish.conflictos_ll1`, **sin** añadir `.py` después del nombre.

**Pruebas de la Fase 1:**

| Comando | Resultado esperado |
|---|---|
| `python -m unittest discover -s tests -v` | 14 pruebas; `OK` |
| `python -m unittest tests.test_java_parser -v` | 8 pruebas; `OK` |
| `python -m unittest tests.test_motor_unico -v` | 4 pruebas; `OK` |
| `python -m unittest tests.test_espanol -v` | 2 pruebas; `OK` |

### 1.4. Oraciones originales del español

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

---

## Fase 2 · Comparación experimental de cuatro enfoques

### 2.1. Objetivo, modelos y criterios

Se evalúan **cuatro enfoques**, pero se producen **cinco logs**, porque Gemini se ejecuta en dos condiciones experimentales:

| Enfoque / log | Implementación | Qué hace | Salida principal |
|---|---|---|---|
| 1. CFG / `cfg` | `run_cfg.py`, `cfg_core/`, `spanish/grammar_es.py` | Usa el parser genérico con retroceso y la CFG **G2** (27 no terminales, 62 producciones). Acepta si existe al menos una derivación completa. | Decisión, árboles y número de lecturas (máximo 50). |
| 2. spaCy / `spacy` | `run_spacy.py` | Analiza dependencias y morfología con `es_core_news_md`; aplica reglas propias R1 (predicado) y R2 (concordancia). | Decisión, tokens, rasgos y fallos R1/R2. |
| 3. Hugging Face / `hf` | `run_hf.py` | Usa `dccuchile/bert-base-spanish-wwm-cased`, modelo de lenguaje enmascarado; calcula la **pseudolog-verosimilitud media (PLL)** y compara con un umbral calibrado. | Decisión, PLL, tokens y umbral. |
| 4a. Gemini zero-shot / `llm_zero` | `run_llm.py --variante zero` | Recibe las reglas, el léxico y el formato JSON, **sin ejemplos completos clasificados**. | Decisión, árboles, razón y respuesta original. |
| 4b. Gemini few-shot / `llm_few` | `run_llm.py --variante few` | Igual que zero-shot, pero con **seis ejemplos resueltos** ajenos al corpus. | Decisión, árboles, razón y respuesta original. |

**Modelo de Gemini registrado en la ejecución final:** `gemini-3.5-flash-lite`; temperatura `0.0` y `response_mime_type="application/json"`. **Especifica siempre `--modelo`**: el valor por defecto escrito en el script original es distinto (`gemini-3.5-flash`).

La **etiqueta lingüística** (`etiqueta_esperada`) significa que la oración es sintácticamente correcta o incorrecta en español. La **fidelidad a la CFG** es una evaluación separada: una oración puede ser válida en español pero no derivable mediante G2. El prompt de Gemini pide **derivabilidad respecto a G2**, no corrección general del español.

**Corpus definitivo:** 60 oraciones (38 aceptadas y 22 rechazadas): 8 de nivel 1, 22 de nivel 2 y 30 de nivel 3. La versión exploratoria anterior contenía 50 (16/16/18); se redujo el peso de los controles simples y se aumentaron los casos intermedios y complejos para estudiar las limitaciones de cobertura. Los identificadores no son necesariamente consecutivos (por ejemplo, existen S61, S62 y S68).

### 2.2. Carpetas y archivos de la Fase 2

Estructura esperada **junto a los archivos de la Fase 1**, en la raíz del proyecto:

```text
TLP02-2026/
├── README.md                         Esta guía
├── requirements.txt                  Dependencias de Fase 1, si se conservan
├── requirements_reproducibilidad.txt Matplotlib para evaluar desde los logs
├── common.py                         Leer CSV y guardar registros/metadatos
├── run_cfg.py                         Ejecución del parser propio
├── run_spacy.py                       Ejecución de spaCy + reglas R1/R2
├── run_hf.py                          Calibración y ejecución de HF-PLL
├── run_llm.py                         Gemini: zero-shot o few-shot (original)
├── evaluar_fase2_v3.py               Cálculo de métricas y gráficas
├── verificar_reproducibilidad.py     Comprueba corpus/logs/hashes y regenera resultados
├── verificar_fuentes.py              Verifica CFG, prompts y calibración histórica
├── manifiesto_referencia.json        Hashes de referencia de la ejecución congelada
├── test_evaluar_fase2_v3.py          Pruebas del evaluador
├── test_verificar_reproducibilidad.py Pruebas del verificador
├── hf_umbral.json                    Se GENERA al calibrar HF (si se recalibra)
├── cfg_core/                          Motor común (heredado de Fase 1)
├── spanish/                           Gramática española G2 y utilidades
├── java_subset/                       Parser de Java, si el repo unifica ambas fases
├── corpus/
│   ├── corpus_tlp02.csv              Primera version
│   ├── corpus_tlp02_v2.csv           Corpus final de 60 oraciones (fuente de evaluación)
│   └── calibracion_hf.csv            Se GENERA durante calibración (20 oraciones)
├── logs/                              Se CREA automáticamente al ejecutar enfoques
│   ├── cfg.jsonl                      60 respuestas de CFG
│   ├── cfg_meta.json                  Metadatos de esa corrida
│   ├── spacy.jsonl
│   ├── spacy_meta.json
│   ├── hf_calibracion.json            20 puntuaciones de calibración
│   ├── hf.jsonl
│   ├── hf_meta.json
│   ├── llm_zero.parcial.jsonl         Caché de progreso; solo si ejecutas Gemini
│   ├── llm_zero.jsonl
│   ├── llm_zero_meta.json
│   ├── llm_few.parcial.jsonl          Caché de progreso; solo si ejecutas Gemini
│   ├── llm_few.jsonl
│   └── llm_few_meta.json
├── prompts/                           Se CREA al ejecutar Gemini
│   ├── zero_shot.txt                 Prompt de sistema completo zero-shot
│   └── few_shot.txt                  Prompt de sistema completo y 6 ejemplos
├── evaluacion/
│   └── resultados/                   Se CREA al ejecutar el evaluador
├── parches_propuestos/
│   └── run_llm_corregido.py          Corrige contador de errores de API
└── anexos/
    └── hf_umbral_RECONSTRUIDO.json   Referencia documental; NO es el original
```

La estructura muestra tanto archivos entregados como otros **generados al ejecutar los comandos**; los archivos opcionales pueden no aparecer en todos los repositorios.

### 2.3. Requisitos e instalación para ejecutar los modelos

Se recomienda **Python 3.11** y trabajar desde **PowerShell** en Windows. En la raíz:

```powershell
# 1) Crear entorno (solo la primera vez)
py -3.11 -m venv .venv

# 2) Activar el entorno (en cada terminal nueva)
.\.venv\Scripts\Activate.ps1

# 3) Actualizar pip
python -m pip install --upgrade pip

# 4) Instalar las librerías usadas en Fase 2
python -m pip install spacy transformers torch google-genai matplotlib

# 5) Descargar el modelo MEDIANO de español de spaCy
python -m spacy download es_core_news_md

# 6) Comprobar la instalación
python -m spacy validate
python -m pip show spacy transformers torch google-genai matplotlib
```

Si también quieres ejecutar la Fase 1 y conservas su archivo de dependencias, instala adicionalmente `python -m pip install -r requirements.txt`. La Fase 1 usaba `es_core_news_sm`; la Fase 2 usa **`es_core_news_md`**, por lo que no son intercambiables para reproducir las decisiones.

| Componente | Versión registrada en los metadatos de la corrida final |
|---|---|
| Python | 3.11.0 |
| spaCy | 3.8.18 |
| `es_core_news_md` | 3.8.0 |
| Transformers | 5.23.0 |
| PyTorch | 2.15.0+cpu |
| SDK `google-genai` | 3.3.0 |
| Matplotlib | 3.10.8 en el entorno de reproducción preparado |

El comando anterior instala versiones compatibles **disponibles en el momento de instalación**, no fija automáticamente las versiones históricas. Para comparar exactamente con la corrida original, revisa las versiones locales y los archivos `logs/*_meta.json`; si cambian el modelo o las librerías, las nuevas inferencias pueden diferir.

**Hugging Face:** `run_hf.py` descarga automáticamente tokenizador y pesos la primera vez que carga `dccuchile/bert-base-spanish-wwm-cased` (requiere Internet); el script usa **CPU**. La corrida original registró `revision: null`. En una revisión posterior de la caché local, `refs/main` apuntaba al hash `c4d86612f51b4f46759c8390d1798c2febe71b93`; también había un snapshot `35695e6a39cb1254b606e9d72d89dd53fb1e384d`. **Esto no demuestra cuál se utilizó originalmente.**

**Advertencia sobre los datos:** `common.py` y los cuatro `run_*.py` originales buscan `corpus/corpus_tlp02_v2.csv`, pero el corpus definitivo del evaluador se llama `corpus/corpus_tlp02.csv`. Antes de lanzar los modelos, crea una copia idéntica:

```powershell
Copy-Item .\corpus\corpus_tlp02.csv .\corpus\corpus_tlp02_v2.csv
```

Hazlo solamente después de asegurarte de que `corpus_tlp02.csv` contiene las **60 oraciones finales**. **No ejecutes una corrida final con el corpus de 50 oraciones.** La copia preserva el original y evita modificar los scripts históricos.

### 2.4. Ejecutar los cuatro enfoques, paso a paso

> **Importante:** si el proyecto ya contiene `logs/` con las evidencias originales, **realiza estas ejecuciones en una copia del proyecto**. `write_run` sobrescribe los archivos `logs/<enfoque>.jsonl` y `logs/<enfoque>_meta.json`. No hace falta reejecutar nada para verificar el informe.

#### Paso A. CFG propia

```powershell
python run_cfg.py
```

Genera `logs/cfg.jsonl` y `logs/cfg_meta.json`. Cada oración incluye el texto tokenizado, decisión, tiempo en milisegundos, número de derivaciones y árboles `[O ...]`; si no hay derivación, guarda un diagnóstico. El motor enumera como máximo **50** árboles por oración.

#### Paso B. spaCy

```powershell
python run_spacy.py --model es_core_news_md
```

Genera `logs/spacy.jsonl` y `logs/spacy_meta.json`. Guarda el análisis de cada token (`texto`, `pos`, `morph`, `dep`, `cabeza`) y los fallos de las reglas **R1/R2**. spaCy no decide por sí solo la gramaticalidad; la clasificación la generan las reglas del script.

#### Paso C. Hugging Face: calibración **antes** del corpus

```powershell
# 1) Calibrar con 20 oraciones distintas del corpus de evaluación
python run_hf.py --modo calibrar

# 2) Analizar las 60 oraciones usando el umbral guardado
python run_hf.py --modo corpus
```

Durante la calibración se generan:

| Archivo | Qué contiene |
|---|---|
| `hf_umbral.json` | Nombre del modelo, umbral PLL, exactitud balanceada de calibración, tamaño y fecha. |
| `logs/hf_calibracion.json` | Las 20 oraciones de calibración con sus etiquetas y puntuaciones PLL. |
| `corpus/calibracion_hf.csv` | Las 20 oraciones y sus etiquetas, en CSV. |

En la **corrida histórica**, el umbral fue **−3.30695**, elegido con 20 casos independientes (10 aceptados y 10 rechazados); la exactitud balanceada en calibración fue **85 %**. No presupongas que recalibrar hoy generará exactamente el mismo número.

Durante el análisis final se generan `logs/hf.jsonl` y `logs/hf_meta.json`. Cada registro contiene `pll_suma`, `pll_media`, umbral, tokens y probabilidades logarítmicas por token; se acepta cuando `pll_media >= umbral`.

> **Importante:** `anexos/hf_umbral_RECONSTRUIDO.json`, si está presente, es una reconstrucción para documentación, **no** el original. Para una ejecución nueva crea `hf_umbral.json` mediante `--modo calibrar` o utiliza un archivo original conservado del mismo modelo y de la corrida que quieras reproducir.

#### Paso D. Gemini: configurar la API Key

Para llamar a Gemini se necesita una **API Key válida** para Google Gemini y conexión a Internet. El código acepta `GEMINI_API_KEY` (o `GOOGLE_API_KEY`). **No guardes la clave en el código, README, capturas ni repositorio.**

**Windows PowerShell** (solo para la sesión actual):

```powershell
$env:GEMINI_API_KEY = "TU_API_KEY_PRIVADA"
python -c "import os; print('API Key configurada:', bool(os.getenv('GEMINI_API_KEY')))"
```

**Windows CMD**, si no usas PowerShell:

```bat
set "GEMINI_API_KEY=TU_API_KEY_PRIVADA"
```

**Linux/macOS:**

```bash
export GEMINI_API_KEY="TU_API_KEY_PRIVADA"
```

Si aparece `Falta la variable de entorno GEMINI_API_KEY`, asegúrate de haber configurado la variable **en la misma terminal** desde donde ejecutarás Python. No imprimas el contenido de la clave para comprobarla.

**Corrección recomendada antes de nuevas llamadas:** el `run_llm.py` histórico puede fallar al procesar el primer error de API porque el contador `seguidos` no se inicializa. Si existe la carpeta `parches_propuestos/`, crea una **copia ejecutable en la raíz**, dejando intacto el original:

```powershell
Copy-Item .\parches_propuestos\run_llm_corregido.py .\run_llm_ejecucion.py
```

Si no tienes ese parche, la corrección mínima es insertar `seguidos = 0` inmediatamente antes del bucle `for row in corpus:` dentro de `main()`.

**Ejecución de las dos condiciones** (usa el script corregido si has creado la copia):

```powershell
# Zero-shot: gramática, léxico, criterio y formato, sin ejemplos completos resueltos
python run_llm_ejecucion.py --variante zero --modelo gemini-3.5-flash-lite --pausa 7

# Few-shot: mismas reglas + seis ejemplos resueltos
python run_llm_ejecucion.py --variante few --modelo gemini-3.5-flash-lite --pausa 7
```

Si no utilizas el parche, sustituye `run_llm_ejecucion.py` por `run_llm.py`, asumiendo el riesgo descrito. `--pausa 7` agrega siete segundos entre llamadas; no evita las restricciones de cuota. Opcionalmente, `--limite 3` procesa solo las tres primeras oraciones **para una prueba en una copia del proyecto**, no para la ejecución definitiva.

Gemini genera:

| Archivo | Contenido |
|---|---|
| `prompts/zero_shot.txt` | Texto exacto de las instrucciones del sistema para zero-shot; incluye las producciones G2 y su léxico. |
| `prompts/few_shot.txt` | El mismo marco de instrucciones y seis ejemplos resueltos. |
| `logs/llm_zero.parcial.jsonl` | Guardado incremental para recuperar una corrida interrumpida. |
| `logs/llm_few.parcial.jsonl` | Guardado incremental de few-shot. |
| `logs/llm_zero.jsonl` y `logs/llm_few.jsonl` | Resultados finales por oración; se escriben al completar cada variante. |
| `logs/llm_zero_meta.json` y `logs/llm_few_meta.json` | Versión del SDK, modelo, temperatura, hashes SHA-256 de prompts, pausa, fecha y número de oraciones. |

Los campos `raw` del log incluyen el **JSON original completo de Gemini** (`respuesta_cruda`), la decisión interpretada, árboles, `razon`, fecha y hora de envío/respuesta, uso de tokens, reintentos, modelo y hash del prompt. La caché `.parcial.jsonl` permite continuar llamadas ya exitosas **si no cambian corpus, modelo ni prompt**. Para una nueva experiencia independiente comienza en una carpeta limpia: no mezcles cachés parciales de corpus o corridas distintas.

La solicitud usa `system_instruction` y `response_mime_type="application/json"`, con temperatura cero. **Ni esa temperatura ni el modo JSON garantizan respuestas iguales o siempre formalmente válidas.** Algunas llamadas pueden fallar por cuota (`429`), y repetir una ejecución consume cuota y potencialmente genera costos según la cuenta.

### 2.5. Orden completo de ejecución

Una vez instaladas las dependencias, creado el alias `corpus_tlp02_v2.csv` y configurada la API Key, el orden de **nuevas corridas** es:

```powershell
python run_cfg.py
python run_spacy.py --model es_core_news_md
python run_hf.py --modo calibrar
python run_hf.py --modo corpus
python run_llm_ejecucion.py --variante zero --modelo gemini-3.5-flash-lite --pausa 7
python run_llm_ejecucion.py --variante few  --modelo gemini-3.5-flash-lite --pausa 7
```

Al terminar, comprueba que existen **cinco logs JSONL completos**, cada uno con 60 registros. En PowerShell:

```powershell
Get-ChildItem .\logs\*.jsonl | Select-Object Name, Length
(Get-Content .\logs\cfg.jsonl).Count
(Get-Content .\logs\spacy.jsonl).Count
(Get-Content .\logs\hf.jsonl).Count
(Get-Content .\logs\llm_zero.jsonl).Count
(Get-Content .\logs\llm_few.jsonl).Count
```

**No confundas** los `.parcial.jsonl` con los cinco logs finales. La comprobación anterior cuenta las líneas del archivo; no sustituye la validación de IDs y contenido del evaluador.

### 2.6. Qué representa cada registro y cada metadato

`*.jsonl` significa **JSON Lines**: una línea JSON independiente por oración. El formato mínimo, compartido por los cinco enfoques, es:

```json
{
  "id": "S01",
  "oracion": "El gato duerme.",
  "decision": "aceptada",
  "timestamp": "FECHA_UTC_DE_LA_EJECUCION",
  "raw": {}
}
```

El ejemplo representa el **esquema**, no una salida literal de los modelos. La clave `raw` tiene contenido diferente según el enfoque:

| Log | Datos específicos de `raw` | Para qué sirven |
|---|---|---|
| `cfg.jsonl` | `tokens`, `n_parses`, `ms`, `estructuras`, posible `diagnostico` | Ver derivaciones, ambigüedad y fallos del parser. |
| `spacy.jsonl` | `tokens` (`texto`, `pos`, `morph`, `dep`, `cabeza`) y `fallos` | Investigar análisis de dependencias y errores de reglas. |
| `hf.jsonl` | `pll_suma`, `pll_media`, `umbral`, `tokens`, `logprob_por_token` | Justificar la decisión del criterio PLL. |
| `llm_zero.jsonl`, `llm_few.jsonl` | `respuesta_cruda`, `razon`, `estructuras`, `modelo`, `prompt_sha256`, `t_envio`, `t_respuesta`, `intentos`, `error`, `uso` | Auditar lo que Gemini respondió y si siguió la CFG. |

Un archivo `*_meta.json` contiene **información general de una corrida**, no respuestas individuales: nombres y versiones de librerías/modelos, parámetros, fecha, número de oraciones y, en Gemini, hash del prompt. `hf_calibracion.json` es especial: contiene los puntajes de las 20 oraciones para elegir el umbral, no uno de los cinco logs del corpus final.

### 2.7. Reproducir los resultados desde los logs (sin API ni descargas)

**Este procedimiento es el recomendado para evaluar el trabajo entregado.** Requiere el corpus final, los cinco logs y el evaluador; no requiere spaCy, PyTorch, Transformers ni Gemini.

```powershell
# Desde la raíz del proyecto y con Python disponible
python -m pip install matplotlib

python evaluar_fase2_v3.py --corpus corpus/corpus_tlp02_v2.csv --log cfg=logs/cfg.jsonl --log spacy=logs/spacy.jsonl --log hf=logs/hf.jsonl --log llm_zero=logs/llm_zero.jsonl --log llm_few=logs/llm_few.jsonl --salida evaluacion/resultados
```

> En PowerShell puedes pegar el comando entero en **una sola línea**. En Windows PowerShell las continuaciones de línea se hacen con acento grave `` ` ``, no con `^` (que corresponde a CMD).

**No altera los logs ni el corpus.** Crea la carpeta `evaluacion/resultados/` (o la indicada mediante `--salida`) y genera:

| Archivo de salida | Qué representa |
|---|---|
| `resumen.csv` | TP, FP, TN, FN, precisión, recall, rechazo correcto, exactitud, F1 e IC Wilson de 95 %. |
| `por_nivel.csv` | Métricas desglosadas por complejidad (niveles 1, 2 y 3). |
| `por_grupo.csv` | Métricas según si la etiqueta lingüística coincide o discrepa de la decisión de la CFG. |
| `fidelidad.csv` | Cuánto coincide cada enfoque con la CFG y qué decide en los casos discriminantes. |
| `mcnemar.csv` | Contrastes exactos de McNemar entre pares de enfoques sobre aciertos de las mismas oraciones. |
| `estructuras.csv` | Totales de árboles completos/parciales, diferencias, problemas de formato y etiquetas no permitidas. |
| `estructuras_detalle.csv` | Comparación caso por caso de árboles obtenidos y esperados. |
| `formatos_llm.csv` | Auditoría del formato JSON y de las etiquetas estructurales de Gemini. |
| `detalle.csv` | Una fila por oración y enfoque: referencia, predicción, clasificación TP/FP/TN/FN, grupo y otros diagnósticos. |
| `errores.csv` | Subconjunto de casos con errores de decisión, estructura o formato para su estudio. |
| `tablas.md` | Seis tablas en Markdown listas para consultar e incorporar al informe. |
| `metricas.png` | Gráfica de precisión, recall y rechazo correcto con intervalos de Wilson. |
| `por_nivel.png` | Gráfica de exactitud por nivel de complejidad. |
| `fidelidad.png` | Gráfica del seguimiento de la CFG en oraciones discriminantes. |

Las gráficas PNG se generan **cuando Matplotlib está instalado**. Para analizar únicamente un subconjunto de enfoques pueden omitirse algunos `--log`, pero la comparación final de Fase 2 utiliza **los cinco**. El evaluador usa `cfg` como referencia de gramática mediante `--referencia cfg` (valor por defecto).

Para elegir otro directorio de salida, modifica solo `--salida`, por ejemplo:

```powershell
python evaluar_fase2_v3.py --corpus corpus/corpus_tlp02.csv --log cfg=logs/cfg.jsonl --log spacy=logs/spacy.jsonl --log hf=logs/hf.jsonl --log llm_zero=logs/llm_zero.jsonl --log llm_few=logs/llm_few.jsonl --salida evaluacion/mi_nueva_evaluacion
```



**Resultados esperados en el paquete original:** 14 pruebas automáticas correctas y mensaje de verificación satisfactoria. `verificar_reproducibilidad.py` genera `evaluacion/resultados_reproducidos/` con los CSV/PNG y `verificacion.json`, y contrasta los SHA-256 con `manifiesto_referencia.json`.

> Si vuelves a generar los logs, cambias un prompt o modificas el corpus, el manifiesto congelado **puede indicar diferencias correctamente**. Eso no significa que el evaluador esté roto, sino que ya no se están comparando los mismos artefactos históricos. No modifiques el manifiesto original para ocultar cambios.

### 2.9. Resultados de referencia y cómo interpretarlos

Los resultados publicados para el **corpus final de 60 oraciones** fueron:

| Enfoque | TP | FP | TN | FN | Exactitud |
|---|---:|---:|---:|---:|---:|
| CFG | 27 | 0 | 22 | 11 | 81.7 % |
| spaCy | 33 | 2 | 20 | 5 | 88.3 % |
| Hugging Face PLL | 29 | 8 | 14 | 9 | 71.7 % |
| Gemini zero-shot | 31 | 0 | 22 | 7 | 88.3 % |
| Gemini few-shot | 31 | 0 | 22 | 7 | 88.3 % |

- Las métricas de clasificación se calculan respecto a `etiqueta_esperada` del corpus.
- La **fidelidad formal** compara decisiones con CFG, especialmente en oraciones correctas del español que G2 no reconoce.
- Los **errores de estructura** se auditan solo cuando existen árboles de referencia comparables; no se equiparan dependencias de spaCy con árboles de constituyentes.
- Los **errores de formato** (JSON inválido) y las **etiquetas no permitidas** se contabilizan por separado. En la ejecución few-shot histórica fueron S05/S27/S62 y S19/S26/S51, respectivamente; son conjuntos distintos.
- Las cifras dependen del corpus diseñado para este experimento; no miden la calidad general de esos modelos en todo el español.

### 2.10. Problemas frecuentes

| Síntoma | Causa probable y solución |
|---|---|
| `FileNotFoundError: corpus/corpus_tlp02_v2.csv` | Falta el alias del corpus. Ejecuta `Copy-Item .\corpus\corpus_tlp02.csv .\corpus\corpus_tlp02_v2.csv`. |
| `ModuleNotFoundError: spacy`, `torch`, `transformers` o `google` | Activa `.venv` y ejecuta `python -m pip install spacy transformers torch google-genai matplotlib`. |
| `OSError: Can't find model 'es_core_news_md'` | Ejecuta `python -m spacy download es_core_news_md`. |
| `Falta hf_umbral.json` | Ejecuta primero `python run_hf.py --modo calibrar` en una copia limpia. |
| `Falta la variable de entorno GEMINI_API_KEY` | Define `$env:GEMINI_API_KEY` en la terminal actual. |
| `UnboundLocalError` relacionado con `seguidos` en Gemini | Usa `parches_propuestos/run_llm_corregido.py` copiado a la raíz como `run_llm_ejecucion.py`. |
| Error `429` / cuota de Gemini | La cuota de la API se agotó. Conserva `.parcial.jsonl`; reanuda **el mismo experimento** cuando dispongas de cuota. |
| El evaluador no encuentra logs completos | Verifica que terminó cada corrida y que existe el archivo `logs/<enfoque>.jsonl`, no solo `.parcial.jsonl`. |
| Las nuevas métricas difieren del informe | Comprueba si cambió el corpus, el modelo, los prompts, el umbral o la versión de librerías. Para reproducir el informe, usa sus **logs congelados**. |
| Fallo de `verificar_reproducibilidad.py` por hashes | Se han modificado artefactos respecto al manifiesto original; compara archivos antes de volver a correr. |

### 2.11. Qué entregar

Para que el trabajo pueda auditarse sin credenciales ni llamadas de pago, se recomienda incluir: código de las dos fases, corpus definitivo y corpus exploratorio identificados, cinco logs completos y metadatos, `hf_calibracion.json`, prompts zero/few, evaluador v3, tablas y gráficas, informe técnico, README y pruebas de reproducibilidad. Mantén fuera de la entrega la API Key, `.venv/`, carpetas de caché y archivos privados.

**Nota de integridad:** el `hf_umbral.json` de una nueva calibración no sustituye retrospectivamente el original perdido; la reconstrucción histórica debe seguir etiquetada como tal. La revisión de Hugging Face recuperada de la caché con posterioridad tampoco demuestra qué snapshot estaba activo durante la corrida inicial.
