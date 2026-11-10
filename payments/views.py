from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.core.exceptions import ValidationError
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import PaymentAttempt
from .serializers import ChargeSerializer, PaymentAttemptSerializer
from .services import visible_charges, start_payment, confirm_payment, reconcile_payment


class ChargeViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = ChargeSerializer

    def get_queryset(self):
        return visible_charges(self.request.user)

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        attempt = start_payment(charge_id=self.get_object().pk, actor=request.user)
        return Response(
            {
                "attempt": attempt.pk,
                "status": attempt.status,
                "continue_url": f"/payments/{attempt.charge_id}/continue/",
            },
            status=201,
        )

    @action(detail=True, methods=["post"])
    def reconcile(self, request, pk=None):
        charge = self.get_object()
        attempt = charge.attempts.order_by("-pk").first()
        if not attempt:
            raise ValidationError("No hay intentos registrados.")
        return Response(PaymentAttemptSerializer(reconcile_payment(attempt.pk)).data)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def webpay_return(request):
    data = request.POST if request.method == "POST" else request.GET
    token = data.get("token_ws")
    try:
        if token:
            attempt = confirm_payment(token)
        else:
            # No confiar en que la cancelación del navegador equivale a un rechazo bancario.
            qs = PaymentAttempt.objects.all()
            if data.get("TBK_TOKEN"):
                qs = qs.filter(token=data["TBK_TOKEN"])
            elif data.get("TBK_ORDEN_COMPRA") and data.get("TBK_ID_SESION"):
                qs = qs.filter(
                    order=data["TBK_ORDEN_COMPRA"], session_id=data["TBK_ID_SESION"]
                )
            else:
                return HttpResponseBadRequest("Retorno no reconocido.")
            candidate = qs.first()
            if not candidate:
                return HttpResponseBadRequest("Retorno no reconocido.")
            attempt = reconcile_payment(candidate.pk)
    except (ValidationError, ValueError):
        return HttpResponseBadRequest("Retorno no reconocido.")
    return redirect(f"/payments/{attempt.charge_id}/")
