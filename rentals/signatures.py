import base64, binascii, hashlib, io
from PIL import Image, ImageChops, UnidentifiedImageError
from django.core.exceptions import ValidationError


def validate_signature(value):
    try:
        if (
            not isinstance(value, str)
            or not value.startswith("data:image/png;base64,")
            or len(value) > 350000
        ):
            raise ValueError()
        raw = base64.b64decode(value.split(",", 1)[1], validate=True)
        if not 100 <= len(raw) <= 256 * 1024:
            raise ValueError()
        with Image.open(io.BytesIO(raw)) as image:
            if (
                image.format != "PNG"
                or image.width > 1600
                or image.height > 800
                or image.width < 20
                or image.height < 20
            ):
                raise ValueError()
            image.load()
            background = Image.new("RGBA", image.size, "white")
            background.alpha_composite(image.convert("RGBA"))
            rgb = background.convert("RGB")
            if not ImageChops.difference(
                rgb, Image.new("RGB", rgb.size, "white")
            ).getbbox():
                raise ValueError()
            if len(rgb.getcolors(maxcolors=2) or []) == 1:
                raise ValueError()
    except (
        ValueError,
        binascii.Error,
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ) as exc:
        raise ValidationError(
            "Dibuja una firma válida en el recuadro (PNG, máximo 256 KiB)."
        ) from exc
    return raw, hashlib.sha256(raw).hexdigest()
