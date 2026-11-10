from rest_framework import viewsets, mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import require_operator
from .request_services import (
    visible_requests,
    submit_request,
    cancel_request,
    reject_request,
    fulfill_request,
    delivery_quote,
)
from .request_serializers import (
    RentalRequestSerializer,
    SubmitRequestSerializer,
    FulfillSerializer,
)


class RentalRequestViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = RentalRequestSerializer

    def get_queryset(self):
        return visible_requests(self.request.user)

    def create(self, request):
        form = SubmitRequestSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        req = submit_request(actor=request.user, **form.validated_data)
        return Response(self.get_serializer(req).data, status=201)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        req = cancel_request(request_id=self.get_object().pk, actor=request.user)
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        require_operator(request.user)

        class Input(serializers.Serializer):
            reason = serializers.CharField(max_length=2000)

        form = Input(data=request.data)
        form.is_valid(raise_exception=True)
        req = reject_request(
            request_id=self.get_object().pk, actor=request.user, **form.validated_data
        )
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["get"], url_path="delivery-quote")
    def quote(self, request, pk=None):
        require_operator(request.user)
        req = self.get_object()
        return Response(
            {
                "quote": delivery_quote(req, request.user),
                "rates": [
                    {"asset": line.asset_id, "daily_rate": line.asset.daily_rate}
                    for line in req.items.select_related("asset")
                ],
            }
        )

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        require_operator(request.user)
        req = self.get_object()
        form = FulfillSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data.copy()
        data["site_id"] = data["site_id"].pk
        loan = fulfill_request(request_id=req.pk, actor=request.user, **data)
        return Response({"loan": loan.pk, "url": f"/rentals/{loan.pk}/"})
