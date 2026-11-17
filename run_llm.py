"""Enfoque 4: LLM (Gemini) con las reglas de la gramática dentro del prompt.

Dos variantes con la MISMA tarea y el mismo formato de respuesta:
  zero: solo las reglas (gramática, léxico, criterio de decisión y formato).
  few : las mismas instrucciones + 6 ejemplos resueltos (ninguno está en el corpus
        ni en el conjunto de calibración de Hugging Face).

La tarea es decidir si la oración es DERIVABLE con la gramática, no si es buen español.
Así se mide si el modelo respeta las reglas formales o se desvía hacia su conocimiento
general del idioma.

Uso (desde la carpeta del proyecto, con la variable GEMINI_API_KEY definida):
  python run_llm.py --variante zero
  python run_llm.py --variante few
Opciones: --modelo <id>   --pausa <segundos entre llamadas>   --limite <N oraciones, para una prueba>
"""
import argparse
import hashlib
import json
import os
import sys
import time
from importlib.metadata import version
from pathlib import Path

from google import genai
from google.genai import types

from common import load_corpus, now_iso, write_run

# >>> Copia aquí la MISMA línea de importación de RULES y LEXICON que dejaste en run_cfg.py <<<
from spanish.grammar_es import RULES, LEXICON

sys.stdout.reconfigure(encoding="utf-8")

MODELO_POR_DEFECTO = "gemini-3.5-flash"

INTRO = (
    "Eres un analizador sintáctico formal. Tu única tarea es decidir si una oración puede "
    "derivarse con la gramática libre de contexto que se da a continuación. NO se te pide "
    "juzgar si la oración es correcta en español.\n\n"
    "GRAMÁTICA\n"
    "El símbolo inicial es O. Cada línea de PRODUCCIONES tiene la forma \"No terminal -> "
    "alternativas\", separadas por |. \"ε\" es la producción vacía. Cada categoría de la lista "
    "LÉXICO produce exactamente una de las palabras que figuran en su lista. Un símbolo que no "
    "es ni no terminal ni categoría del léxico (por ejemplo, que) es una palabra literal."
)

CRITERIO = (
    "CRITERIO DE DECISIÓN\n"
    "- ACEPTADA: existe al menos una derivación desde O que produce exactamente las palabras "
    "de la oración, en ese orden, usando solo estas producciones y estas palabras.\n"
    "- RECHAZADA: en cualquier otro caso. Esto incluye oraciones que son correctas en español "
    "pero que la gramática no puede derivar, y oraciones con palabras que no están en el léxico. "
    "No uses tu conocimiento del español para completar ni corregir la gramática.\n"
    "- Ignora las mayúsculas y la puntuación final."
)

FORMATO = (
    "FORMATO DE RESPUESTA\n"
    "Responde únicamente con un objeto JSON, sin texto adicional ni bloques de código, con estas claves:\n"
    "{\"decision\": \"ACEPTADA\" o \"RECHAZADA\", \"estructuras\": [lista de cadenas], \"razon\": \"una frase breve\"}\n"
    "\"estructuras\" contiene un árbol de constituyentes entre corchetes por cada derivación "
    "distinta que encuentres (lista vacía si es RECHAZADA). Usa solo estas etiquetas: O, SN, SV, SP, "
    "Rel, Comp, Atr, Adv. El determinante, el sustantivo y el adjetivo van como palabras dentro de su SN. "
    "La cópula con su adjetivo se escribe [SV es [Atr feliz]]; una completiva, [SV dice [Comp que [O ...]]]; "
    "una relativa, [Rel que [SV ...]]. Ejemplo: [O [SN el gato] [SV duerme [Adv bien]]]."
)

EJEMPLOS = [
    ("La gata come la manzana.",
     {"decision": "ACEPTADA", "estructuras": ["[O [SN la gata] [SV come [SN la manzana]]]"],
      "razon": "Sujeto femenino singular, verbo singular y objeto: se deriva desde O."}),
    ("Los niños duermen en el parque.",
     {"decision": "ACEPTADA", "estructuras": ["[O [SN los niños] [SV duermen [SP en [SN el parque]]]]"],
      "razon": "Sujeto plural, verbo plural y un SP después del verbo: se deriva desde O."}),
    ("El niño dice que la gata duerme.",
     {"decision": "ACEPTADA",
      "estructuras": ["[O [SN el niño] [SV dice [Comp que [O [SN la gata] [SV duerme]]]]]"],
      "razon": "Vdec seguido de que y una oración completa: se deriva con la producción de la completiva."}),
    ("La niños duermen.",
     {"decision": "RECHAZADA", "estructuras": [],
      "razon": "Det_fs (la) solo se combina con Nom_fs, y niños es N_mp: ninguna producción los une."}),
    ("Las gatas come.",
     {"decision": "RECHAZADA", "estructuras": [],
      "razon": "Con sujeto plural el predicado exige SV_p, y come es V_s."}),
    ("Ayer el perro durmió.",
     {"decision": "RECHAZADA", "estructuras": [],
      "razon": "Ninguna producción de O empieza con Adv: el adverbio solo aparece después del verbo, aunque la oración sea correcta en español."}),
]


def construir_sistema(variante):
    producciones = "\n".join(f"{nt} -> " + " | ".join(" ".join(p) for p in prods)
                             for nt, prods in RULES.items())
    lexico = "\n".join(f"{cat}: {' '.join(sorted(pal))}" for cat, pal in LEXICON.items())
    partes = [INTRO, "PRODUCCIONES\n" + producciones, "LÉXICO\n" + lexico, CRITERIO, FORMATO]
    if variante == "few":
        ejemplos = "\n\n".join(f"Oración: {o}\nRespuesta: {json.dumps(r, ensure_ascii=False)}"
                               for o, r in EJEMPLOS)
        partes.append("EJEMPLOS\n" + ejemplos)
    return "\n\n".join(partes)


def parsear(texto):
    """Devuelve (decision, estructuras, razon). decision: aceptada / rechazada / sin_decision."""
    if not texto:
        return "sin_decision", [], None
    t = texto.strip()
    if t.startswith("```"):
        t = t.strip("`").strip()
        if t.lower().startswith("json"):
            t = t[4:].strip()
    try:
        d = json.loads(t)
        dec = str(d.get("decision", "")).strip().upper()
        est = d.get("estructuras") or []
        if isinstance(est, str):
            est = [est]
        return {"ACEPTADA": "aceptada", "RECHAZADA": "rechazada"}.get(dec, "sin_decision"), est, d.get("razon")
    except (json.JSONDecodeError, AttributeError):
        up = texto.upper()
        a, r = "ACEPTADA" in up, "RECHAZADA" in up
        return ("aceptada" if a and not r else "rechazada" if r and not a else "sin_decision"), [], None


def llamar(client, modelo, sistema, oracion, reintentos=5):
    """Una llamada con reintentos (cuota, saturación). Devuelve un dict con tiempos y la respuesta cruda."""
    espera = 10
    prompt_usuario = f"Oración: {oracion}"
    for intento in range(1, reintentos + 1):
        t_envio = now_iso()
        try:
            r = client.models.generate_content(
                model=modelo, contents=prompt_usuario,
                config=types.GenerateContentConfig(
                    system_instruction=sistema, temperature=0.0,
                    response_mime_type="application/json"))
            uso = r.usage_metadata.model_dump(mode="json") if r.usage_metadata else None
            return {"prompt_usuario": prompt_usuario, "t_envio": t_envio, "t_respuesta": now_iso(),
                    "respuesta_cruda": r.text,"model_version": getattr(r, "model_version", None), "uso": uso, "intentos": intento, "error": None}
        except Exception as e:                       # noqa: BLE001
            error = f"{type(e).__name__}: {e}"
            print(f"  intento {intento} falló: {error[:200]}")
            if intento == reintentos:
                return {"prompt_usuario": prompt_usuario, "t_envio": t_envio, "t_respuesta": now_iso(),
                        "respuesta_cruda": None, "uso": None, "intentos": intento, "error": error}
            time.sleep(espera)
            espera *= 2


def main(variante, modelo, pausa, limite):
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")):
        sys.exit("Falta la variable de entorno GEMINI_API_KEY (ver los pasos de configuración).")
    sistema = construir_sistema(variante)
    Path("prompts").mkdir(exist_ok=True)
    archivo = Path(f"prompts/{variante}_shot.txt")
    archivo.write_text(sistema, encoding="utf-8")
    sha = hashlib.sha256(sistema.encode("utf-8")).hexdigest()
    client = genai.Client()

    Path("logs").mkdir(exist_ok=True)
    parcial = Path(f"logs/llm_{variante}.parcial.jsonl")      # caché: permite reanudar sin repetir llamadas
    hechos = {}
    if parcial.exists():
        for linea in parcial.read_text(encoding="utf-8").splitlines():
            r = json.loads(linea)
            if r["raw"]["error"] is None and r["raw"]["prompt_sha256"] == sha and r["raw"]["modelo"] == modelo:
                hechos[r["id"]] = r

    corpus = load_corpus()[:limite] if limite else load_corpus()
    registros = []
    for row in corpus:
        if row["id"] in hechos:
            registros.append(hechos[row["id"]])
            continue
        res = llamar(client, modelo, sistema, row["oracion"])
        decision, estructuras, razon = parsear(res["respuesta_cruda"])
        reg = {"id": row["id"], "oracion": row["oracion"], "decision": decision,
               "timestamp": res["t_envio"],
               "raw": {**res, "variante": variante, "modelo": modelo, "prompt_sha256": sha,
                       "estructuras": estructuras, "razon": razon}}
        registros.append(reg)
        with open(parcial, "a", encoding="utf-8") as f:
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
        seguidos = seguidos + 1 if res["error"] else 0
        if seguidos >= 3:
            sys.exit("3 errores seguidos (cuota agotada). Lo hecho quedó guardado; repite el mismo comando más tarde.")
        print(f'{row["id"]}  {decision:12}  {row["oracion"]}')
        time.sleep(pausa)

    write_run(f"llm_{variante}", registros, {
        "enfoque": f"LLM Gemini, {'zero-shot' if variante == 'zero' else 'few-shot'} con las reglas de la gramática",
        "modelo": modelo, "sdk_google_genai": version("google-genai"),
        "temperatura": 0.0, "formato_respuesta": "application/json",
        "prompt_archivo": str(archivo), "prompt_sha256": sha, "pausa_entre_llamadas_s": pausa,
        "nota": "temperatura 0 no garantiza respuestas idénticas entre corridas; el análisis usa estos logs"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante", choices=["zero", "few"], required=True)
    ap.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    ap.add_argument("--pausa", type=float, default=6.0)
    ap.add_argument("--limite", type=int, default=0)
    a = ap.parse_args()
    main(a.variante, a.modelo, a.pausa, a.limite)
