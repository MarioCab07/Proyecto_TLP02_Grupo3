"""Enfoque 3: Hugging Face (modelo de lenguaje enmascarado) con puntuación PLL.

Un modelo enmascarado no acepta ni rechaza oraciones. Regla de decisión (fijada antes
de correr el corpus):

  1. Puntuación = PLL normalizada: se enmascara cada token por turno y se promedia el
     log-probabilidad del token original (Salazar et al., 2020, "Masked Language Model
     Scoring"). Es la media por token, para no penalizar las oraciones largas.
  2. aceptada <=> puntuación >= umbral.
  3. El umbral se calcula UNA VEZ con un conjunto de calibración aparte (20 oraciones
     que no están en el corpus) y se guarda en hf_umbral.json. El corpus no interviene.

Uso (desde la carpeta del proyecto):
  python run_hf.py --modo calibrar     # escribe hf_umbral.json y corpus/calibracion_hf.csv
  python run_hf.py --modo corpus       # corre el corpus con el umbral ya fijado
  Opcional: --modelo xlm-roberta-base  (requiere: pip install sentencepiece)
"""
import argparse
import csv
import json
import statistics
import sys
from pathlib import Path

import torch
import transformers
from transformers import AutoModelForMaskedLM, AutoTokenizer

from common import load_corpus, now_iso, write_run

sys.stdout.reconfigure(encoding="utf-8")

MODELO_POR_DEFECTO = "dccuchile/bert-base-spanish-wwm-cased"
UMBRAL_PATH = Path("hf_umbral.json")

# Conjunto de calibración: léxico y construcciones como las del corpus, pero oraciones distintas.
CALIBRACION = [
    ("El perro duerme.", "aceptada"),
    ("La mujer corre.", "aceptada"),
    ("Los hombres comen la manzana.", "aceptada"),
    ("Las niñas leen un libro.", "aceptada"),
    ("El niño grande canta bien.", "aceptada"),
    ("La gata roja come en la casa.", "aceptada"),
    ("Los gatos pequeños duermen.", "aceptada"),
    ("María dice que el perro corre.", "aceptada"),
    ("El libro de la niña es rojo.", "aceptada"),
    ("Los hombres que corren están cansados.", "aceptada"),
    ("Las perro duermen.", "rechazada"),
    ("El mujer corre.", "rechazada"),
    ("Los hombres come la manzana.", "rechazada"),
    ("Las niñas leen un libros.", "rechazada"),
    ("El niño grande cantan bien.", "rechazada"),
    ("La gata rojo come en la casa.", "rechazada"),
    ("Los gatos pequeños duerme.", "rechazada"),
    ("María dice que el perro corren.", "rechazada"),
    ("El libro de la niña son rojo.", "rechazada"),
    ("Los hombres que corren están cansada.", "rechazada"),
]


def cargar(nombre):
    tok = AutoTokenizer.from_pretrained(nombre)
    mdl = AutoModelForMaskedLM.from_pretrained(nombre).eval()
    return tok, mdl


@torch.no_grad()
def pll(texto, tok, mdl):
    """Devuelve (suma, media, tokens, log-probs por token) de la PLL de `texto`."""
    ids = tok(texto, return_tensors="pt")["input_ids"][0]    # [CLS] ... [SEP]
    n = ids.size(0) - 2
    lote = ids.repeat(n, 1)
    for k in range(n):
        lote[k, k + 1] = tok.mask_token_id                    # un token enmascarado por fila
    logits = mdl(input_ids=lote, attention_mask=torch.ones_like(lote)).logits
    pos = torch.arange(n)
    lp = torch.log_softmax(logits[pos, pos + 1], dim=-1)[pos, ids[1:-1]]
    tokens = tok.convert_ids_to_tokens(ids[1:-1])
    return lp.sum().item(), lp.mean().item(), tokens, [round(x, 4) for x in lp.tolist()]


def elegir_umbral(puntajes, etiquetas):
    """Umbral que maximiza la exactitud balanceada (promedio de recall y rechazo correcto)."""
    pos = [s for s, e in zip(puntajes, etiquetas) if e == "aceptada"]
    neg = [s for s, e in zip(puntajes, etiquetas) if e == "rechazada"]
    vals = sorted(set(puntajes))
    candidatos = [(a + b) / 2 for a, b in zip(vals, vals[1:])]

    def balanceada(t):
        return (sum(s >= t for s in pos) / len(pos) + sum(s < t for s in neg) / len(neg)) / 2

    mejor = max(balanceada(t) for t in candidatos)
    empatados = [t for t in candidatos if balanceada(t) == mejor]
    return statistics.median(empatados), mejor


def calibrar(tok, mdl, modelo):
    en_corpus = {r["oracion"] for r in load_corpus()}
    solapadas = [o for o, _ in CALIBRACION if o in en_corpus]
    if solapadas:
        sys.exit(f"Estas oraciones de calibración están en el corpus: {solapadas}")
    filas = []
    for oracion, etiqueta in CALIBRACION:
        _, media, _, _ = pll(oracion, tok, mdl)
        filas.append({"oracion": oracion, "etiqueta": etiqueta, "pll_media": round(media, 4)})
    umbral, balanceada = elegir_umbral([f["pll_media"] for f in filas], [f["etiqueta"] for f in filas])

    UMBRAL_PATH.write_text(json.dumps({
        "modelo": modelo, "metrica": "PLL media por token", "umbral": umbral,
        "exactitud_balanceada_calibracion": balanceada, "n_calibracion": len(filas),
        "fecha": now_iso()}, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("logs").mkdir(exist_ok=True)
    Path("logs/hf_calibracion.json").write_text(
        json.dumps(filas, ensure_ascii=False, indent=2), encoding="utf-8")
    with open("corpus/calibracion_hf.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["oracion", "etiqueta"])
        w.writerows(CALIBRACION)

    for f in sorted(filas, key=lambda x: x["pll_media"]):
        print(f'{f["pll_media"]:8.3f}  {f["etiqueta"]:9}  {f["oracion"]}')
    print(f"\numbral = {umbral:.4f} | exactitud balanceada en calibración = {balanceada:.2f}")
    print("Guardado en hf_umbral.json. Haz commit ANTES de correr el corpus.")


def correr_corpus(tok, mdl, modelo):
    if not UMBRAL_PATH.exists():
        sys.exit("Falta hf_umbral.json: corre primero --modo calibrar")
    cfg = json.loads(UMBRAL_PATH.read_text(encoding="utf-8"))
    if cfg["modelo"] != modelo:
        sys.exit(f"El umbral se calibró con {cfg['modelo']}, no con {modelo}")
    registros = []
    for row in load_corpus():
        suma, media, tokens, lps = pll(row["oracion"], tok, mdl)
        registros.append({
            "id": row["id"], "oracion": row["oracion"],
            "decision": "aceptada" if media >= cfg["umbral"] else "rechazada",
            "timestamp": now_iso(),
            "raw": {"pll_suma": round(suma, 4), "pll_media": round(media, 4),
                    "umbral": cfg["umbral"], "tokens": tokens, "logprob_por_token": lps}})
    write_run("hf", registros, {
        "enfoque": "Hugging Face: PLL de modelo enmascarado + umbral calibrado aparte",
        "modelo": modelo, "revision": getattr(mdl.config, "_commit_hash", None),
        "transformers": transformers.__version__, "torch": torch.__version__,
        "umbral": cfg["umbral"], "calibracion": {k: cfg[k] for k in ("n_calibracion", "fecha")},
        "dispositivo": "cpu"})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modo", choices=["calibrar", "corpus"], required=True)
    ap.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    a = ap.parse_args()
    tok, mdl = cargar(a.modelo)
    (calibrar if a.modo == "calibrar" else correr_corpus)(tok, mdl, a.modelo)
