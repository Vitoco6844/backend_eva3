from pathlib import Path
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from .catalog import public_assets, family_image


def tool_image(request, pk):
    asset = get_object_or_404(public_assets(), pk=pk)
    if asset.image:
        try:
            file = asset.image.open("rb")
            suffix = Path(asset.image.name).suffix.lower()
            mime = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".webp": "image/webp",
            }.get(suffix, "image/png")
            response = FileResponse(file, content_type=mime)
        except OSError:
            response = None
    else:
        response = None
    if response is None:
        path = settings.BASE_DIR / "static/images/tools" / f"{family_image(asset)}.png"
        response = FileResponse(path.open("rb"), content_type="image/png")
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "public, max-age=300"
    return response
