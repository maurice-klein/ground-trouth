"""
Deskewing: Schiefe Bilder begradigen mittels Hough-Transform.
Für gescannte Kreditverträge die oft ±2-5° schief sind.
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple, Optional
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
    
    # Speichern mit absoluter Pfadauflösung
    output_path = Path(path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img_pil.save(output_path)
    print(f"   💾 Gespeichert: {output_path}")

def detect_skew_angle(image: np.ndarray, delta: float = 1.0, limit: float = 5.0) -> float:
    """
    Erkennt Schräglage eines Bildes mittels Hough-Transform.
    
    Args:
        image: Graustufenbild (cv2-Format)
        delta: Winkelauflösung in Grad
        limit: Maximaler Winkel zum Testen (±limit)
    
    Returns:
        Erkannter Winkel in Grad (positiv = gegen Uhrzeigersinn)
    """
    # Kanten erkennen (Canny)
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    
    # Hough-Line-Transform
    angles = np.arange(-limit, limit + delta, delta)
    scores = []
    
    for angle in angles:
        # Bild rotieren
        h, w = image.shape
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(edges, M, (w, h), flags=cv2.INTER_CUBIC, 
                                  borderMode=cv2.BORDER_REPLICATE)
        
        # Score: Summe der horizontalen Kanten (je höher, desto gerader)
        score = np.sum(rotated, axis=1).var()
        scores.append(score)
    
    # Bester Winkel
    best_angle = angles[np.argmax(scores)]
    return best_angle


def deskew_image(image: np.ndarray, angle: Optional[float] = None) -> Tuple[np.ndarray, float]:
    """
    Begradigt ein schräges Bild.
    
    Args:
        image: Input-Bild (Graustufen oder BGR)
        angle: Wenn None, wird Winkel automatisch erkannt
    
    Returns:
        (deskewed_image, angle)
    """
    # Zu Graustufen konvertieren falls nötig
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Winkel erkennen falls nicht gegeben
    if angle is None:
        angle = detect_skew_angle(gray)
    
    # Nichts tun bei sehr kleinem Winkel
    if abs(angle) < 0.1:
        return image, 0.0
    
    # Rotation durchführen
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Auf Originalformat rotieren
    if len(image.shape) == 3:
        deskewed = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)
    else:
        deskewed = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC,
                                   borderMode=cv2.BORDER_REPLICATE)
    
    return deskewed, angle


def deskew_file(input_path: Path, output_path: Path, angle: Optional[float] = None) -> float:
    image = imread_unicode(input_path)  # ← FIX
    """
    Lädt Bild, begradigt es, speichert es.
    
    Returns:
        Angewendeter Winkel
    """
    deskewed, detected_angle = deskew_image(image, angle)
    
    imwrite_unicode(output_path, deskewed)  # ← FIX
    
    return detected_angle


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Deskew: Schiefe Bilder begradigen')
    parser.add_argument('input', type=Path, help='Input-Bild')
    parser.add_argument('output', type=Path, help='Output-Bild')
    parser.add_argument('--angle', type=float, default=None, help='Fester Winkel (sonst Auto-Detect)')
    
    args = parser.parse_args()
    
    angle = deskew_file(args.input, args.output, args.angle)
    print(f"✅ Deskewed: {angle:.2f}° → {args.output}")