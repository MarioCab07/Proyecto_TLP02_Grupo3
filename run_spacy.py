"""Enfoque 2: spaCy + regla de decisión acordada para la Fase 2.

spaCy siempre devuelve un análisis, así que 'aceptada/rechazada' sale de esta REGLA,
fijada antes de correr el corpus y que no se modifica según los resultados:

  aceptada  <=>  se cumple R1 y no hay ningún desacuerdo en R2.

  R1 (verbo raíz): hay exactamente una raíz y es VERB o AUX, o es otro predicado que
      tiene un hijo con dep 'cop' (en el esquema UD, 'El niño es feliz' tiene como raíz
      al adjetivo y 'es' cuelga de él como cópula).
  R2 (concordancia): un desacuerdo es un par de tokens que tienen ambos el rasgo
      (Gender o Number) con valores distintos. Un rasgo ausente en alguno no cuenta.
        - dep 'det' o 'amod' con cabeza NOUN/PROPN: Gender y Number.
        - dep 'nsubj': Number del sujeto vs Number del verbo (la cabeza si es VERB/AUX,
          o el hijo 'cop' de la cabeza).
        - 'nsubj' cuya cabeza es un ADJ con cópula (atributo): Gender y Number del
          adjetivo vs el sujeto.
        - dep 'acl' (relativa) con cabeza NOUN/PROPN: Number del antecedente vs el verbo.
"""
import argparse

import spacy

from common import load_corpus, now_iso, write_run


def feat(tok, name):
    v = tok.morph.get(name)
    return v[0] if v else None


def clash(a, b, names):
    """Lista de desacuerdos de rasgos entre los tokens a y b (solo si ambos tienen el rasgo)."""
    out = []
    for n in names:
        va, vb = feat(a, n), feat(b, n)
        if va and vb and va != vb:
            out.append(f"{a.text}({n}={va}) vs {b.text}({n}={vb})")
    return out


def verb_of(head):
    if head.pos_ in ("VERB", "AUX"):
        return head
    return next((c for c in head.children if c.dep_ == "cop"), None)


def decide(doc):
    roots = [t for t in doc if t.dep_ == "ROOT"]
    r1 = len(roots) == 1 and (roots[0].pos_ in ("VERB", "AUX")
                              or any(c.dep_ == "cop" for c in roots[0].children))
    fallos = [] if r1 else [f"R1: raíces={[t.text for t in roots]}, sin verbo raíz ni cópula"]
    for t in doc:
        h = t.head
        if t.dep_ in ("det", "amod") and h.pos_ in ("NOUN", "PROPN"):
            fallos += [f"R2 {t.dep_}: {c}" for c in clash(t, h, ("Gender", "Number"))]
        elif t.dep_ == "nsubj":
            v = verb_of(h)
            if v is not None and v is not t:
                fallos += [f"R2 nsubj-verbo: {c}" for c in clash(t, v, ("Number",))]
            if h.pos_ == "ADJ" and any(c.dep_ == "cop" for c in h.children):
                fallos += [f"R2 atributo: {c}" for c in clash(t, h, ("Gender", "Number"))]
        elif t.dep_ == "acl" and h.pos_ in ("NOUN", "PROPN"):
            fallos += [f"R2 relativa: {c}" for c in clash(h, t, ("Number",))]
    return not fallos, fallos


def main(model="es_core_news_md", corpus_path="corpus/corpus_tlp02_v2.csv"):
    nlp = spacy.load(model)
    records = []
    for row in load_corpus(corpus_path):
        doc = nlp(row["oracion"])
        ok, fallos = decide(doc)
        records.append({
            "id": row["id"], "oracion": row["oracion"],
            "decision": "aceptada" if ok else "rechazada",
            "timestamp": now_iso(),
            "raw": {"fallos": fallos,
                    "tokens": [{"texto": t.text, "pos": t.pos_, "morph": str(t.morph),
                                "dep": t.dep_, "cabeza": t.head.text} for t in doc]}})
    write_run("spacy", records, {"enfoque": "spaCy + regla de decisión", "spacy": spacy.__version__,
                                 "modelo": nlp.meta["name"], "version_modelo": nlp.meta["version"],
                                 "pipeline": nlp.pipe_names})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="es_core_news_md")
    main(ap.parse_args().model)
