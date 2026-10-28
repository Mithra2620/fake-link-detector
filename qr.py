"""Offline QR decoding. Uses zxing-cpp (pip install zxing-cpp), falls back to OpenCV if present."""
from __future__ import annotations

import io


def decode(image_bytes: bytes) -> tuple[list[str], str | None]:
    """Return (decoded_texts, error_message). Never raises."""
    try:
        from PIL import Image, ImageOps
        img = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    except Exception:
        return [], "Could not read that image. Try a clear PNG or JPG."
    try:
        import zxingcpp
        texts = [b.text for b in zxingcpp.read_barcodes(img) if b.text]
        if not texts:  # retry on a grayscale, upscaled copy (helps small/blurry codes)
            g = ImageOps.autocontrast(img.convert("L"))
            texts = [b.text for b in zxingcpp.read_barcodes(g.resize((g.width * 2, g.height * 2))) if b.text]
        return (texts, None) if texts else ([], "No QR code found. Make it bigger, sharper and well lit.")
    except ImportError:
        pass
    except Exception:
        return [], "QR decoding failed on this image. Try another photo."
    try:
        import cv2
        import numpy as np
        ok, texts, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(np.array(img)[:, :, ::-1])
        texts = [t for t in (texts or []) if t] if ok else []
        return (texts, None) if texts else ([], "No QR code found. Make it bigger, sharper and well lit.")
    except ImportError:
        return [], "QR support not installed. Run: pip install zxing-cpp"
    except Exception:
        return [], "QR decoding failed on this image. Try another photo."
