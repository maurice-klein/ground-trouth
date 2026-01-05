"""
Sauvola Thresholding: Adaptive Binarisierung.
Konvertiert Graustufen in Schwarz-Weiß mit lokalen Schwellenwerten.
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
    # Graustufenbild (2D)
    if len(image.shape) == 2:
        img_pil = Image.fromarray(image, mode='L')
    # Farbbild (3D): BGR → RGB
    elif len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(image)
    else:
        raise ValueError(f"Unerwartete Bildform: {image.shape}")
    
    img_pil.save(str(path))


def sauvola_threshold(image: np.ndarray, window_size: int = 25, k: float = 0.2, 
                      r: float = 128.0) -> np.ndarray:
    """
    Sauvola Adaptive Thresholding.
    
    Args:
        image: Graustufenbild
        window_size: Größe des lokalen Fensters (ungerade!)
        k: Sauvola-Parameter (0.2-0.5 typisch)
        r: Dynamikbereich (128 für uint8)
    
    Returns:
        Binärbild (0/255)
    """
    # Sicherstellen dass window_size ungerade ist
    if window_size % 2 == 0:
        window_size += 1
    
    # Lokale Mittelwerte und Standardabweichungen
    mean = cv2.blur(image.astype(np.float32), (window_size, window_size))
    
    # Quadrat für Standardabweichung
    sqmean = cv2.blur((image.astype(np.float32) ** 2), (window_size, window_size))
    std = np.sqrt(sqmean - mean ** 2)
    
    # Sauvola-Schwellenwert
    threshold = mean * (1 + k * ((std / r) - 1))
    
    # Binarisierung
    binary = np.where(image > threshold, 255, 0).astype(np.uint8)
    
    return binary


def threshold_file(input_path: Path, output_path: Path, window_size: int = 25, 
                   k: float = 0.2) -> None:
    """
    Lädt Bild, binarisiert es, speichert es.
    """
    image = imread_unicode(input_path)
    
    # Zu Graustufen konvertieren falls nötig
    if len(image.shape) == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Sauvola Thresholding anwenden
    binary = sauvola_threshold(image, window_size, k)
    
    # Speichern
    imwrite_unicode(output_path, binary)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Sauvola: Adaptive Binarisierung')
    parser.add_argument('input', type=Path, help='Input-Bild (Graustufen)')
    parser.add_argument('output', type=Path, help='Output-Bild (Binär)')
    parser.add_argument('--window', type=int, default=25, help='Window Size')
    parser.add_argument('--k', type=float, default=0.2, help='Sauvola k-Parameter')
    
    args = parser.parse_args()
    
    threshold_file(args.input, args.output, args.window, args.k)
    print(f"✅ Binarisiert (window={args.window}, k={args.k}) → {args.output}")