from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps
from telegram import InputFile


def compress_to_bytes(
    image_bytes: bytes,
    *,
    max_side: int = 1280,
    quality: int = 75,
    image_format: str = "WEBP",
    optimize: bool = True,
) -> bytes:
    """
    Compress image bytes and return the resulting bytes.
    Supported formats: WEBP, JPEG.
    """
    if not image_bytes:
        raise ValueError("image_bytes is empty")

    fmt = (image_format or "WEBP").upper()
    if fmt not in {"WEBP", "JPEG"}:
        raise ValueError(f"Unsupported image_format: {image_format}")

    with Image.open(BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)

        if max_side and max(image.size) > max_side:
            resample = (
                Image.Resampling.LANCZOS
                if hasattr(Image, "Resampling")
                else Image.LANCZOS
            )
            image.thumbnail((max_side, max_side), resample=resample)

        has_alpha = "A" in image.getbands()
        if fmt == "JPEG":
            if has_alpha:
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1])
                image = background
            else:
                image = image.convert("RGB")
        else:
            image = image.convert("RGBA" if has_alpha else "RGB")

        output = BytesIO()
        save_kwargs = {"format": fmt, "quality": quality}
        if fmt == "WEBP":
            save_kwargs["method"] = 6
        if fmt == "JPEG":
            save_kwargs["optimize"] = optimize
            save_kwargs["progressive"] = True

        image.save(output, **save_kwargs)
        return output.getvalue()


def bytes_to_input_file(image_bytes: bytes, filename: str = "report.webp") -> InputFile:
    if not image_bytes:
        raise ValueError("image_bytes is empty")
    buffer = BytesIO()
    buffer.write(image_bytes)
    buffer.seek(0)
    return InputFile(buffer, filename=filename)
