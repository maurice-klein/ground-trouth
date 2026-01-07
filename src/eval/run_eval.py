#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Evaluation Runner for IDP Bachelor Pipeline
-------------------------------------------

Metriken:
- WER (word error rate) pro Seite + overall micro
- Field/Entity F1 (micro) anhand von GT entities.json vs. Prediction fields.json
- Table Exact Match (strict) anhand von GT tilgungsplan.csv vs. Prediction table_*.csv
  + zusätzlich "best-permutation" als Diagnose, falls Spalteninhalte vertauscht benannt wurden

Standard-Pfade (relativ zum Repo-Root):
  data/eval        (Ground Truth)
  data/processed   (Predictions)
Outputs:
  out/reports/eval_summary.json
  out/reports/eval_report.html
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
from rapidfuzz.distance import Levenshtein
from dateutil import parser as dtparser


# -----------------------------
# Helpers
# -----------------------------

def repo_root() -> Path:
    # .../src/eval/run_eval.py -> repo root is 3 levels up
    return Path(__file__).resolve().parents[2]


def norm_id(s: str) -> str:
    return re.sub(r"[\s\-_]+", "_", s.strip().lower())


def is_empty(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if isinstance(v, list) and len(v) == 0:
        return True
    return False


def normalize_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def wer_counts(gt_text: str, pred_text: str) -> Dict[str, Any]:
    gt_words = normalize_text(gt_text).split() if gt_text else []
    pred_words = normalize_text(pred_text).split() if pred_text else []
    ops = Levenshtein.editops(gt_words, pred_words)

    subs = sum(1 for op in ops if op.tag == "replace")
    dels = sum(1 for op in ops if op.tag == "delete")
    ins = sum(1 for op in ops if op.tag == "insert")

    n = len(gt_words)
    wer = (subs + dels + ins) / n if n > 0 else (0.0 if len(pred_words) == 0 else 1.0)

    return {
        "wer": wer,
        "substitutions": subs,
        "deletions": dels,
        "insertions": ins,
        "total_words": n,
        "errors": subs + dels + ins,
    }


def parse_number(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    s = s.replace("€", "").replace("%", "")
    s = re.sub(r"[^\d,.\-]", "", s)

    if "," in s and "." in s:
        # decide by last separator (common EU formatting)
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        if "," in s and "." not in s:
            s = s.replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None


def parse_rate(v: Any) -> Optional[float]:
    # returns percent value
    if v is None:
        return None
    raw = str(v)
    num = parse_number(v)
    if num is None:
        return None
    if "%" in raw:
        return num
    if num <= 1.0:
        return num * 100
    return num


def parse_date(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        dt = dtparser.parse(s, dayfirst=True, yearfirst=False, fuzzy=True)
        return dt.date().isoformat()
    except Exception:
        return None


def extract_iban(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).upper().replace(" ", "")
    s = re.sub(r"IBAN[:\s]*", "", s)
    m = re.search(r"[A-Z]{2}\d{2}[A-Z0-9]{10,30}", s)
    return m.group(0) if m else (s if s else None)


def extract_bic(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).upper().replace(" ", "")
    s = re.sub(r"BIC[:\s]*", "", s)
    m = re.search(r"[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?", s)
    return m.group(0) if m else (s if s else None)


def norm_name(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).lower()
    s = re.sub(r"[^a-zäöüß\s\-]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or None


def parse_eur_amounts(text: str) -> List[float]:
    matches = re.findall(r"(\d[\d\.\,]*)\s*(?:€|eur)", text, flags=re.IGNORECASE)
    nums: List[float] = []
    for m in matches:
        n = parse_number(m)
        if n is not None:
            nums.append(n)
    return nums


def canonical_sicherheit(item: str) -> Optional[Tuple[str, Optional[float]]]:
    s = normalize_text(item)
    if not s:
        return None

    if "grundschuld" in s:
        typ = "grundschuld"
    elif "lebensversicherung" in s or "risikolebensversicherung" in s:
        typ = "lebensversicherung"
    elif "bürgschaft" in s or "buergschaft" in s:
        typ = "buergschaft"
    elif "blankokredit" in s or ("keine" in s and "sicherheit" in s):
        typ = "keine"
    else:
        typ = "sonstiges"

    eur_nums = parse_eur_amounts(item)
    amt = max(eur_nums) if eur_nums else None
    return (typ, round(amt, 2) if amt is not None else None)


def normalize_field_value(field: str, v: Any) -> Any:
    if is_empty(v):
        return None

    if field == "iban":
        return extract_iban(v)
    if field == "bic":
        return extract_bic(v)
    if field == "darlehenssumme":
        n = parse_number(v)
        return None if n is None else round(n, 2)
    if field in ("sollzinssatz", "effektivzinssatz"):
        n = parse_rate(v)
        return None if n is None else round(n, 4)
    if field == "laufzeit":
        if isinstance(v, (int, float)):
            return int(v)
        m = re.search(r"\d+", str(v))
        return int(m.group(0)) if m else None
    if field in ("vertragsbeginn", "vertragsende", "vertragsdatum"):
        return parse_date(v)
    if field in ("darlehensnehmer", "kreditgeber"):
        return norm_name(v)
    if field == "vertragsnummer":
        s = str(v).upper()
        return re.sub(r"\s+", "", s)
    if field == "iban_valid":
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s in ("true", "1", "yes", "ja", "valid", "gültig"):
            return True
        if s in ("false", "0", "no", "nein", "invalid", "ungültig"):
            return False
        return None
    if field == "sicherheiten":
        items = v if isinstance(v, list) else [v]
        can = [canonical_sicherheit(str(it)) for it in items]
        return [c for c in can if c is not None]

    return normalize_text(str(v))


def field_values_match(field: str, gt_v: Any, pred_v: Any) -> bool:
    gt_n = normalize_field_value(field, gt_v)
    pred_n = normalize_field_value(field, pred_v)
    if gt_n is None and pred_n is None:
        return True
    if gt_n is None or pred_n is None:
        return False

    if field in ("darlehenssumme", "sollzinssatz", "effektivzinssatz"):
        if isinstance(gt_n, (int, float)) and isinstance(pred_n, (int, float)):
            tol = 0.01 if field == "darlehenssumme" else 0.05
            return abs(gt_n - pred_n) <= tol

    if field == "sicherheiten":
        return set(gt_n) == set(pred_n)

    return gt_n == pred_n


def norm_colname(c: str) -> str:
    c = str(c).strip().lower()
    c = c.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    c = re.sub(r"[^a-z0-9]+", "", c)
    return c


def norm_cell(val: Any, col_norm: str) -> Any:
    if pd.isna(val):
        return None
    if col_norm == "monat":
        try:
            return int(float(val))
        except Exception:
            m = re.search(r"\d+", str(val))
            return int(m.group(0)) if m else None
    if col_norm == "datum":
        return parse_date(val)
    n = parse_number(val)
    if n is not None:
        return round(n, 2)
    return normalize_text(str(val))


def choose_pred_table(pred_tables_dir: Path) -> Optional[Path]:
    meta_file = pred_tables_dir / "tables_metadata.json"
    if meta_file.exists():
        md = json.loads(meta_file.read_text(encoding="utf-8", errors="ignore"))
        best_file = None
        best_score = -1.0
        for pg in md.get("pages", []):
            for t in pg.get("tables", []):
                score = float(t.get("rows", 0)) * float(t.get("cols", 0))
                score += float(t.get("confidence", 0.0)) / 1000.0
                if score > best_score:
                    best_score = score
                    best_file = t.get("csv_file")
        if best_file:
            p = pred_tables_dir / best_file
            if p.exists():
                return p
    csvs = sorted(pred_tables_dir.glob("*.csv"))
    return csvs[0] if csvs else None


def exact_match_strict(gt_df: pd.DataFrame, pred_df: pd.DataFrame) -> Dict[str, Any]:
    gt_cols_norm = [norm_colname(c) for c in gt_df.columns]
    pred_cols_norm = [norm_colname(c) for c in pred_df.columns]

    # map GT columns to prediction columns by name
    col_map: Dict[int, Optional[int]] = {}
    for gi, gc in enumerate(gt_cols_norm):
        col_map[gi] = pred_cols_norm.index(gc) if gc in pred_cols_norm else None

    # sort by Monat if present
    if "monat" in gt_cols_norm:
        i = gt_cols_norm.index("monat")
        gt_df = gt_df.copy()
        gt_df["_sort"] = gt_df.iloc[:, i].apply(lambda x: norm_cell(x, "monat"))
        gt_df = gt_df.sort_values("_sort").drop(columns=["_sort"])

    if "monat" in pred_cols_norm:
        i = pred_cols_norm.index("monat")
        pred_df = pred_df.copy()
        pred_df["_sort"] = pred_df.iloc[:, i].apply(lambda x: norm_cell(x, "monat"))
        pred_df = pred_df.sort_values("_sort").drop(columns=["_sort"])

    n_rows = min(len(gt_df), len(pred_df))
    gt_df = gt_df.iloc[:n_rows].reset_index(drop=True)
    pred_df = pred_df.iloc[:n_rows].reset_index(drop=True)

    total_cells = n_rows * len(gt_cols_norm)
    correct_cells = 0
    row_correct = 0
    col_correct_counts = [0] * len(gt_cols_norm)

    for r in range(n_rows):
        row_all = True
        for gi, gc in enumerate(gt_cols_norm):
            pi = col_map[gi]
            gt_val = norm_cell(gt_df.iat[r, gi], gc)
            pred_val = norm_cell(pred_df.iat[r, pi], gc) if pi is not None else None
            if gt_val == pred_val:
                correct_cells += 1
                col_correct_counts[gi] += 1
            else:
                row_all = False
        if row_all:
            row_correct += 1

    col_accuracy = {gt_df.columns[i]: (col_correct_counts[i] / n_rows if n_rows else 0.0)
                    for i in range(len(gt_cols_norm))}

    return {
        "exact_match_rate": (correct_cells / total_cells if total_cells else 0.0),
        "total_cells": total_cells,
        "correct_cells": correct_cells,
        "row_accuracy": (row_correct / n_rows if n_rows else 0.0),
        "col_accuracy": col_accuracy,
        "rows_compared": n_rows,
    }


def exact_match_best_permutation(gt_df: pd.DataFrame, pred_df: pd.DataFrame, fixed_cols: Tuple[str, ...] = ("Monat", "Datum")) -> Dict[str, Any]:
    # Best mapping (diagnostics) - brute force, ok for small tables
    gt_cols = list(gt_df.columns)
    pred_cols = list(pred_df.columns)

    def find_idx(cols: List[str], target: str) -> Optional[int]:
        if target in cols:
            return cols.index(target)
        nt = norm_colname(target)
        for i, c in enumerate(cols):
            if norm_colname(c) == nt:
                return i
        return None

    gt_fixed = [find_idx(gt_cols, c) for c in fixed_cols if find_idx(gt_cols, c) is not None]
    pred_fixed = [find_idx(pred_cols, c) for c in fixed_cols if find_idx(pred_cols, c) is not None]

    gt_rem = [i for i in range(len(gt_cols)) if i not in gt_fixed]
    pred_rem = [i for i in range(len(pred_cols)) if i not in pred_fixed]
    if len(gt_rem) != len(pred_rem):
        return exact_match_strict(gt_df, pred_df)

    # sort by Monat if present
    gt_cols_norm = [norm_colname(c) for c in gt_cols]
    pred_cols_norm = [norm_colname(c) for c in pred_cols]

    if find_idx(gt_cols, "Monat") is not None:
        i = find_idx(gt_cols, "Monat")
        gt_df = gt_df.copy()
        gt_df["_sort"] = gt_df.iloc[:, i].apply(lambda x: norm_cell(x, "monat"))
        gt_df = gt_df.sort_values("_sort").drop(columns=["_sort"])
    if find_idx(pred_cols, "Monat") is not None:
        i = find_idx(pred_cols, "Monat")
        pred_df = pred_df.copy()
        pred_df["_sort"] = pred_df.iloc[:, i].apply(lambda x: norm_cell(x, "monat"))
        pred_df = pred_df.sort_values("_sort").drop(columns=["_sort"])

    n_rows = min(len(gt_df), len(pred_df))
    gt_df = gt_df.iloc[:n_rows].reset_index(drop=True)
    pred_df = pred_df.iloc[:n_rows].reset_index(drop=True)

    base_map: Dict[int, int] = {}
    for g, p in zip(gt_fixed, pred_fixed):
        base_map[g] = p

    best_map = dict(base_map)
    best_correct = -1

    def mapping_score(mapping: Dict[int, int]) -> int:
        correct = 0
        for r in range(n_rows):
            for gi, pi in mapping.items():
                coln = gt_cols_norm[gi]
                gv = norm_cell(gt_df.iat[r, gi], coln)
                pv = norm_cell(pred_df.iat[r, pi], coln)
                if gv == pv:
                    correct += 1
        return correct

    import itertools
    for perm in itertools.permutations(pred_rem):
        mapping = dict(base_map)
        for gi, pi in zip(gt_rem, perm):
            mapping[gi] = pi
        c = mapping_score(mapping)
        if c > best_correct:
            best_correct = c
            best_map = mapping

    total_cells = n_rows * len(gt_cols)
    correct_cells = 0
    row_correct = 0
    col_correct = [0] * len(gt_cols)

    for r in range(n_rows):
        row_all = True
        for gi in range(len(gt_cols)):
            pi = best_map.get(gi)
            coln = gt_cols_norm[gi]
            gv = norm_cell(gt_df.iat[r, gi], coln)
            pv = norm_cell(pred_df.iat[r, pi], coln) if pi is not None else None
            if gv == pv:
                correct_cells += 1
                col_correct[gi] += 1
            else:
                row_all = False
        if row_all:
            row_correct += 1

    col_accuracy = {gt_cols[i]: (col_correct[i] / n_rows if n_rows else 0.0)
                    for i in range(len(gt_cols))}
    best_mapping = {gt_cols[gi]: pred_cols[pi] for gi, pi in best_map.items()}

    return {
        "exact_match_rate": (correct_cells / total_cells if total_cells else 0.0),
        "total_cells": total_cells,
        "correct_cells": correct_cells,
        "row_accuracy": (row_correct / n_rows if n_rows else 0.0),
        "col_accuracy": col_accuracy,
        "rows_compared": n_rows,
        "best_mapping": best_mapping,
    }


def load_pred_page_text(pred_doc_dir: Path, page: int) -> str:
    ocr_json = pred_doc_dir / "ocr.json"
    if ocr_json.exists():
        data = json.loads(ocr_json.read_text(encoding="utf-8", errors="ignore"))
        for pg in data.get("pages", []):
            if pg.get("page") == page:
                lines = [ln.get("text", "") for ln in pg.get("lines", [])]
                return "\n".join(lines)

    # fallback: per-page text file
    txt = pred_doc_dir / f"page_{page:03d}_preprocessed_ocr.txt"
    if txt.exists():
        return txt.read_text(encoding="utf-8", errors="ignore")
    return ""


def html_report(
    wer_overall: Dict[str, Any],
    f1_overall: Dict[str, Any],
    tables_overall: Dict[str, Any],
    wer_per_doc: pd.DataFrame,
    f1_per_field: pd.DataFrame,
    tables_per_doc: pd.DataFrame,
) -> str:
    def df_to_html(df: pd.DataFrame) -> str:
        return df.to_html(index=False, escape=True, border=0, classes="tbl")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<title>IDP Evaluation Report</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
h1,h2 {{ margin-bottom: 6px; }}
.small {{ color: #555; }}
.kpi {{ display:flex; gap:16px; flex-wrap:wrap; margin: 12px 0 24px; }}
.card {{ border:1px solid #ddd; border-radius:10px; padding:12px 14px; min-width:220px; }}
.card .value {{ font-size:26px; font-weight:700; }}
.pass {{ color: #0a7; }}
.fail {{ color: #c33; }}
.tbl {{ border-collapse: collapse; width: 100%; margin: 10px 0 24px; }}
.tbl th, .tbl td {{ border: 1px solid #ddd; padding: 6px 8px; font-size: 13px; }}
.tbl th {{ background: #f6f6f6; text-align: left; }}
.note {{ background:#fff7e6; border:1px solid #f0d9a6; padding:10px 12px; border-radius:10px; }}
code {{ background:#f2f2f2; padding:1px 4px; border-radius:4px; }}
</style>
</head>
<body>
<h1>IDP-Pipeline Evaluation</h1>
<div class="small">Generiert am {now}</div>

<div class="kpi">
  <div class="card">
    <div>WER (micro)</div>
    <div class="value {'pass' if wer_overall['wer_micro'] < 0.15 else 'fail'}">{wer_overall['wer_micro']:.2%}</div>
    <div class="small">Ziel: &lt; 15% — Wörter: {wer_overall['total_words']}, Fehler: {wer_overall['errors']}</div>
  </div>
  <div class="card">
    <div>Field/Entity F1 (micro)</div>
    <div class="value {'pass' if f1_overall['f1'] > 0.80 else 'fail'}">{f1_overall['f1']:.3f}</div>
    <div class="small">Ziel: &gt; 0.80 — TP: {f1_overall['tp']}, FP: {f1_overall['fp']}, FN: {f1_overall['fn']}</div>
  </div>
  <div class="card">
    <div>Table Exact Match (strict, micro)</div>
    <div class="value {'pass' if tables_overall['strict_micro'] > 0.70 else 'fail'}">{tables_overall['strict_micro']:.2%}</div>
    <div class="small">Ziel: &gt; 70%</div>
  </div>
  <div class="card">
    <div>Table Exact Match (best-permutation, micro)</div>
    <div class="value">{tables_overall['best_micro']:.2%}</div>
    <div class="small">Diagnose, falls Spalten vertauscht benannt wurden</div>
  </div>
</div>

<div class="note">
<b>Hinweis zu Tabellen:</b> Ein großer Gap zwischen <i>strict</i> und <i>best-permutation</i> deutet häufig auf vertauschte Spaltennamen
(z. B. <code>Zinsen</code> ↔ <code>Tilgung</code>) hin.
</div>

<h2>WER pro Dokument</h2>
{df_to_html(wer_per_doc)}

<h2>Field/Entity F1 pro Feld</h2>
{df_to_html(f1_per_field)}

<h2>Tabellen: Strict vs Best-Permutation pro Dokument</h2>
{df_to_html(tables_per_doc)}

</body></html>
"""


# -----------------------------
# Main evaluation
# -----------------------------

def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--gt", type=str, default=str(repo_root() / "data" / "eval"), help="Ground Truth root (default: data/eval)")
    parser.add_argument("--pred", type=str, default=str(repo_root() / "data" / "processed"), help="Prediction root (default: data/processed)")
    parser.add_argument("--out", type=str, default=str(repo_root() / "out" / "reports"), help="Output dir (default: out/reports)")
    args = parser.parse_args()

    gt_root = Path(args.gt)
    pred_root = Path(args.pred)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Docs
    gt_docs = [p for p in gt_root.iterdir() if p.is_dir() and p.name != "raw"]
    pred_docs = [p for p in pred_root.iterdir() if p.is_dir()]

    gt_map = {norm_id(p.name): p for p in gt_docs}
    pred_map = {norm_id(p.name): p for p in pred_docs}
    common = sorted(set(gt_map.keys()) & set(pred_map.keys()))

    if not common:
        print("ERROR: Keine passenden Dokumente gefunden. Prüfe Pfade --gt und --pred.")
        return 2

    # 1) WER
    wer_rows: List[Dict[str, Any]] = []
    for k in common:
        gt_dir = gt_map[k]
        pred_dir = pred_map[k]
        for pg_file in sorted((gt_dir / "ocr").glob("page_*.txt")):
            m = re.search(r"page_(\d+)\.txt", pg_file.name)
            if not m:
                continue
            page = int(m.group(1))
            gt_text = pg_file.read_text(encoding="utf-8", errors="ignore")
            pred_text = load_pred_page_text(pred_dir, page)
            res = wer_counts(gt_text, pred_text)
            wer_rows.append({"doc": gt_dir.name, "page": page, **res})

    wer_df = pd.DataFrame(wer_rows)
    wer_micro = wer_df["errors"].sum() / max(1, wer_df["total_words"].sum())
    wer_overall = {
        "wer_micro": float(wer_micro),
        "total_words": int(wer_df["total_words"].sum()),
        "errors": int(wer_df["errors"].sum()),
    }
    wer_per_doc = (
        wer_df.assign(wer_micro=lambda d: d["errors"] / d["total_words"])
        .groupby("doc")
        .agg(words=("total_words", "sum"), errors=("errors", "sum"))
        .reset_index()
    )
    wer_per_doc["wer_micro_%"] = (wer_per_doc["errors"] / wer_per_doc["words"] * 100).round(2)
    wer_per_doc = wer_per_doc.sort_values("wer_micro_%", ascending=False)

    # 2) Field/Entity F1
    # Ground Truth: */entities.json
    # Pred: */fields.json
    all_fields: set[str] = set()
    for k in common:
        gt_data = json.loads((gt_map[k] / "entities.json").read_text(encoding="utf-8", errors="ignore"))
        pred_data = json.loads((pred_map[k] / "fields.json").read_text(encoding="utf-8", errors="ignore"))
        all_fields |= set(gt_data.keys()) | set(pred_data.keys())
    all_fields.discard("document")

    stats: Dict[str, Dict[str, int]] = {f: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for f in sorted(all_fields)}

    for k in common:
        gt_data = json.loads((gt_map[k] / "entities.json").read_text(encoding="utf-8", errors="ignore"))
        pred_data = json.loads((pred_map[k] / "fields.json").read_text(encoding="utf-8", errors="ignore"))
        for field in all_fields:
            gt_v = gt_data.get(field)
            pred_v = pred_data.get(field)
            gt_present = not is_empty(gt_v)
            pred_present = not is_empty(pred_v)

            if gt_present:
                stats[field]["support"] += 1

            if gt_present and pred_present:
                if field_values_match(field, gt_v, pred_v):
                    stats[field]["tp"] += 1
                else:
                    stats[field]["fp"] += 1
                    stats[field]["fn"] += 1
            elif gt_present and not pred_present:
                stats[field]["fn"] += 1
            elif pred_present and not gt_present:
                stats[field]["fp"] += 1

    tp_total = sum(v["tp"] for v in stats.values())
    fp_total = sum(v["fp"] for v in stats.values())
    fn_total = sum(v["fn"] for v in stats.values())
    prec = tp_total / (tp_total + fp_total) if (tp_total + fp_total) else 0.0
    rec = tp_total / (tp_total + fn_total) if (tp_total + fn_total) else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0

    f1_overall = {"precision": float(prec), "recall": float(rec), "f1": float(f1), "tp": int(tp_total), "fp": int(fp_total), "fn": int(fn_total)}

    f1_rows = []
    for field, v in stats.items():
        tp, fp, fn = v["tp"], v["fp"], v["fn"]
        p = tp / (tp + fp) if (tp + fp) else 0.0
        r = tp / (tp + fn) if (tp + fn) else 0.0
        f = 2 * p * r / (p + r) if (p + r) else 0.0
        f1_rows.append({"field": field, "support": v["support"], "tp": tp, "fp": fp, "fn": fn,
                        "precision_%": round(p * 100, 1), "recall_%": round(r * 100, 1), "f1_%": round(f * 100, 1)})
    f1_per_field = pd.DataFrame(f1_rows).sort_values("f1_%")

    # 3) Tables exact match (strict + best-permutation diagnostic)
    table_rows = []
    strict_correct = 0
    strict_total = 0
    best_correct = 0
    best_total = 0

    for k in common:
        gt_dir = gt_map[k]
        pred_dir = pred_map[k]
        gt_table = gt_dir / "tables" / "tilgungsplan.csv"
        pred_table = choose_pred_table(pred_dir / "tables")
        if not gt_table.exists() or pred_table is None:
            continue

        gt_df = pd.read_csv(gt_table)
        pred_df = pd.read_csv(pred_table)

        strict = exact_match_strict(gt_df, pred_df)
        best = exact_match_best_permutation(gt_df, pred_df)

        strict_correct += strict["correct_cells"]
        strict_total += strict["total_cells"]
        best_correct += best["correct_cells"]
        best_total += best["total_cells"]

        table_rows.append({
            "doc": gt_dir.name,
            "pred_table": pred_table.name,
            "strict_exact_%": round(strict["exact_match_rate"] * 100, 1),
            "best_exact_%": round(best["exact_match_rate"] * 100, 1),
            "strict_row_%": round(strict["row_accuracy"] * 100, 1),
            "best_row_%": round(best["row_accuracy"] * 100, 1),
        })

    tables_per_doc = pd.DataFrame(table_rows).sort_values("strict_exact_%")

    tables_overall = {
        "strict_micro": float(strict_correct / strict_total) if strict_total else 0.0,
        "best_micro": float(best_correct / best_total) if best_total else 0.0,
    }

    # Outputs
    summary = {
        "generated_at": datetime.now().isoformat(),
        "paths": {"gt_root": str(gt_root), "pred_root": str(pred_root)},
        "wer": wer_overall,
        "fields": f1_overall,
        "tables": tables_overall,
    }
    (out_dir / "eval_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    html = html_report(wer_overall, f1_overall, tables_overall, wer_per_doc, f1_per_field, tables_per_doc)
    (out_dir / "eval_report.html").write_text(html, encoding="utf-8")

    # Terminal summary (ASCII-only)
    print("=" * 80)
    print("EVALUATION SUMMARY")
    print("=" * 80)
    print(f"WER micro:           {wer_overall['wer_micro']:.2%} (target < 15%)")
    print(f"Field/Entity F1:     {f1_overall['f1']:.3f} (target > 0.80)")
    print(f"Table Exact strict:  {tables_overall['strict_micro']:.2%} (target > 70%)")
    print(f"Table Exact (diag):  {tables_overall['best_micro']:.2%} (best-permutation)")
    print("-" * 80)
    print(f"Report:   {out_dir / 'eval_report.html'}")
    print(f"Summary:  {out_dir / 'eval_summary.json'}")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
