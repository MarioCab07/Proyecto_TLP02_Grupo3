#!/usr/bin/env python3
"""Evaluación de la Fase 2 (v3): decisiones y estructuras independientes.

Uso (desde la carpeta del proyecto; se puede pasar cualquier subconjunto de logs):
  python evaluar_fase2_v3.py --corpus corpus/corpus_tlp02.csv ^
      --log cfg=logs/cfg.jsonl --log spacy=logs/spacy.jsonl --log hf=logs/hf.jsonl ^
      --log llm_zero=logs/llm_zero.jsonl --log llm_few=logs/llm_few.jsonl ^
      --salida evaluacion/resultados

Qué calcula (todo determinista: mismos archivos de entrada -> mismas tablas):
  1. Precisión, recall, rechazo correcto y exactitud, con intervalo de confianza 95 % (Wilson).
  2. Matriz de errores: falsos positivos, falsos negativos, sin decisión y errores de etiquetado
     (los errores de estructura y los de formato JSON se contabilizan por separado).
  3. Desglose por nivel y por grupo (oraciones donde la CFG coincide / difiere de la etiqueta).
  4. Fidelidad a la gramática: en las oraciones donde la etiqueta esperada y la decisión de la
     CFG discrepan, ¿el enfoque sigue a la gramática o a su conocimiento general del español?
  5. Prueba de McNemar exacta entre pares de enfoques (mismas oraciones, aciertos pareados).
Salidas en --salida: resumen.csv, por_nivel.csv, por_grupo.csv, fidelidad.csv, mcnemar.csv,
estructuras.csv, estructuras_detalle.csv, formatos_llm.csv, detalle.csv, errores.csv, tablas.md y, si hay matplotlib, tres gráficas .png.
No modifica el corpus ni los logs.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

POSITIVAS = {"aceptada", "aceptado", "acepta", "si", "true", "1", "gramatical"}
NEGATIVAS = {"rechazada", "rechazado", "rechaza", "no", "false", "0", "agramatical"}
CLAVES_LOG = ("records", "registros", "resultados", "results", "predicciones", "data", "items", "log")


# ----------------------------------------------------------------------------- lectura
def sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def decision(valor):
    """True (aceptada), False (rechazada) o None si no hay decisión utilizable (p. ej. 'sin_decision')."""
    if isinstance(valor, bool):
        return valor
    s = sin_acentos(str(valor).strip().casefold())
    if s in POSITIVAS:
        return True
    if s in NEGATIVAS:
        return False
    return None


def leer(path: Path) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"No se pudo leer {path}")


def cargar_csv(path: Path) -> list[dict]:
    txt = leer(path)
    primera = txt.splitlines()[0] if txt else ""
    delim = ";" if primera.count(";") > primera.count(",") else ","
    filas = list(csv.DictReader(txt.splitlines(), delimiter=delim))
    if not filas:
        raise ValueError(f"CSV vacío: {path}")
    return filas


def cargar_log(path: Path) -> list[dict]:
    txt = leer(path)
    if path.suffix.lower() in (".jsonl", ".ndjson"):
        filas = [json.loads(linea) for linea in txt.splitlines() if linea.strip()]
    else:
        filas = json.loads(txt)
        if isinstance(filas, dict):
            for k in CLAVES_LOG:
                if isinstance(filas.get(k), list):
                    filas = filas[k]
                    break
    if not isinstance(filas, list) or not all(isinstance(f, dict) for f in filas):
        raise ValueError(f"Formato de log no reconocido en {path}")
    return filas


def indexar(filas: list[dict], donde: str) -> dict[str, dict]:
    out = {}
    for n, f in enumerate(filas, 1):
        i = str(f.get("id", "")).strip()
        if not i:
            raise ValueError(f"Falta id en el registro {n} de {donde}")
        if i in out:
            raise ValueError(f"ID duplicado {i!r} en {donde}")
        out[i] = f
    return out


# ------------------------------------------------------------------------- estructuras
# Se compara la forma del árbol (etiquetas, palabras, jerarquía), no su estética.
# ÚNICAS normalizaciones: espacios, mayúsculas y corchetes Unicode escapados.
# No se cambian palabras, etiquetas ni la ubicación de los adjuntos.
class ArbolInvalido(ValueError):
    pass


def normalizar_corchetes_unicode(s: str) -> str:
    """Interpreta escapes Unicode literales que algunos LLM dejan en el árbol.

    El JSON ya se decodificó: aquí solo convertimos secuencias de escape Unicode,
    sin eliminar acentos ni alterar las etiquetas/posiciones del árbol.
    """
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), s)


def canon_arbol(s: str) -> str:
    """Valida corchetes equilibrados y devuelve árbol canónico, o lanza ArbolInvalido."""
    tokens = re.findall(r"\[|\]|[^\s\[\]]+", normalizar_corchetes_unicode(str(s)).strip())
    if not tokens:
        raise ArbolInvalido("Árbol vacío")
    pos = 0

    def leer_nodo():
        nonlocal pos
        if pos >= len(tokens):
            raise ArbolInvalido("Nodo incompleto")
        if tokens[pos] == "]":
            raise ArbolInvalido("Cierre inesperado")
        if tokens[pos] != "[":
            val = tokens[pos].casefold()
            pos += 1
            return val
        pos += 1
        if pos >= len(tokens) or tokens[pos] in ("[", "]"):
            raise ArbolInvalido("Falta etiqueta del nodo")
        etiqueta = tokens[pos].casefold()
        pos += 1
        hijos = []
        while pos < len(tokens) and tokens[pos] != "]":
            hijos.append(leer_nodo())
        if pos >= len(tokens):
            raise ArbolInvalido("Falta cerrar un nodo")
        pos += 1
        if not hijos:
            raise ArbolInvalido("Nodo sin contenido")
        return "[" + etiqueta + " " + " ".join(hijos) + "]"

    if tokens[0] != "[":
        raise ArbolInvalido("La estructura debe comenzar con [")
    resultado = leer_nodo()
    if pos != len(tokens):
        raise ArbolInvalido("Contenido adicional tras el árbol")
    return resultado


def convertir_arboles(valor) -> tuple[set[str], list[str], int]:
    if valor is None:
        valor = []
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, list):
        return set(), ["El campo estructuras no es una lista"], 0
    canonicos, problemas = [], []
    for n, v in enumerate(valor, 1):
        if not isinstance(v, str):
            problemas.append(f"Estructura {n}: no es una cadena")
            continue
        try:
            canonicos.append(canon_arbol(v))
        except ArbolInvalido as e:
            problemas.append(f"Estructura {n}: {e}")
    return set(canonicos), problemas, len(canonicos) - len(set(canonicos))


def estructuras_esperadas(texto) -> set[str]:
    arboles = [p.strip() for p in str(texto or "").split("||") if p.strip()]
    normalizados, errores, duplicados = convertir_arboles(arboles)
    if errores or duplicados:
        raise ValueError(f"Error en las estructuras esperadas del corpus: {errores}; duplicados={duplicados}")
    return normalizados


def leer_estructura_log(reg: dict, es_llm: bool) -> dict:
    """Analiza el JSON original sin modificarlo, conservando fallos de formato.

    En JSON defectuoso se recupera el primer objeto solo para auditoría: no
    se califica como un JSON válido ni como estructura correctamente entregada.
    """
    raw = reg.get("raw") if isinstance(reg.get("raw"), dict) else {}
    almacenadas = raw.get("estructuras", reg.get("estructuras", []))
    info = {"formato": "no_aplica", "arboles": set(), "errores_arbol": [],
            "duplicados": 0, "recuperados": set(), "error_formato": "",
            "observacion_formato": "", "fuente": "raw.estructuras"}
    if es_llm:
        texto = raw.get("respuesta_cruda")
        if not isinstance(texto, str) or not texto.strip():
            info["formato"] = "sin_respuesta_cruda"
            info["error_formato"] = "Ausente respuesta original"
            return info
        texto = texto.strip()
        if texto.startswith("```"):
            # La consigna prohíbe los fences, aunque podamos inspeccionarlos.
            info["formato"] = "json_invalido"
            info["error_formato"] = "Respuesta envuelta en bloque de código"
            texto = re.sub(r"^```(?:json)?\s*", "", texto, flags=re.I)
            texto = re.sub(r"\s*```$", "", texto)
        try:
            data = json.loads(texto)
        except (ValueError, TypeError) as e:
            info["formato"] = "json_invalido"
            info["error_formato"] = str(e)
            try:
                # Ejemplo real: {...}, "razon": ... (objeto seguido de datos)
                data, final = json.JSONDecoder().raw_decode(texto)
                info["observacion_formato"] = "Objeto inicial legible; hay contenido adicional" if texto[final:].strip() else ""
            except ValueError:
                return info
        if not isinstance(data, dict):
            info["formato"] = "json_invalido"
            info["error_formato"] = "La respuesta JSON no es un objeto"
            return info
        if (str(data.get("decision", "")).upper() not in {"ACEPTADA", "RECHAZADA"}
                or not isinstance(data.get("estructuras"), list)
                or any(not isinstance(x, str) for x in data["estructuras"])
                or not isinstance(data.get("razon"), str)):
            info["formato"] = "json_invalido"
            info["error_formato"] = "La respuesta no cumple el esquema de decisión, estructuras y razón"
        elif info["formato"] != "json_invalido":
            info["formato"] = "json_valido"
        info["fuente"] = "respuesta_cruda"
        info["recuperados"], info["errores_arbol"], info["duplicados"] = convertir_arboles(data.get("estructuras", []))
        if info["formato"] == "json_valido":
            info["arboles"] = info["recuperados"]
        return info
    info["arboles"], info["errores_arbol"], info["duplicados"] = convertir_arboles(almacenadas)
    return info


ETIQUETAS_PERMITIDAS_LLM = {"o", "sn", "sv", "sp", "rel", "comp", "atr", "adv"}


def etiquetas_fuera_esquema(arboles: set[str]) -> list[str]:
    """Incumplimientos de las etiquetas exigidas al LLM (no equivale a etiquetado POS)."""
    usadas = {etiqueta for arbol in arboles for etiqueta in re.findall(r"\[([^\s\[\]]+)", arbol)}
    return sorted(usadas - ETIQUETAS_PERMITIDAS_LLM)


def estado_estructura(esperadas: set[str], info: dict) -> tuple[str, set[str], set[str], set[str]]:
    if info["formato"] in {"json_invalido", "sin_respuesta_cruda"}:
        return "formato_invalido", set(), set(), set()
    pred = info["arboles"]
    comunes, faltantes, adicionales = esperadas & pred, esperadas - pred, pred - esperadas
    if info["errores_arbol"]:
        return "arbol_invalido", comunes, faltantes, adicionales
    if not pred:
        return "sin_estructura", comunes, faltantes, adicionales
    if not faltantes and not adicionales:
        return "completo", comunes, faltantes, adicionales
    if comunes and faltantes and not adicionales:
        return "parcial", comunes, faltantes, adicionales
    if not faltantes and adicionales:
        return "lecturas_extra", comunes, faltantes, adicionales
    if comunes:
        return "mixto", comunes, faltantes, adicionales
    return "diferente", comunes, faltantes, adicionales


# ----------------------------------------------------------------------------- métricas
def wilson(k: int, n: int, z: float = 1.96):
    p = k / n
    d = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / d
    mitad = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centro - mitad), min(1.0, centro + mitad)


def con_ic(d: dict, nombre: str, k: int, n: int):
    if n:
        lo, hi = wilson(k, n)
        d[f"{nombre}_pct"], d[f"{nombre}_ic95_lo"], d[f"{nombre}_ic95_hi"] = (
            round(100 * k / n, 1), round(100 * lo, 1), round(100 * hi, 1))
    else:
        d[f"{nombre}_pct"] = d[f"{nombre}_ic95_lo"] = d[f"{nombre}_ic95_hi"] = ""


def conteo(ids, pred: dict, gold: dict) -> Counter:
    c = Counter()
    for i in ids:
        p = pred[i]
        if p is None:
            c["SD"] += 1
        else:
            c["TP" if gold[i] and p else "FN" if gold[i] else "FP" if p else "TN"] += 1
    return c


def fila_metricas(etiquetas: dict, c: Counter) -> dict:
    tp, fp, tn, fn = (c[k] for k in ("TP", "FP", "TN", "FN"))
    d = dict(etiquetas)
    d.update({"n": tp + fp + tn + fn + c["SD"], "sin_decision": c["SD"], "TP": tp, "FP": fp, "TN": tn, "FN": fn})
    con_ic(d, "precision", tp, tp + fp)
    con_ic(d, "recall", tp, tp + fn)
    con_ic(d, "rechazo_correcto", tn, tn + fp)
    con_ic(d, "exactitud", tp + tn, tp + tn + fp + fn)
    d["f1_pct"] = round(100 * 2 * tp / (2 * tp + fp + fn), 1) if (2 * tp + fp + fn) else ""
    return d


def mcnemar_exacto(b: int, c: int) -> float:
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def celda(d: dict, nombre: str) -> str:
    if d.get(f"{nombre}_pct", "") == "":
        return "—"
    return f"{d[f'{nombre}_pct']} [{d[f'{nombre}_ic95_lo']}–{d[f'{nombre}_ic95_hi']}]"


# ------------------------------------------------------------------------------ salida
def escribir_csv(path: Path, filas: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not filas:
        path.write_text("", encoding="utf-8")
        return
    columnas = list(filas[0])
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)


def tabla_md(titulo: str, cabeceras: list[str], filas: list[list]) -> str:
    out = [f"**{titulo}**", "", "| " + " | ".join(cabeceras) + " |", "|" + "---|" * len(cabeceras)]
    out += ["| " + " | ".join(str(x) for x in f) + " |" for f in filas]
    return "\n".join(out) + "\n"


def graficas(salida: Path, nombres, resumen, por_nivel, fidelidad):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("AVISO: matplotlib no está instalado; no se generaron gráficas (python -m pip install matplotlib).")
        return
    num = lambda v, defecto=0.0: float(v) if v != "" else defecto

    fig, ax = plt.subplots(figsize=(max(8, 1.9 * len(nombres)), 5))
    ancho = 0.26
    for j, (k, etq) in enumerate((("precision", "Precisión"), ("recall", "Recall"), ("rechazo_correcto", "Rechazo correcto"))):
        vals = [num(r[f"{k}_pct"]) for r in resumen]
        err_lo = [max(0.0, v - num(r[f"{k}_ic95_lo"], v)) for v, r in zip(vals, resumen)]
        err_hi = [max(0.0, num(r[f"{k}_ic95_hi"], v) - v) for v, r in zip(vals, resumen)]
        ax.bar([i + (j - 1) * ancho for i in range(len(nombres))], vals, ancho, yerr=[err_lo, err_hi],
               capsize=3, label=etq)
    ax.set_xticks(range(len(nombres)))
    ax.set_xticklabels(nombres)
    ax.set_ylim(0, 108)
    ax.set_ylabel("%  (barras: IC 95 %)")
    ax.set_title("Fase 2: métricas por enfoque")
    ax.legend(loc="lower right")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(salida / "metricas.png", dpi=180)
    plt.close(fig)

    niveles = sorted({r["nivel"] for r in por_nivel})
    fig, ax = plt.subplots(figsize=(8, 5))
    ancho = 0.8 / max(1, len(nombres))
    for j, n in enumerate(nombres):
        vals = [num(next((r["exactitud_pct"] for r in por_nivel if r["enfoque"] == n and r["nivel"] == nv), "")) for nv in niveles]
        ax.bar([i + (j - (len(nombres) - 1) / 2) * ancho for i in range(len(niveles))], vals, ancho, label=n)
    ax.set_xticks(range(len(niveles)))
    ax.set_xticklabels([f"Nivel {nv}" for nv in niveles])
    ax.set_ylim(0, 108)
    ax.set_ylabel("Exactitud (%)")
    ax.set_title("Exactitud por nivel de complejidad")
    ax.legend()
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(salida / "por_nivel.png", dpi=180)
    plt.close(fig)

    if fidelidad:
        fig, ax = plt.subplots(figsize=(max(6, 1.6 * len(fidelidad)), 4.5))
        ax.bar([f["enfoque"] for f in fidelidad], [num(f["sigue_gramatica_pct"]) for f in fidelidad])
        ax.set_ylim(0, 108)
        ax.set_ylabel("% que sigue a la gramática")
        ax.set_title("Oraciones donde la gramática y el español difieren:\n¿a quién obedece el enfoque?")
        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()
        fig.savefig(salida / "fidelidad.png", dpi=180)
        plt.close(fig)


# -------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--corpus", required=True, type=Path)
    ap.add_argument("--log", action="append", required=True, metavar="NOMBRE=RUTA")
    ap.add_argument("--referencia", default="cfg", help="nombre del log que actúa como gramática de referencia")
    ap.add_argument("--gold-col", default="etiqueta_esperada")
    ap.add_argument("--salida", type=Path, default=Path("evaluacion/resultados"))
    a = ap.parse_args()

    specs = []
    for item in a.log:
        if "=" not in item:
            ap.error(f"--log requiere NOMBRE=RUTA, recibido: {item}")
        nombre, ruta = item.split("=", 1)
        if any(nombre.strip() == s[0] for s in specs):
            ap.error(f"Nombre de log duplicado: {nombre}")
        specs.append((nombre.strip(), Path(ruta.strip())))

    # --- corpus: verificar estructura y número de lecturas antes de evaluar
    filas = cargar_csv(a.corpus)
    for col in ("id", "oracion", a.gold_col, "estructura_esperada", "n_lecturas_esperadas"):
        if col not in filas[0]:
            sys.exit(f"ERROR: el corpus no tiene la columna '{col}'. Columnas: {list(filas[0])}")
    corpus = {}
    for f in filas:
        i = f["id"].strip()
        if not i or i in corpus:
            sys.exit(f"ERROR: ID vacío o duplicado en el corpus: {i!r}")
        g = decision(f[a.gold_col])
        if g is None:
            sys.exit(f"ERROR: etiqueta no reconocida {f[a.gold_col]!r} en {i}")
        esperado = estructuras_esperadas(f.get("estructura_esperada"))
        try:
            numero = int(f["n_lecturas_esperadas"])
        except (ValueError, TypeError):
            sys.exit(f"ERROR: n_lecturas_esperadas inválido en {i}")
        if numero != len(esperado) or (not g and numero != 0):
            sys.exit(f"ERROR: {i} declara {numero} lecturas pero tiene {len(esperado)} árboles únicos")
        corpus[i] = {"oracion": f["oracion"], "nivel": (f.get("nivel") or "?").strip(), "gold": g,
                     "est": esperado, "lecturas": numero, "hip": decision(f.get("hipotesis_cfg", ""))}
    ids = sorted(corpus)
    gold = {i: corpus[i]["gold"] for i in ids}

    # --- logs: validación de ID y texto, sin modificar las respuestas originales
    nombres, preds, reg_por_enfoque, estructurales = [], {}, {}, {}
    for nombre, ruta in specs:
        reg = indexar(cargar_log(ruta), f"{nombre} ({ruta})")
        faltan, sobran = sorted(set(corpus) - set(reg)), sorted(set(reg) - set(corpus))
        if faltan or sobran:
            sys.exit(f"ERROR: el log {nombre} no coincide con el corpus (faltan {faltan[:6]}, sobran {sobran[:6]}).")
        for i in ids:
            if "oracion" in reg[i] and str(reg[i]["oracion"]).strip() != corpus[i]["oracion"].strip():
                sys.exit(f"ERROR: la oración de {i} en {nombre} no coincide con el corpus.")
        nombres.append(nombre)
        preds[nombre] = {i: decision(reg[i].get("decision")) for i in ids}
        reg_por_enfoque[nombre] = reg
        # El BERT-PLL y spaCy no generan árboles de constituyentes equivalentes.
        # Su evaluación de clasificación sigue igual; la estructural es n/a.
        if nombre == "cfg" or nombre.startswith("llm_"):
            estructurales[nombre] = {i: leer_estructura_log(reg[i], nombre.startswith("llm_")) for i in ids}

    # --- gramática de referencia y grupos
    if a.referencia in preds:
        ref = dict(preds[a.referencia])
        fuente_ref = f"decisión del log '{a.referencia}'"
    else:
        ref = {i: corpus[i]["hip"] for i in ids}
        fuente_ref = "columna hipotesis_cfg del corpus"
    grupo = {i: ("sin_referencia" if ref[i] is None else
                 "CFG_coincide_con_etiqueta" if ref[i] == gold[i] else "CFG_difiere_de_etiqueta") for i in ids}

    # --- resumen
    resumen = [fila_metricas({"enfoque": n}, conteo(ids, preds[n], gold)) for n in nombres]
    niveles = sorted({corpus[i]["nivel"] for i in ids})
    por_nivel = [fila_metricas({"enfoque": n, "nivel": nv}, conteo([i for i in ids if corpus[i]["nivel"] == nv], preds[n], gold))
                 for nv in niveles for n in nombres]
    grupos = sorted(set(grupo.values()))
    por_grupo = [fila_metricas({"enfoque": n, "grupo": g}, conteo([i for i in ids if grupo[i] == g], preds[n], gold))
                 for g in grupos for n in nombres]

    # --- fidelidad a la gramática
    discrepantes = [i for i in ids if grupo[i] == "CFG_difiere_de_etiqueta"]
    fidelidad = []
    for n in nombres:
        if n == a.referencia:
            continue
        validos = [i for i in ids if preds[n][i] is not None and ref[i] is not None]
        acuerdo = sum(preds[n][i] == ref[i] for i in validos)
        dis = [i for i in discrepantes if preds[n][i] is not None]
        sigue = sum(preds[n][i] == ref[i] for i in dis)
        fila = {"enfoque": n, "n_comparadas": len(validos), "acuerdo_con_referencia_pct": round(100 * acuerdo / len(validos), 1) if validos else "",
                "n_discrepantes": len(dis), "sigue_gramatica": sigue, "sigue_etiqueta": len(dis) - sigue}
        fila["sigue_gramatica_pct"] = round(100 * sigue / len(dis), 1) if dis else ""
        fidelidad.append(fila)

    # --- McNemar entre pares (aciertos pareados)
    mcn = []
    for x in range(len(nombres)):
        for y in range(x + 1, len(nombres)):
            A, B = nombres[x], nombres[y]
            ok = lambda n, i: preds[n][i] == gold[i]
            comunes = [i for i in ids if preds[A][i] is not None and preds[B][i] is not None]
            b = sum(ok(A, i) and not ok(B, i) for i in comunes)
            c = sum(ok(B, i) and not ok(A, i) for i in comunes)
            mcn.append({"enfoque_A": A, "enfoque_B": B, "n_comunes": len(comunes), "A_acierta_B_falla": b,
                        "B_acierta_A_falla": c, "p_mcnemar_exacto": round(mcnemar_exacto(b, c), 4)})

    # --- evaluación estructural, independiente del veredicto binario y del formato
    estados, est_resumen, est_detalle, formatos = {}, [], [], []
    for n in nombres:
        cnt = Counter()
        n_etiquetas_fuera = 0
        es_comparable = n in estructurales
        for i in ids:
            if not es_comparable:
                continue
            info = estructurales[n][i]
            valido = (preds[n][i] is True and gold[i] and bool(corpus[i]["est"]))
            estado, comunes, faltantes, adicionales = (estado_estructura(corpus[i]["est"], info)
                                                      if valido else ("no_evaluable", set(), set(), set()))
            estados[(n, i)] = estado
            # Se detecta el error de formato incluso en oraciones rechazadas.
            if n.startswith("llm_"):
                formatos.append({"enfoque": n, "id": i, "nivel": corpus[i]["nivel"],
                                 "decision": reg_por_enfoque[n][i].get("decision"),
                                 "estado_formato": info["formato"], "descripcion": info["error_formato"],
                                 "arboles_recuperables": len(info["recuperados"]),
                                 "coincidencia_recuperada": ("si" if info["recuperados"] == corpus[i]["est"]
                                                             else "no") if info["formato"] == "json_invalido" and valido else "no_aplica"})
            if valido:
                cnt[estado] += 1
                fuera = etiquetas_fuera_esquema(info["arboles"]) if n.startswith("llm_") else []
                if fuera:
                    n_etiquetas_fuera += 1
                est_detalle.append({
                    "enfoque": n, "id": i, "nivel": corpus[i]["nivel"], "oracion": corpus[i]["oracion"],
                    "estado": estado, "formato": info["formato"],
                    "etiquetas_no_permitidas": "; ".join(fuera),
                    "n_lecturas_esperadas": corpus[i]["lecturas"], "n_lecturas_generadas": len(info["arboles"]),
                    "n_lecturas_coincidentes": len(comunes), "n_lecturas_faltantes": len(faltantes),
                    "n_lecturas_adicionales": len(adicionales), "duplicados": info["duplicados"],
                    "esperadas": " || ".join(sorted(corpus[i]["est"])),
                    "predichas": " || ".join(sorted(info["arboles"])),
                    "faltantes": " || ".join(sorted(faltantes)), "adicionales": " || ".join(sorted(adicionales)),
                    "error_arbol": "; ".join(info["errores_arbol"]),
                    "arboles_recuperables_no_calificados": " || ".join(sorted(info["recuperados"]))
                    if info["formato"] == "json_invalido" else "",
                })
        e = {"enfoque": n, "produce_estructura": "si" if es_comparable else "no (no aplica)"}
        if es_comparable:
            e.update({"tp_con_referencia": sum(cnt.values()),
                      "evaluables_formato_y_arbol": sum(v for k, v in cnt.items() if k != "formato_invalido"),
                      "completo": cnt["completo"], "parcial": cnt["parcial"],
                      "lecturas_extra": cnt["lecturas_extra"], "mixto": cnt["mixto"],
                      "diferente": cnt["diferente"], "sin_estructura": cnt["sin_estructura"],
                      "arbol_invalido": cnt["arbol_invalido"], "formato_invalido_tp": cnt["formato_invalido"],
                      "errores_estructura": (cnt["parcial"] + cnt["lecturas_extra"] + cnt["mixto"]
                                              + cnt["diferente"] + cnt["sin_estructura"] + cnt["arbol_invalido"]),
                      "errores_formato_total": sum(1 for i in ids if estructurales[n][i]["formato"]
                                                  in ("json_invalido", "sin_respuesta_cruda")),
                      "respuestas_con_etiquetas_no_permitidas": n_etiquetas_fuera})
        else:
            e.update({k: "" for k in ("tp_con_referencia", "evaluables_formato_y_arbol", "completo", "parcial",
                                           "lecturas_extra", "mixto", "diferente", "sin_estructura", "arbol_invalido",
                                           "formato_invalido_tp", "errores_estructura", "errores_formato_total",
                                           "respuestas_con_etiquetas_no_permitidas")})
        est_resumen.append(e)

    # --- detalle: permitir identificar exactamente los errores, sin mezclar formatos
    detalle, errores = [], []
    for n in nombres:
        for i in ids:
            p = preds[n][i]
            clase = "SD" if p is None else "TP" if gold[i] and p else "FN" if gold[i] else "FP" if p else "TN"
            info = estructurales.get(n, {}).get(i, {})
            d = {"enfoque": n, "id": i, "nivel": corpus[i]["nivel"], "oracion": corpus[i]["oracion"],
                 "esperada": "aceptada" if gold[i] else "rechazada",
                 "predicha": "sin_decision" if p is None else "aceptada" if p else "rechazada",
                 "clasificacion": clase, "grupo": grupo[i],
                 "resultado_estructura": estados.get((n, i), "no_aplica"),
                 "resultado_formato": info.get("formato", "no_aplica")}
            detalle.append(d)
            if (clase in ("FP", "FN", "SD") or d["resultado_estructura"] not in ("completo", "no_aplica", "no_evaluable")
                    or d["resultado_formato"] in ("json_invalido", "sin_respuesta_cruda")):
                errores.append(d)

    # --- escribir
    s = a.salida
    escribir_csv(s / "resumen.csv", resumen)
    escribir_csv(s / "por_nivel.csv", por_nivel)
    escribir_csv(s / "por_grupo.csv", por_grupo)
    escribir_csv(s / "fidelidad.csv", fidelidad)
    escribir_csv(s / "mcnemar.csv", mcn)
    escribir_csv(s / "estructuras.csv", est_resumen)
    escribir_csv(s / "estructuras_detalle.csv", est_detalle)
    escribir_csv(s / "formatos_llm.csv", formatos)
    escribir_csv(s / "detalle.csv", detalle)
    escribir_csv(s / "errores.csv", errores)

    md = [f"Corpus: {len(ids)} oraciones ({sum(gold.values())} aceptadas, {len(ids) - sum(gold.values())} rechazadas). "
          f"Referencia de la gramática: {fuente_ref}. Los corchetes son intervalos de confianza 95 % (Wilson).\n",
          tabla_md("Tabla 1. Métricas por enfoque (%)", ["Enfoque", "Precisión", "Recall", "Rechazo correcto", "Exactitud", "F1"],
                   [[r["enfoque"], celda(r, "precision"), celda(r, "recall"), celda(r, "rechazo_correcto"), celda(r, "exactitud"), r["f1_pct"]] for r in resumen]),
          tabla_md("Tabla 2. Clasificación de errores", ["Enfoque", "TP", "FP", "TN", "FN", "Sin decisión", "Errores de estructura"],
                   [[r["enfoque"], r["TP"], r["FP"], r["TN"], r["FN"], r["sin_decision"], e["errores_estructura"] if e["errores_estructura"] != "" else "n/a"]
                    for r, e in zip(resumen, est_resumen)]),
          tabla_md("Tabla 3. Exactitud por nivel (%)", ["Enfoque"] + [f"Nivel {nv}" for nv in niveles],
                   [[n] + [celda(next(r for r in por_nivel if r["enfoque"] == n and r["nivel"] == nv), "exactitud") for nv in niveles] for n in nombres]),
          tabla_md("Tabla 4. Fidelidad a la gramática en oraciones donde la etiqueta y la CFG difieren",
                   ["Enfoque", "Acuerdo con la referencia (%)", "Oraciones discrepantes", "Sigue a la gramática", "Sigue a la etiqueta"],
                   [[f["enfoque"], f["acuerdo_con_referencia_pct"], f["n_discrepantes"], f["sigue_gramatica"], f["sigue_etiqueta"]] for f in fidelidad]),
          tabla_md("Tabla 5. McNemar exacto entre pares (p-valor)", ["A", "B", "A acierta / B falla", "B acierta / A falla", "p"],
                   [[m["enfoque_A"], m["enfoque_B"], m["A_acierta_B_falla"], m["B_acierta_A_falla"], m["p_mcnemar_exacto"]] for m in mcn]),
          tabla_md("Tabla 6. Estructuras (verdaderos positivos con árbol de referencia)",
                   ["Enfoque", "TP con árbol", "Completos", "Parciales", "Otras diferencias", "Errores estructura", "Errores formato", "Etiquetas no permitidas"],
                   [[e["enfoque"], e["tp_con_referencia"], e["completo"], e["parcial"],
                     "n/a" if e["completo"] == "" else e["lecturas_extra"] + e["mixto"] + e["diferente"] + e["sin_estructura"] + e["arbol_invalido"],
                     e["errores_estructura"], e["errores_formato_total"], e["respuestas_con_etiquetas_no_permitidas"]] for e in est_resumen])]
    (s / "tablas.md").write_text("\n".join(md), encoding="utf-8")
    graficas(s, nombres, resumen, por_nivel, fidelidad)

    print("\n".join(md))
    sd = {r["enfoque"]: r["sin_decision"] for r in resumen if r["sin_decision"]}
    if sd:
        print(f"AVISO: hay oraciones sin decisión utilizable (excluidas de las métricas): {sd}")
    print(f"Archivos guardados en: {s.resolve()}")


if __name__ == "__main__":
    main()