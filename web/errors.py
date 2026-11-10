from django.shortcuts import render
from django.http import JsonResponse


def page_not_found(request, exception):
    if request.path.startswith("/api/"):
        return JsonResponse({"detail": "El recurso solicitado no existe."}, status=404)
    return render(request, "404.html", status=404)
