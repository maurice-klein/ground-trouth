"""PDF zu Bildern konvertieren mit PyMuPDF - mit Smart Skip."""
import fitz  # PyMuPDF
from pathlib import Path
import json
from typing import Tuple, List


def is_already_processed(pdf_path: Path, output_dir: Path) -> bool:
    """
    Prüft, ob PDF bereits verarbeitet wurde.
    
    Returns:
        True wenn bereits verarbeitet und aktuell
    """
    doc_name = pdf_path.stem
    doc_output = output_dir / doc_name
    meta_file = doc_output / "meta.json"
    
    # Existiert der Ordner nicht? → Noch nicht verarbeitet
    if not doc_output.exists():
        return False
    
    # Existiert meta.json nicht? → Unvollständig verarbeitet
    if not meta_file.exists():
        return False
    
    # Meta laden und Seitenzahl prüfen
    try:
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        
        # PDF öffnen und Seitenzahl vergleichen
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()
        
        # Stimmt die Seitenzahl?
        if meta.get('num_pages') != num_pages:
            return False
        
        # Existieren alle Bilder?
        expected_images = [doc_output / f"page_{i:03d}.png" for i in range(num_pages)]
        if not all(img.exists() for img in expected_images):
            return False
        
        return True  # ✅ Alles da und aktuell!
        
    except Exception as e:
        print(f"⚠️  Fehler beim Prüfen: {e}")
        return False  # Bei Fehler lieber neu verarbeiten


def pdf_to_images(
    pdf_path: Path, 
    output_dir: Path, 
    dpi: int = 400,
    force: bool = False
) -> Tuple[List[Path], dict]:
    """
    Konvertiert PDF-Seiten in PNG-Bilder.
    
    Args:
        pdf_path: Pfad zum PDF
        output_dir: Ausgabe-Verzeichnis
        dpi: Auflösung (DPI)
        force: Wenn True, wird immer neu verarbeitet (überschreibt)
    
    Returns:
        Liste der erstellten Bild-Pfade + Metadaten
    """
    doc_name = pdf_path.stem
    doc_output = output_dir / doc_name
    
    # Skip-Check (außer bei force=True)
    if not force and is_already_processed(pdf_path, output_dir):
        print(f"⏭️  SKIP: {pdf_path.name} (bereits verarbeitet)")
        
        # Bestehende Daten laden
        meta_file = doc_output / "meta.json"
        with open(meta_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        images = [doc_output / f"page_{i:03d}.png" for i in range(metadata['num_pages'])]
        return images, metadata
    
    # Neu verarbeiten
    print(f"🔄 VERARBEITE: {pdf_path.name}")
    
    doc = fitz.open(pdf_path)
    doc_output.mkdir(parents=True, exist_ok=True)
    
    images = []
    metadata = {
        "doc_name": doc_name,
        "num_pages": len(doc),
        "pages": []
    }
    
    # DPI in Zoom-Faktor umrechnen (72 DPI ist Standard)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(matrix=mat)
        
        # Bild speichern
        img_path = doc_output / f"page_{page_num:03d}.png"
        pix.save(str(img_path))
        images.append(img_path)
        
        # Metadaten sammeln
        metadata["pages"].append({
            "page_num": page_num,
            "width": page.rect.width,
            "height": page.rect.height,
            "image": str(img_path.relative_to(output_dir))
        })
        
        print(f"  ✅ Seite {page_num + 1}/{len(doc)} → {img_path.name}")
    
    # Metadaten speichern
    meta_path = doc_output / "meta.json"
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    doc.close()
    return images, metadata


if __name__ == "__main__":
    import argparse
    
    # CLI-Argumente
    parser = argparse.ArgumentParser(description='PDF zu Bildern konvertieren')
    parser.add_argument('--input', default='data/raw', help='Input-Verzeichnis mit PDFs')
    parser.add_argument('--output', default='data/interim', help='Output-Verzeichnis')
    parser.add_argument('--dpi', type=int, default=400, help='Auflösung in DPI')
    parser.add_argument('--force', action='store_true', help='Alle PDFs neu verarbeiten (überschreiben)')
    
    args = parser.parse_args()
    
    input_dir = Path(args.input)
    output_dir = Path(args.output)
    
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("❌ Keine PDFs gefunden in", input_dir)
        exit(1)
    
    print(f"📄 Gefunden: {len(pdf_files)} PDF(s)")
    print(f"🔄 Force-Modus: {'JA (überschreibt alles)' if args.force else 'NEIN (skip bereits verarbeitete)'}")
    print()
    
    processed = 0
    skipped = 0
    
    for pdf_file in pdf_files:
        images, meta = pdf_to_images(pdf_file, output_dir, dpi=args.dpi, force=args.force)
        
        if is_already_processed(pdf_file, output_dir) and not args.force:
            skipped += 1
        else:
            processed += 1
    
    print(f"\n✅ Fertig!")
    print(f"   Verarbeitet: {processed}")
    print(f"   Übersprungen: {skipped}")