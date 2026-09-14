#!/usr/bin/env python3
"""
Prepare a portrait photo for clean ASCII conversion:
  1. Remove the background (rembg) so the subject is isolated (fallback to PIL autocontrast if rembg not present)
  2. Boost LOCAL contrast (CLAHE) so a flatly-lit face gains highlights and shadows
  3. Composite the subject onto pure white so the background reads as blank (white -> spaces in the ascii ramp)

Output: source-prepped.png (grayscale), consumed by make_ascii_svg.py.
Run once whenever the source photo changes; the ascii SVG itself is static.

    python scripts/prep_photo.py [input.jpg] [output.png]
"""
import os
import sys
from PIL import Image, ImageEnhance, ImageOps
import numpy as np

try:
    import cv2
    from rembg import remove
    HAS_CV_REMBG = True
except ImportError:
    HAS_CV_REMBG = False

HERE = os.path.dirname(os.path.abspath(__file__))
INP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "source-photo.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "source-prepped.png")

if not os.path.exists(INP):
    print(f"Error: Source image not found at {INP}", file=sys.stderr)
    sys.exit(1)

if HAS_CV_REMBG:
    print("Using rembg + OpenCV CLAHE pipeline...")
    # 1. cut out the subject
    cut = remove(Image.open(INP).convert("RGBA"))
    rgb = np.array(cut.convert("RGB"))
    alpha = np.array(cut.split()[-1])  # 0 = background

    # 2. local-contrast the luminance (CLAHE)
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.6, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    # a touch of global lift so the face sits in the sparse end of the ramp
    gray = cv2.convertScaleAbs(gray, alpha=1.05, beta=18)

    # 3. paste onto white using the alpha mask (feathered a hair to avoid a halo)
    mask = (alpha.astype(np.float32) / 255.0)
    mask = cv2.GaussianBlur(mask, (0, 0), 1.0)
    out = gray.astype(np.float32) * mask + 255.0 * (1.0 - mask)
    out = np.clip(out, 0, 255).astype(np.uint8)

    Image.fromarray(out, mode="L").save(OUT)
    print("wrote", OUT, out.shape)
else:
    print("Notice: rembg / opencv-python not found; running high-contrast Pillow fallback...")
    im = Image.open(INP).convert("RGBA")
    # Check if alpha channel exists
    if im.mode == "RGBA":
        r, g, b, a = im.split()
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=a)
        im = bg.convert("L")
    else:
        im = im.convert("L")

    im = ImageOps.autocontrast(im, cutoff=2)
    im = ImageEnhance.Contrast(im).enhance(1.4)
    im = ImageEnhance.Brightness(im).enhance(1.1)
    im.save(OUT)
    print("wrote", OUT, im.size)
