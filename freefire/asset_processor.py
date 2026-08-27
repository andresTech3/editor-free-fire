"""
freefire/asset_processor.py
============================
Procesador de assets para Free Fire Edición:
1. Rota el avatar 90° en sentido horario para dejarlo erguido verticalmente.
2. Remueve el fondo del avatar usando OpenCV GrabCut preservando colores reales (BGRA).
3. Recorta la tabla de sensibilidad (sección derecha del menú).
"""

import os
import cv2
import numpy as np
from pathlib import Path
from PIL import Image

from .presets import AVATAR_PATH, SENSIBILIDAD_PATH, ASSETS_DIR

PROCESSED_AVATAR = str(ASSETS_DIR / "avatar_cutout.png")
PROCESSED_SENSIBILIDAD = str(ASSETS_DIR / "sensibilidad_cropped.png")


def process_avatar(avatar_path: str = AVATAR_PATH, output_path: str = PROCESSED_AVATAR) -> str:
    """
    Rota el avatar 90° sentido horario y remueve el fondo con OpenCV GrabCut.
    Preserva colores reales en formato BGRA para evitar distorsiones de color.
    """
    if not os.path.exists(avatar_path):
        print(f"❌ Avatar no encontrado: {avatar_path}")
        return avatar_path

    img = cv2.imread(avatar_path)
    if img is None:
        return avatar_path

    if img.shape[1] > img.shape[0]:
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

    h, w = img.shape[:2]
    rect = (int(w * 0.05), int(h * 0.02), int(w * 0.90), int(h * 0.96))

    mask = np.zeros((h, w), np.uint8)
    bgdModel = np.zeros((1, 65), np.float64)
    fgdModel = np.zeros((1, 65), np.float64)

    try:
        cv2.grabCut(img, mask, rect, bgdModel, fgdModel, 6, cv2.GC_INIT_WITH_RECT)
        mask2 = np.where((mask == 1) | (mask == 3), 255, 0).astype('uint8')
        alpha = cv2.GaussianBlur(mask2, (3, 3), 0)

        # OpenCV imwrite con 4 canales espera formato BGRA
        bgra = cv2.merge([img[:, :, 0], img[:, :, 1], img[:, :, 2], alpha])

        nonzero = np.argwhere(alpha > 10)
        if len(nonzero) > 0:
            ymin, xmin = nonzero.min(axis=0)
            ymax, xmax = nonzero.max(axis=0)
            bgra = bgra[ymin:ymax+1, xmin:xmax+1]

        cv2.imwrite(output_path, bgra)
        print(f"✓ Avatar sin fondo procesado (colores reales): {output_path} ({bgra.shape})")
        return output_path
    except Exception as e:
        print(f"⚠️ Error procesando avatar ({e}), guardando básico...")
        cv2.imwrite(output_path, img)
        return output_path


def process_sensibilidad(sensi_path: str = SENSIBILIDAD_PATH, output_path: str = PROCESSED_SENSIBILIDAD) -> str:
    """
    Recorta únicamente el panel de controles de sensibilidad (sliders derechos).
    """
    if not os.path.exists(sensi_path):
        print(f"❌ Sensibilidad no encontrada: {sensi_path}")
        return sensi_path

    im = Image.open(sensi_path)
    W, H = im.size

    # Recortar panel derecho (sensibilidad sliders): X: 44%-94%, Y: 8%-92%
    box = (int(W * 0.44), int(H * 0.08), int(W * 0.94), int(H * 0.92))
    cropped = im.crop(box)
    cropped.save(output_path, "PNG")
    print(f"✓ Sensibilidad recortada: {output_path} ({cropped.size})")
    return output_path


def prepare_assets() -> dict:
    """
    Garantiza que existan avatar_cutout.png y sensibilidad_cropped.png.
    """
    os.makedirs(ASSETS_DIR, exist_ok=True)

    avatar_out = PROCESSED_AVATAR if os.path.exists(PROCESSED_AVATAR) else process_avatar()
    sensi_out = PROCESSED_SENSIBILIDAD if os.path.exists(PROCESSED_SENSIBILIDAD) else process_sensibilidad()

    return {
        "avatar_cutout": avatar_out,
        "sensibilidad_cropped": sensi_out,
    }


if __name__ == "__main__":
    prepare_assets()
