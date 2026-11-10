from django.core.exceptions import (
    ValidationError as DjangoValidationError,
    ObjectDoesNotExist,
)
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError
from rest_framework.views import exception_handler as drf_handler
from rest_framework.response import Response


def exception_handler(exc, context):
    if isinstance(exc, ObjectDoesNotExist):
        return Response({"detail": "El registro solicitado no existe."}, status=404)
    if isinstance(exc, DjangoValidationError):
        return Response(
            {"detail": getattr(exc, "message_dict", None) or exc.messages}, status=400
        )
    if isinstance(exc, (ProtectedError, IntegrityError)):
        return Response(
            {
                "detail": "Operación incompatible con el historial o una operación simultánea. Actualiza y revisa los datos."
            },
            status=409,
        )
    return drf_handler(exc, context)
