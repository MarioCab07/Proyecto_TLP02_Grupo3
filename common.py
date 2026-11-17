"""Utilidades compartidas: carga del corpus y escritura de logs en formato uniforme.

Cada enfoque escribe logs/<enfoque>.jsonl (una línea JSON por oración) y
logs/<enfoque>_meta.json (versiones, parámetros, fecha de la corrida).
Campos mínimos de cada línea: id, oracion, decision ('aceptada'/'rechazada'),
timestamp (UTC, ISO-8601) y raw (salida bruta propia del enfoque).
"""
import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def load_corpus(path="corpus/corpus_tlp02_v2.csv"):
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def write_run(approach, records, meta, out_dir="logs"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / f"{approach}.jsonl", "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    meta = {**meta, "python": sys.version.split()[0], "plataforma": platform.platform(),
            "fecha_corrida": now_iso(), "n_oraciones": len(records)}
    (out / f"{approach}_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{approach}: {len(records)} oraciones -> {out / (approach + '.jsonl')}")
