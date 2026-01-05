"""
Preprocessing für alle Dokumente im interim-Ordner.
Wendet Deskew, CLAHE und Sauvola auf alle Seiten an.
"""
from pathlib import Path
import sys
from typing import List
import cv2
import shutil
import numpy as np
from PIL import Image

# Projekt-Root zum Path
if str(Path(__file__).parent.parent.parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.preprocess.deskew import deskew_image, imread_unicode
from src.preprocess.clahe import apply_clahe
from src.preprocess.threshold import sauvola_threshold


def preprocess_image(
    input_path: Path,
    output_path: Path,
    deskew: bool = True,
    clahe: bool = True,
    threshold: bool = True,
    clip_limit: float = 2.0,
    window_size: int = 25,
    k: float = 0.2
) -> dict:
    """
    Wendet komplette Preprocessing-Pipeline auf ein Bild an.
    
    Returns:
        dict mit Stats (angle, ...)
    """
    # Laden
    image = imread_unicode(input_path)
    stats = {}
    
    # 1. Deskew
    if deskew:
        image, angle = deskew_image(image)
        stats['deskew_angle'] = angle
    
    # 2. Zu Graustufen
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # 3. CLAHE
    if clahe:
        image = apply_clahe(image, clip_limit=clip_limit, tile_size=8)
        stats['clahe'] = True
    
    # 4. Sauvola Threshold
    if threshold:
        image = sauvola_threshold(image, window_size=window_size, k=k)
        stats['threshold'] = True
    
    # Speichern
    img_pil = Image.fromarray(image, mode='L')
    img_pil.save(str(output_path))
    
    return stats


def copy_to_label_studio(preprocessed_images: List[Path], ls_output: Path) -> int:
    """
    Kopiert preprocessed Bilder nach Label Studio (flaches Verzeichnis).
    
    Args:
        preprocessed_images: Liste der preprocessed Bildpfade
        ls_output: Label Studio Ausgabe-Verzeichnis
    
    Returns:
        Anzahl kopierter Bilder
    """
    ls_output.mkdir(parents=True, exist_ok=True)
    copied = 0
    
    for img_path in preprocessed_images:
        # Neuer Dateiname: <doc>_<page>_preprocessed.png
        # z.B. data/interim/doc1/page_001_preprocessed.png
        #   → data/label_studio/images/doc1_page_001_preprocessed.png
        doc_name = img_path.parent.name
        ls_filename = f"{doc_name}_{img_path.name}"
        ls_path = ls_output / ls_filename
        
        # Kopiere Bild
        shutil.copy2(img_path, ls_path)
        copied += 1
    
    return copied


def preprocess_all_documents(
    interim_dir: Path,
    skip_existing: bool = True,
    copy_to_ls: bool = False,
    **preprocess_kwargs
) -> dict:
    """
    Preprocesst alle Seiten aller Dokumente im interim-Ordner.
    
    Args:
        interim_dir: data/interim/
        skip_existing: Wenn True, überspringe bereits preprocesste Seiten
        copy_to_ls: Wenn True, kopiere nach Label Studio
        **preprocess_kwargs: Parameter für preprocess_image()
    
    Returns:
        dict mit Statistiken
    """
    # Alle Dokument-Ordner finden
    doc_dirs = [d for d in interim_dir.iterdir() 
                if d.is_dir() and (d / "meta.json").exists()]
    
    if not doc_dirs:
        print("❌ Keine Dokumente gefunden in", interim_dir)
        return {}
    
    print(f"📄 Gefunden: {len(doc_dirs)} Dokument(e)\n")
    
    stats = {
        'total_docs': len(doc_dirs),
        'total_pages': 0,
        'processed': 0,
        'skipped': 0,
        'errors': 0,
        'ls_copied': 0
    }
    
    preprocessed_images = []  # Für Label Studio
    
    for doc_dir in sorted(doc_dirs):
        print(f"📂 {doc_dir.name}")
        
        # Alle Original-Seiten finden (ohne _preprocessed)
        page_files = sorted([
            f for f in doc_dir.glob("page_*.png")
            if "_preprocessed" not in f.name
        ])
        
        stats['total_pages'] += len(page_files)
        
        for page_file in page_files:
            output_file = page_file.parent / f"{page_file.stem}_preprocessed.png"
            
            # Skip wenn bereits existiert
            if skip_existing and output_file.exists():
                print(f"   ⏭️  SKIP: {page_file.name} (bereits preprocessed)")
                stats['skipped'] += 1
                preprocessed_images.append(output_file)  # Trotzdem zur Liste
                continue
            
            try:
                # Preprocessing anwenden
                page_stats = preprocess_image(page_file, output_file, **preprocess_kwargs)
                
                angle = page_stats.get('deskew_angle', 0.0)
                print(f"   ✅ {page_file.name} → {output_file.name} ({angle:.2f}°)")
                stats['processed'] += 1
                preprocessed_images.append(output_file)
                
            except Exception as e:
                print(f"   ❌ FEHLER bei {page_file.name}: {e}")
                stats['errors'] += 1
        
        print()  # Leerzeile nach jedem Dokument
    
    # Label Studio Export
    if copy_to_ls and preprocessed_images:
        print("📋 Kopiere zu Label Studio...")
        ls_output = Path("data/label_studio/images")
        copied = copy_to_label_studio(preprocessed_images, ls_output)
        stats['ls_copied'] = copied
        print(f"   ✅ {copied} Bilder → {ls_output}\n")
    
    return stats


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Preprocessing: Alle Dokumente')
    parser.add_argument('--input', default='data/interim', help='Input-Verzeichnis')
    parser.add_argument('--force', action='store_true', help='Überschreibe existierende')
    parser.add_argument('--no-deskew', action='store_true', help='Deskew deaktivieren')
    parser.add_argument('--no-clahe', action='store_true', help='CLAHE deaktivieren')
    parser.add_argument('--no-threshold', action='store_true', help='Threshold deaktivieren')
    parser.add_argument('--clip', type=float, default=2.0, help='CLAHE Clip Limit')
    parser.add_argument('--window', type=int, default=25, help='Sauvola Window Size')
    parser.add_argument('--k', type=float, default=0.2, help='Sauvola k-Parameter')
    parser.add_argument('--label-studio', action='store_true', help='Kopiere zu Label Studio')
    
    args = parser.parse_args()
    
    interim_dir = Path(args.input)
    
    if not interim_dir.exists():
        print(f"❌ Verzeichnis nicht gefunden: {interim_dir}")
        sys.exit(1)
    
    print("🔄 Starte Preprocessing...\n")
    
    stats = preprocess_all_documents(
        interim_dir,
        skip_existing=not args.force,
        copy_to_ls=args.label_studio,
        deskew=not args.no_deskew,
        clahe=not args.no_clahe,
        threshold=not args.no_threshold,
        clip_limit=args.clip,
        window_size=args.window,
        k=args.k
    )
    
    print("="*60)
    print("✅ FERTIG!\n")
    print(f"📊 Statistik:")
    print(f"   Dokumente:   {stats['total_docs']}")
    print(f"   Seiten:      {stats['total_pages']}")
    print(f"   Verarbeitet: {stats['processed']}")
    print(f"   Übersprungen: {stats['skipped']}")
    print(f"   Fehler:      {stats['errors']}")
    if stats.get('ls_copied', 0) > 0:
        print(f"   Label Studio: {stats['ls_copied']}")