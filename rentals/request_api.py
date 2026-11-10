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

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        from .approval_services import approve_request
        from inventory.models import Site
        from .request_serializers import SubmitRequestSerializer

        require_operator(request.user)

        class Input(serializers.Serializer):
            site_id = serializers.PrimaryKeyRelatedField(
                queryset=Site.objects.filter(active=True)
            )
            quote = serializers.CharField()

            def to_internal_value(self, data):
                unknown = set(data) - set(self.fields)
                if unknown:
                    raise serializers.ValidationError(
                        {key: "Campo no permitido." for key in unknown}
                    )
                return super().to_internal_value(data)

        form = Input(data=request.data)
        form.is_valid(raise_exception=True)
        req = approve_request(
            request_id=self.get_object().pk,
            site_id=form.validated_data["site_id"].pk,
            quote=form.validated_data["quote"],
            actor=request.user,
        )
        return Response(self.get_serializer(req).data)

    @action(detail=True, methods=["get"], url_path="approval-quote")
    def approval_summary(self, request, pk=None):
        from .approval_services import approval_quote

        require_operator(request.user)
        return Response({"quote": approval_quote(self.get_object(), request.user)})

    @action(detail=True, methods=["post"])
    def fulfill(self, request, pk=None):
        require_operator(request.user)
        req = self.get_object()
        form = FulfillSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        data = form.validated_data.copy()
        loan = fulfill_request(request_id=req.pk, actor=request.user, **data)
        return Response({"loan": loan.pk, "url": f"/rentals/{loan.pk}/"})
