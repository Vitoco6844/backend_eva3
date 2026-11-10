from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError


def validate_tool_image(file):
    if not file:
        return
    try:
        if file.size > 512 * 1024:
            raise ValidationError("La imagen debe pesar como máximo 512 KiB.")
        position = file.tell()
        try:
            image = Image.open(file)
            if image.format not in ("JPEG", "PNG", "WEBP") or max(image.size) > 4096:
                raise ValidationError(
                    "Usa JPEG, PNG o WebP, hasta 4096 píxeles por lado."
                )
            image.verify()
        finally:
            file.seek(position)
    except (
        OSError,
        ValueError,
        UnidentifiedImageError,
        Image.DecompressionBombError,
    ) as exc:
        raise ValidationError("El archivo no es una imagen válida.") from exc
