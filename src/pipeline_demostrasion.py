"""
MÓDULO DE DEMOSTRACIÓN – PIPELINE DE PREPROCESAMIENTO CITOLÓGICO
- Normalización de Color de Reinhard (CIE L*a*b*)
- Segmentación y Recorte Seguro (Tissue-Aware Safe Crop)
"""

import numpy as np
import cv2
import random

# ======================================================
# CONSTANTES Y CONFIGURACIÓN DE PREPROCESAMIENTO
# ======================================================

TARGET_MEANS = (145, 128, 128)
TARGET_STDS  = (20, 12, 12)

CHROMA_THR_LOOSE = 6
L_DARK_THR_LOOSE = 245
MIN_TISSUE_AREA = 2500
MIN_TISSUE_FRAC = 0.08
MIN_CROP_SIDE = 160
PAD_EXTRA_FRAC = 0.15


# ======================================================
# 1. NORMALIZACIÓN CROMÁTICA (REINHARD)
# ======================================================

def reinhard_normalize_bgr(src_bgr, target_means=TARGET_MEANS, target_stds=TARGET_STDS):
    """
    Alinea estadísticamente las distribuciones de color de la imagen de entrada
    con una imagen de referencia ideal en el espacio de color CIE L*a*b*, 
    mitigando la variabilidad de tinciones entre diferentes laboratorios.
    """
    src = cv2.cvtColor(src_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    L, A, B = cv2.split(src)

    means = (np.mean(L), np.mean(A), np.mean(B))
    stds  = (np.std(L) + 1e-6, np.std(A) + 1e-6, np.std(B) + 1e-6)

    L = (L - means[0]) / stds[0] * target_stds[0] + target_means[0]
    A = (A - means[1]) / stds[1] * target_stds[1] + target_means[1]
    B = (B - means[2]) / stds[2] * target_stds[2] + target_means[2]

    out = cv2.merge([L, A, B])
    out = np.clip(out, 0, 255).astype(np.uint8)
    out = cv2.cvtColor(out, cv2.COLOR_LAB2BGR)
    return out


# ======================================================
# 2. MÁSCARA DE TEJIDO Y RECORTE SEGURO
# ======================================================

def tissue_mask_lab_loose(rgb):
    """
    Genera una máscara binaria para aislar componentes celulares relevantes 
    y descartar el fondo blanco o artefactos lumínicos del portaobjetos.
    """
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB).astype(np.int16)
    L = lab[:, :, 0]
    a = lab[:, :, 1] - 128
    b = lab[:, :, 2] - 128
    chroma = np.sqrt(a*a + b*b)

    m = (chroma > CHROMA_THR_LOOSE) | (L < L_DARK_THR_LOOSE)
    m = (m.astype(np.uint8) * 255)

    m = cv2.medianBlur(m, 5)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8), iterations=1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=1)

    num, labels, stats, _ = cv2.connectedComponentsWithStats((m > 0).astype(np.uint8), connectivity=8)
    out = np.zeros_like(m, dtype=np.uint8)
    for i in range(1, num):
        area = stats[i, cv2.CC_STAT_AREA]
        if area >= MIN_TISSUE_AREA:
            out[labels == i] = 255

    return (out > 0)


def crop_tissue_aware_safe(rgb):
    """
    Realiza un recorte centrado en el componente celular de mayor relevancia 
    (evitando núcleos sueltos o ruido periférico) y asegura la retención 
    adecuada del citoplasma bajo criterios morfológicos estándar.
    """
    h, w = rgb.shape[:2]
    m = tissue_mask_lab_loose(rgb)

    if int(m.sum()) < MIN_TISSUE_AREA:
        return rgb

    num, labels, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), connectivity=8)
    if num <= 1:
        return rgb

    areas = stats[1:, cv2.CC_STAT_AREA]
    idx = 1 + int(np.argmax(areas))  # Componente principal

    x = stats[idx, cv2.CC_STAT_LEFT]
    y = stats[idx, cv2.CC_STAT_TOP]
    ww = stats[idx, cv2.CC_STAT_WIDTH]
    hh = stats[idx, cv2.CC_STAT_HEIGHT]

    pad = int(PAD_EXTRA_FRAC * max(ww, hh))
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(w, x + ww + pad)
    y2 = min(h, y + hh + pad)

    roi = rgb[y1:y2, x1:x2]
    roi_m = m[y1:y2, x1:x2]

    if min(roi.shape[0], roi.shape[1]) < MIN_CROP_SIDE:
        return rgb

    tissue_frac = float(roi_m.mean())
    if tissue_frac < MIN_TISSUE_FRAC:
        return rgb

    return roi


# ======================================================
# 3. FUNCIÓN DE PRUEBA / PIPELINE INTEGRADO
# ======================================================

def procesar_imagen_demostracion(ruta_imagen_bgr):
    """
    Ejemplo de flujo de procesamiento unitario para validación visual.
    """
    # 1. Lectura y conversión a RGB
    bgr = cv2.imread(ruta_imagen_bgr)
    if bgr is None:
        raise FileNotFoundError("No se pudo cargar la imagen de prueba.")
    
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    # 2. Normalización Cromática
    bgr_norm = reinhard_normalize_bgr(bgr)
    rgb_norm = cv2.cvtColor(bgr_norm, cv2.COLOR_BGR2RGB)

    # 3. Recorte Seguro Basado en Tejido
    rgb_cropped = crop_tissue_aware_safe(rgb_norm)

    return rgb_cropped


if __name__ == "__main__":
    print("Módulo de preprocesamiento citológico cargado correctamente.")
    print("Arquitectura diseñada para soporte clínico asistido por computadora (CAD).")