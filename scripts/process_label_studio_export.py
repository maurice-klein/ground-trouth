#!/usr/bin/env python3
"""
Konvertiert Label Studio Export zu dokumentenbasierter Ground Truth Struktur

V3: FIX - Entfernt Label Studio Hash-Prefix korrekt
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
    
    WICHTIG: Entfernt Label Studio Hash-Prefix!
    
    Beispiele:
    - /data/upload/1/72b377a7-Kreditvertrag_001_Annuitätendarlehen_born_page_000.png
      → Kreditvertrag_001_Annuitätendarlehen_born
    
    - 5e0705cb-Kreditvertrag_001_Annuitätendarlehen_born_page_002.png
      → Kreditvertrag_001_Annuitätendarlehen_born
    
    Returns: Kreditvertrag_001_Annuitätendarlehen_born (ohne Hash, ohne _page_XXX)
    """
    # Dateiname extrahieren
    filename = Path(image_path).name
    
    # URL-Encoding rückgängig machen (%C3%A4 → ä)
    from urllib.parse import unquote
    filename = unquote(filename)
    
    # 1. Hash-Prefix entfernen (alles vor erstem Bindestrich nach 8 Hex-Zeichen)
    # Pattern: 8 Hex-Zeichen + Bindestrich = Label Studio Hash
    hash_pattern = r'^[0-9a-f]{8}-(.+)$'
    match = re.match(hash_pattern, filename)
    if match:
        filename = match.group(1)  # Rest nach Hash
    
    # 2. _page_XXX.png entfernen
    page_pattern = r'^(.+)_page_\d+\.png$'
    match = re.match(page_pattern, filename)
    if match:
        return match.group(1)
    
    # Fallback: alles vor _page_
    parts = filename.split('_page_')
    return parts[0] if parts else "unknown"

def process_export(raw_file: Path, output_base_dir: Path):
    """
    Label Studio JSON → Separate JSONs pro Dokument
    
    Args:
        raw_file: Label Studio Export (z.B. label_studio_export.json)
        output_base_dir: Basis-Verzeichnis (z.B. data/eval/)
    """
    
    print(f"📂 Lese Label Studio Export: {raw_file}")
    
    with open(raw_file, encoding="utf-8") as f:
        raw_data = json.load(f)
    
    print(f"   {len(raw_data)} Tasks gefunden")
    
    # DEBUG: Zeige erkannte Dokumente
    print("\n🔍 Erkannte Dokumente:")
    for task in raw_data:
        image_path = task["data"].get("image", "")
        doc_id = extract_doc_id(image_path)
        page_num = Path(image_path).stem.split('_page_')[-1].split('.')[0] if '_page_' in image_path else '?'
        print(f"   Seite {page_num}: {doc_id}")
    
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
                "kreditgeber": None,
                "iban": [],
                "bic": [],
                "darlehenssumme": None,
                "sollzinssatz": None,
                "effektivzinssatz": None,
                "laufzeit": None,
                "vertragsbeginn": None,
                "vertragsende": None,
                "vertragsdatum": None,
                "sicherheiten": []
            }
        
        if not task.get("annotations"):
            continue
        
        annotation = task["annotations"][0]
        
        # Gruppiere rectanglelabels und textarea
        rectangles = {}
        textareas = {}
        
        for result in annotation["result"]:
            if result["type"] == "rectanglelabels":
                rectangles[result["id"]] = result
            elif result["type"] == "textarea":
                textareas[result["id"]] = result
        
        # Verarbeite jede Annotation
        for rid, rect in rectangles.items():
            label = rect["value"]["rectanglelabels"][0]
            
            # Text aus textarea
            text = ""
            if rid in textareas:
                text_value = textareas[rid]["value"].get("text", [])
                text = text_value[0] if text_value else ""
            
            if not text:
                continue
            
            # Zuordnung basierend auf Label
            if label == "vertragsnummer":
                documents[doc_id]["vertragsnummer"] = text
            
            elif label == "darlehensnehmer":
                documents[doc_id]["darlehensnehmer"] = text
            
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
            
            elif label == "vertragsbeginn":
                documents[doc_id]["vertragsbeginn"] = normalize_date(text)
            
            elif label == "vertragsende":
                documents[doc_id]["vertragsende"] = normalize_date(text)
            
            elif label == "vertragsdatum":
                documents[doc_id]["vertragsdatum"] = normalize_date(text)
            
            elif label == "sicherheit":
                documents[doc_id]["sicherheiten"].append(text)
    
    print(f"\n✅ {len(documents)} Dokument(e) identifiziert\n")
    
    # Bereinige Listen (IBAN/BIC) und speichere pro Dokument
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
            1 if doc["kreditgeber"] else 0,
            1 if doc["iban"] else 0,
            1 if doc["bic"] else 0,
            1 if doc["darlehenssumme"] else 0,
            1 if doc["sollzinssatz"] else 0,
            1 if doc["effektivzinssatz"] else 0,
            1 if doc["laufzeit"] else 0,
            1 if doc["vertragsbeginn"] else 0,
            1 if doc["vertragsende"] else 0,
            1 if doc["vertragsdatum"] else 0,
            len(doc["sicherheiten"])
        ])
        
        print(f"📄 {doc_id}")
        print(f"   📁 {entities_file}")
        print(f"   📊 {entity_count} Felder extrahiert")
        
        # Metadata
        metadata["documents"].append({
            "doc_id": doc_id,
            "entities_file": str(entities_file.relative_to(output_base_dir)),
            "entity_count": entity_count,
            "has_iban": doc["iban"] is not None,
            "has_sicherheiten": len(doc["sicherheiten"]) > 0
        })
    
    # Metadata speichern
    metadata_file = output_base_dir / "metadata.json"
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print(f"\n📋 Metadata: {metadata_file}")
    print(f"✅ Fertig!")

if __name__ == "__main__":
    process_export(
        raw_file=Path("data/eval/raw/label_studio_export.json"),
        output_base_dir=Path("data/eval")
    )