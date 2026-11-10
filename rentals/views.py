from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from accounts.permissions import require_operator, contractor_scope
from .models import Loan
from .serializers import LoanSerializer, IssueSerializer, ReturnSerializer
from .services import issue_loan, return_items


class LoanViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = LoanSerializer

    def get_queryset(self):
        return contractor_scope(
            self.request.user,
            Loan.objects.select_related("contractor", "site").prefetch_related(
                "items__asset"
            ),
        )

    def create(self, request):
        require_operator(request.user)
        form = IssueSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        from django.shortcuts import get_object_or_404
        from .models import RentalRequest
        from .request_services import fulfill_request

        data = form.validated_data.copy()
        req = get_object_or_404(RentalRequest, pk=data.pop("request_id"))
        loan = fulfill_request(request_id=req.pk, actor=request.user, **data)
        return Response(LoanSerializer(loan).data, status=201)

    @action(detail=True, methods=["post"], url_path="return")
    def return_tools(self, request, pk=None):
        require_operator(request.user)
        loan = self.get_object()
        form = ReturnSerializer(data=request.data)
        form.is_valid(raise_exception=True)
        return Response(
            LoanSerializer(
                return_items(loan_id=loan.pk, actor=request.user, **form.validated_data)
            ).data
        )
