"""
CLAHE: Contrast Limited Adaptive Histogram Equalization.
Verbessert Kontrast bei schwachen Scans.
"""
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

def imread_unicode(path: Path) -> np.ndarray:
    """Lädt Bild mit Unicode-Support (für Umlaute etc.)."""
    img_pil = Image.open(path)
    img_np = np.array(img_pil)
    
    # PIL gibt RGB, OpenCV braucht BGR
    if len(img_np.shape) == 3:
        img_np = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    
    return img_np


def imwrite_unicode(path: Path, image: np.ndarray) -> None:
    """Speichert Bild mit Unicode-Support."""
    # OpenCV BGR → PIL RGB
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    
    img_pil = Image.fromarray(image)
    img_pil.save(path)


def apply_clahe(image: np.ndarray, clip_limit: float = 2.0, tile_size: int = 8) -> np.ndarray:
    """
    Wendet CLAHE auf Graustufenbild an.
    
    Args:
        image: Graustufenbild
        clip_limit: Contrast-Limiting (höher = stärker)
        tile_size: Größe der lokalen Regionen
    
    Returns:
        Kontrastverbessertes Bild
    """
    # CLAHE-Objekt erstellen
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_size, tile_size))
    
    # Anwenden
    enhanced = clahe.apply(image)
    
    return enhanced


def clahe_file(input_path: Path, output_path: Path, clip_limit: float = 2.0, 
               tile_size: int = 8) -> None:
    """
    Lädt Bild, wendet CLAHE an, speichert es.
    """
    image = imread_unicode(input_path)
    
    # Zu Graustufen konvertieren falls nötig
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # CLAHE anwenden  ← DAS FEHLT!
    enhanced = apply_clahe(image, clip_limit, tile_size)
    
    # Speichern  ← DAS AUCH!
    imwrite_unicode(output_path, enhanced)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='CLAHE: Kontrast verbessern')
    parser.add_argument('input', type=Path, help='Input-Bild')
    parser.add_argument('output', type=Path, help='Output-Bild')
    parser.add_argument('--clip', type=float, default=2.0, help='Clip Limit (1.0-4.0)')
    parser.add_argument('--tile', type=int, default=8, help='Tile Size')
    
    args = parser.parse_args()
    
    clahe_file(args.input, args.output, args.clip, args.tile)
    print(f"✅ CLAHE angewendet → {args.output}")