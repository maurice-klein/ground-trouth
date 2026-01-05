"""
PDF-Analyse-Modul für Kapitel 4.2.1 (PDF-Engine: PyMuPDF)

Funktionen:
- Text-Layer-Prüfung (born-digital vs. gescannt)
- Native Text-Extraktion mit Bounding Boxes
- PDF-Metadaten-Analyse
"""

import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


def has_text_layer(pdf_path: Path) -> bool:
    """
    Prüft ob PDF einen Text-Layer hat (born-digital) oder nur Bilder (gescannt).
    
    Args:
        pdf_path: Pfad zum PDF
        
    Returns:
        True wenn Text-Layer vorhanden, False bei reinen Bildern
        
    Methode:
        Ein PDF gilt als "born-digital" wenn mindestens eine Seite
        extrahierbaren Text enthält (> 10 Zeichen zur Fehlertoleranz).
    """
    try:
        doc = fitz.open(pdf_path)
        
        # Prüfe erste 3 Seiten (ausreichend für Klassifikation)
        pages_to_check = min(3, len(doc))
        
        for page_num in range(pages_to_check):
            page = doc[page_num]
            text = page.get_text().strip()
            
            # Wenn Seite mehr als 10 Zeichen Text hat → Text-Layer vorhanden
            if len(text) > 10:
                doc.close()
                return True
        
        doc.close()
        return False
        
    except Exception as e:
        print(f"⚠️  Fehler beim Text-Layer-Check: {e}")
        return False


def extract_native_text_with_bbox(
    pdf_path: Path, 
    page_num: int
) -> List[Dict]:
    """
    Extrahiert Text mit Bounding Boxes aus born-digital PDFs.
    
    Args:
        pdf_path: Pfad zum PDF
        page_num: Seitennummer (0-basiert)
        
    Returns:
        Liste von Dicts mit: {text, bbox, font_size, font_name, block_type}
        
    Format bbox: [x0, y0, x1, y1] (links-oben, rechts-unten)
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_num]
        
        # get_text("dict") liefert strukturierte Informationen
        text_dict = page.get_text("dict")
        
        text_blocks = []
        
        # Durchlaufe alle Blöcke auf der Seite
        for block in text_dict.get("blocks", []):
            # Nur Text-Blöcke (type 0), keine Bilder (type 1)
            if block.get("type") == 0:
                
                # Durchlaufe alle Zeilen im Block
                for line in block.get("lines", []):
                    line_text = ""
                    line_bbox = line.get("bbox")
                    
                    # Durchlaufe alle Spans (Textabschnitte mit gleicher Formatierung)
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    
                    # Nur Zeilen mit tatsächlichem Text
                    if line_text.strip():
                        text_blocks.append({
                            "text": line_text.strip(),
                            "bbox": list(line_bbox),  # [x0, y0, x1, y1]
                            "font_size": line["spans"][0].get("size", 0) if line.get("spans") else 0,
                            "font_name": line["spans"][0].get("font", "") if line.get("spans") else "",
                            "block_type": "text"
                        })
        
        doc.close()
        return text_blocks
        
    except Exception as e:
        print(f"⚠️  Fehler bei Text-Extraktion: {e}")
        return []


def analyze_pdf_metadata(pdf_path: Path) -> Dict:
    """
    Vollständige PDF-Metadaten-Analyse (robust gegen fehlende Methoden).
    """
    try:
        doc = fitz.open(pdf_path)
        
        # Text-Layer-Prüfung
        has_text = has_text_layer(pdf_path)
        
        # Textmenge pro Seite analysieren (erste 5 Seiten)
        text_lengths = []
        pages_to_sample = min(5, len(doc))
        
        for page_num in range(pages_to_sample):
            try:
                page = doc[page_num]
                text = page.get_text()
                text_lengths.append(len(text))
            except Exception as e:
                print(f"   ⚠️  Warnung bei Seite {page_num}: {e}")
                continue
        
        avg_text_length = sum(text_lengths) / len(text_lengths) if text_lengths else 0.0
        
        # PDF-Metadaten (mit Fallback)
        try:
            metadata = doc.metadata or {}
        except:
            metadata = {}
        
        # PDF-Version (mit Fallback - OPTIONAL!)
        try:
            pdf_ver = doc.pdf_version()
        except AttributeError:
            # Methode existiert nicht in älteren PyMuPDF-Versionen
            pdf_ver = None
        except Exception:
            pdf_ver = None
        
        analysis = {
            "filename": pdf_path.name,
            "num_pages": len(doc),
            "has_text_layer": has_text,
            "document_type": "born-digital" if has_text else "scanned",
            "avg_text_length_per_page": round(avg_text_length, 1),
            "is_encrypted": doc.is_encrypted,
            "metadata": {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "creator": metadata.get("creator", ""),
                "producer": metadata.get("producer", ""),
                "creation_date": metadata.get("creationDate", ""),
                "mod_date": metadata.get("modDate", "")
            }
        }
        
        # PDF-Version nur hinzufügen wenn verfügbar
        if pdf_ver is not None:
            analysis["pdf_version"] = pdf_ver
        
        doc.close()
        return analysis
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n❌ FEHLER bei {pdf_path.name}:")
        print(error_trace)
        return {
            "filename": pdf_path.name,
            "error": str(e),
            "error_type": type(e).__name__
        }


def analyze_all_pdfs(input_dir: Path, output_file: Optional[Path] = None) -> List[Dict]:
    """
    Analysiert alle PDFs in einem Verzeichnis.
    
    Args:
        input_dir: Verzeichnis mit PDFs
        output_file: Optional - JSON-Datei für Ergebnisse
        
    Returns:
        Liste mit Analyse-Ergebnissen pro PDF
    """
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"❌ Keine PDFs gefunden in {input_dir}")
        return []
    
    results = []
    
    print(f"📊 Analysiere {len(pdf_files)} PDF(s)...\n")
    
    for pdf_file in pdf_files:
        print(f"🔍 {pdf_file.name}...", end=" ")
        analysis = analyze_pdf_metadata(pdf_file)
        results.append(analysis)
        
        doc_type = analysis.get("document_type", "unknown")
        print(f"→ {doc_type}")
    
    # Optional: Ergebnisse speichern
    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Ergebnisse gespeichert: {output_file}")
    
    return results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='PDF-Analyse: Text-Layer, Metadaten, Klassifikation')
    parser.add_argument('--input', default='data/raw', help='Input-Verzeichnis mit PDFs')
    parser.add_argument('--output', default='data/interim/pdf_analysis.json', help='Output JSON-Datei')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_file = Path(args.output)
    
    results = analyze_all_pdfs(input_dir, output_file)
    
    # Zusammenfassung
    if results:
        born_digital = sum(1 for r in results if r.get("document_type") == "born-digital")
        scanned = sum(1 for r in results if r.get("document_type") == "scanned")
        
        print(f"\n📊 Zusammenfassung:")
        print(f"   Total:        {len(results)}")
        print(f"   Born-digital: {born_digital} ({born_digital/len(results)*100:.1f}%)")
        print(f"   Gescannt:     {scanned} ({scanned/len(results)*100:.1f}%)")