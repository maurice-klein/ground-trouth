#!/usr/bin/env python3
"""
Konvertiert Label Studio Export zu dokumentenbasierter Ground Truth Struktur

V7 FIXED: Append statt Replace für Sicherheiten über mehrere Seiten
"""

import json
from pathlib import Path
import re
from datetime import datetime
from typing import Dict, List, Any

def normalize_currency(text: str) -> float:
    """150.000,00 EUR → 150000.00"""
    text = text.replace(".", "").replace(",", ".").replace(" ", "")
    match = re.search(r'([\d.]+)', text)
    return float(match.group(1)) if match else None

def normalize_percentage(text: str) -> float:
    """3,50 % p.a. → 3.50"""
    text = text.replace(",", ".").replace("%", "").strip()
    match = re.search(r'([\d.]+)', text)
    return float(match.group(1)) if match else None

def normalize_date(text: str) -> str:
    """01.02.2024 → 2024-02-01"""
    match = re.match(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', text)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return text

def validate_iban(iban: str) -> bool:
    """Prüfziffer-Validierung nach ISO 7064 Mod 97-10"""
    iban = iban.replace(" ", "").upper()
    
    if len(iban) < 15:
        return False
    
    rearranged = iban[4:] + iban[:4]
    
    numeric = ""
    for char in rearranged:
        if char.isdigit():
            numeric += char
        else:
            numeric += str(ord(char) - ord('A') + 10)
    
    return int(numeric) % 97 == 1

def extract_doc_id(image_path: str) -> str:
    """
    Extrahiert Dokument-ID aus Label Studio Image-Path
    Entfernt Label Studio Hash-Prefix!
    """
    filename = Path(image_path).name
    
    # URL-Encoding rückgängig
    from urllib.parse import unquote
    filename = unquote(filename)
    
    # Hash-Prefix entfernen (8 Hex-Zeichen + Bindestrich)
    hash_pattern = r'^[0-9a-f]{8}-(.+)$'
    match = re.match(hash_pattern, filename)
    if match:
        filename = match.group(1)
    
    # _page_XXX.png entfernen (mit optionalem _preprocessed)
    page_pattern = r'^(.+)_page_\d+.*\.png$'
    match = re.match(page_pattern, filename)
    if match:
        return match.group(1)
    
    parts = filename.split('_page_')
    return parts[0] if parts else "unknown"

def group_sicherheiten_sequential(result_array: List[Dict]) -> List[Dict]:
    """
    Gruppiert Sicherheiten-Felder basierend auf Array-Position
    
    KRITISCH: Label Studio IDs sind NICHT alphabetisch sortierbar!
              Wir müssen die Original-Reihenfolge im result-Array nutzen!
    
    REGEL: Jedes 'sicherheit_typ' startet neuen Block,
           alle nachfolgenden Felder gehören dazu bis zum nächsten 'sicherheit_typ'
    
    Args:
        result_array: Komplettes result-Array aus Label Studio (in Original-Reihenfolge)
    
    Returns:
        Liste von strukturierten Sicherheiten
    """
    # 1. Sammle Sicherheiten-Annotationen MIT Array-Position
    sicherheiten_annotations = []
    
    for index, result in enumerate(result_array):
        if result['type'] != 'rectanglelabels':
            continue
        
        label = result['value']['rectanglelabels'][0]
        
        # Nur Sicherheiten-Felder
        if not (label.startswith('sicherheit_') or label.startswith('grundbuch_') or label == 'versicherungsnummer'):
            continue
        
        # Text aus dem entsprechenden textarea-Eintrag holen
        rid = result['id']
        text = ""
        for r in result_array:
            if r['type'] == 'textarea' and r['id'] == rid:
                text_value = r['value'].get('text', [])
                text = text_value[0] if text_value else ""
                break
        
        if not text:
            continue
        
        sicherheiten_annotations.append({
            'index': index,  # ← Array-Position!
            'label': label,
            'text': text
        })
    
    if not sicherheiten_annotations:
        return []
    
    # 2. Sortiere nach Array-Index (= chronologische Reihenfolge)
    sicherheiten_annotations.sort(key=lambda x: x['index'])
    
    # 3. Gruppiere: Jedes 'sicherheit_typ' startet neuen Block
    sicherheiten = []
    current_sicherheit = None
    
    for ann in sicherheiten_annotations:
        label = ann['label']
        text = ann['text']
        
        # NEUER BLOCK: sicherheit_typ
        if label == 'sicherheit_typ':
            # Speichere vorherige Sicherheit
            if current_sicherheit and current_sicherheit.get('typ'):
                sicherheiten.append(current_sicherheit)
            
            # Starte neue Sicherheit
            current_sicherheit = {'typ': text.lower()}
        
        # Füge zu aktuellem Block hinzu
        elif current_sicherheit:
            if label == 'sicherheit_betrag':
                current_sicherheit['betrag_text'] = text
            
            elif label == 'sicherheit_strasse':
                if 'adresse' not in current_sicherheit:
                    current_sicherheit['adresse'] = {}
                current_sicherheit['adresse']['strasse'] = text
            
            elif label == 'sicherheit_plz':
                if 'adresse' not in current_sicherheit:
                    current_sicherheit['adresse'] = {}
                current_sicherheit['adresse']['plz'] = text
            
            elif label == 'sicherheit_ort':
                if 'adresse' not in current_sicherheit:
                    current_sicherheit['adresse'] = {}
                current_sicherheit['adresse']['ort'] = text
            
            elif label == 'grundbuch_blatt':
                if 'grundbuch' not in current_sicherheit:
                    current_sicherheit['grundbuch'] = {}
                current_sicherheit['grundbuch']['blatt'] = text
            
            elif label == 'grundbuch_flur':
                if 'grundbuch' not in current_sicherheit:
                    current_sicherheit['grundbuch'] = {}
                current_sicherheit['grundbuch']['flur'] = text
            
            elif label == 'grundbuch_flurstueck':
                if 'grundbuch' not in current_sicherheit:
                    current_sicherheit['grundbuch'] = {}
                current_sicherheit['grundbuch']['flurstueck'] = text
            
            elif label == 'versicherungsnummer':
                current_sicherheit['versicherungsnummer'] = text
    
    # Letzte Sicherheit hinzufügen
    if current_sicherheit and current_sicherheit.get('typ'):
        sicherheiten.append(current_sicherheit)
    
    return sicherheiten

def process_export(raw_file: Path, output_base_dir: Path):
    """
    Label Studio JSON → Separate JSONs pro Dokument (v7 fixed)
    
    Args:
        raw_file: Label Studio Export (z.B. label_studio_export.json)
        output_base_dir: Basis-Verzeichnis (z.B. data/eval/)
    """
    
    print(f"📂 Lese Label Studio Export: {raw_file}")
    
    with open(raw_file, encoding="utf-8") as f:
        raw_data = json.load(f)
    
    print(f"   {len(raw_data)} Tasks gefunden")
    
    # Gruppiere Annotations nach Dokument
    documents = {}
    
    for task in raw_data:
        # Dokument-ID extrahieren
        image_path = task["data"].get("image", "")
        doc_id = extract_doc_id(image_path)
        
        if doc_id not in documents:
            documents[doc_id] = {
                "document": doc_id,
                "vertragsnummer": None,
                "darlehensnehmer": None,
                "darlehensnehmer_adresse": {},
                "kreditgeber": None,
                "iban": [],
                "bic": [],
                "darlehenssumme": None,
                "sollzinssatz": None,
                "effektivzinssatz": None,
                "laufzeit": None,
                "sondertilgung_prozent": None,
                "vertragsbeginn": None,
                "vertragsende": None,
                "vertragsdatum": None,
                "sicherheiten": [],  # ← Starte als leere Liste!
                "sicherheiten_legacy": []
            }
        
        if not task.get("annotations"):
            continue
        
        annotation = task["annotations"][0]
        result_array = annotation["result"]  # ← Komplettes Array!
        
        # Verarbeite Standard-Felder
        for result in result_array:
            if result['type'] != 'rectanglelabels':
                continue
            
            label = result['value']['rectanglelabels'][0]
            rid = result['id']
            
            # Skip Sicherheiten (werden separat gruppiert)
            if label.startswith('sicherheit_') or label.startswith('grundbuch_') or label == 'versicherungsnummer':
                continue
            
            # Text aus textarea
            text = ""
            for r in result_array:
                if r['type'] == 'textarea' and r['id'] == rid:
                    text_value = r['value'].get('text', [])
                    text = text_value[0] if text_value else ""
                    break
            
            if not text:
                continue
            
            # Zuordnung
            if label == "vertragsnummer":
                documents[doc_id]["vertragsnummer"] = text
            
            elif label == "darlehensnehmer":
                documents[doc_id]["darlehensnehmer"] = text
            
            elif label == "darlehensnehmer_strasse":
                documents[doc_id]["darlehensnehmer_adresse"]["strasse"] = text
            
            elif label == "darlehensnehmer_plz":
                documents[doc_id]["darlehensnehmer_adresse"]["plz"] = text
            
            elif label == "darlehensnehmer_ort":
                documents[doc_id]["darlehensnehmer_adresse"]["ort"] = text
            
            elif label == "kreditgeber":
                documents[doc_id]["kreditgeber"] = text
            
            elif label == "iban":
                iban_clean = text.replace(" ", "").upper()
                documents[doc_id]["iban"].append({
                    "value": iban_clean,
                    "valid": validate_iban(iban_clean)
                })
            
            elif label == "bic":
                documents[doc_id]["bic"].append(text.replace(" ", "").upper())
            
            elif label == "darlehenssumme":
                documents[doc_id]["darlehenssumme"] = normalize_currency(text)
            
            elif label == "sollzinssatz":
                documents[doc_id]["sollzinssatz"] = normalize_percentage(text)
            
            elif label == "effektivzinssatz":
                documents[doc_id]["effektivzinssatz"] = normalize_percentage(text)
            
            elif label == "laufzeit":
                documents[doc_id]["laufzeit"] = text
            
            elif label == "sondertilgung_prozent":
                documents[doc_id]["sondertilgung_prozent"] = normalize_percentage(text)
            
            elif label == "vertragsbeginn":
                documents[doc_id]["vertragsbeginn"] = normalize_date(text)
            
            elif label == "vertragsende":
                documents[doc_id]["vertragsende"] = normalize_date(text)
            
            elif label == "vertragsdatum":
                documents[doc_id]["vertragsdatum"] = normalize_date(text)
            
            elif label == "sicherheit":  # Legacy v1.0
                documents[doc_id]["sicherheiten_legacy"].append(text)
        
        # Sicherheiten sequenziell gruppieren (v7)
        sicherheiten_grouped = group_sicherheiten_sequential(result_array)
        if sicherheiten_grouped:
            # APPEND statt REPLACE! ← FIX!
            documents[doc_id]["sicherheiten"].extend(sicherheiten_grouped)
    
    print(f"\n✅ {len(documents)} Dokument(e) identifiziert\n")
    
    # Speichere pro Dokument
    metadata = {
        "export_date": datetime.now().isoformat(),
        "source_file": str(raw_file),
        "total_documents": len(documents),
        "documents": []
    }
    
    for doc_id, doc in documents.items():
        # IBAN/BIC bereinigen
        if doc["iban"]:
            primary_iban = doc["iban"][0]
            doc["iban"] = primary_iban["value"]
            doc["iban_valid"] = primary_iban["valid"]
        else:
            doc["iban"] = None
            doc["iban_valid"] = False
        
        if doc["bic"]:
            doc["bic"] = doc["bic"][0]
        else:
            doc["bic"] = None
        
        # Adresse entfernen wenn leer
        if not doc["darlehensnehmer_adresse"]:
            doc.pop("darlehensnehmer_adresse")
        
        # Sicherheiten: Kombiniere strukturiert + legacy
        if not doc["sicherheiten"] and doc["sicherheiten_legacy"]:
            doc["sicherheiten"] = [{"text": s} for s in doc["sicherheiten_legacy"]]
        
        doc.pop("sicherheiten_legacy")
        
        # Dokumenten-Ordner erstellen
        doc_dir = output_base_dir / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        # Entities JSON speichern
        entities_file = doc_dir / "entities.json"
        with open(entities_file, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        
        # Statistik
        entity_count = sum([
            1 if doc["vertragsnummer"] else 0,
            1 if doc["darlehensnehmer"] else 0,
            1 if "darlehensnehmer_adresse" in doc else 0,
            1 if doc["kreditgeber"] else 0,
            1 if doc["iban"] else 0,
            1 if doc["bic"] else 0,
            1 if doc["darlehenssumme"] else 0,
            1 if doc["sollzinssatz"] else 0,
            1 if doc["effektivzinssatz"] else 0,
            1 if doc["laufzeit"] else 0,
            1 if doc["sondertilgung_prozent"] else 0,
            1 if doc["vertragsbeginn"] else 0,
            1 if doc["vertragsende"] else 0,
            1 if doc["vertragsdatum"] else 0,
            len(doc["sicherheiten"])
        ])
        
        print(f"📄 {doc_id}")
        print(f"   📁 {entities_file}")
        print(f"   📊 {entity_count} Felder extrahiert")
        if "darlehensnehmer_adresse" in doc:
            print(f"   🏠 Adresse: {doc['darlehensnehmer_adresse']}")
        if doc["sondertilgung_prozent"]:
            print(f"   💰 Sondertilgung: {doc['sondertilgung_prozent']}%")
        if doc["sicherheiten"]:
            print(f"   🔒 Sicherheiten: {len(doc['sicherheiten'])}")
            for s in doc["sicherheiten"]:
                print(f"      - {s.get('typ', 'unbekannt')}: {s.get('betrag_text', 'N/A')}")
                if 'versicherungsnummer' in s:
                    print(f"        LV-Nr: {s['versicherungsnummer']}")
                if 'adresse' in s:
                    print(f"        Adresse: {s['adresse']}")
                if 'grundbuch' in s:
                    print(f"        Grundbuch: {s['grundbuch']}")
        
        # Metadata
        metadata["documents"].append({
            "doc_id": doc_id,
            "entities_file": str(entities_file.relative_to(output_base_dir)),
            "entity_count": entity_count,
            "has_iban": doc["iban"] is not None,
            "has_address": "darlehensnehmer_adresse" in doc,
            "has_sondertilgung": doc["sondertilgung_prozent"] is not None,
            "sicherheiten_count": len(doc["sicherheiten"])
        })
    
    # Metadata speichern
    metadata_file = output_base_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Metadata: {metadata_file}")
    print(f"✅ Fertig! (v7 FIXED - Multi-Seiten-Support)")

if __name__ == "__main__":
    process_export(
        raw_file=Path("data/eval/raw/label_studio_export.json"),
        output_base_dir=Path("data/eval")
    )