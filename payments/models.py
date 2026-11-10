import uuid
from django.db import models
from django.db.models import Q


class Charge(models.Model):
    loan = models.ForeignKey(
        "rentals.Loan",
        on_delete=models.PROTECT,
        related_name="charges",
        null=True,
        blank=True,
    )
    rental_request = models.ForeignKey(
        "rentals.RentalRequest",
        on_delete=models.PROTECT,
        related_name="charges",
        null=True,
        blank=True,
    )
    kind = models.CharField(
        max_length=10,
        choices=[
            ("LEGACY", "Cargo histórico"),
            ("INITIAL", "Período contratado"),
            ("EXTRA", "Tiempo adicional"),
        ],
        default="LEGACY",
    )
    voided_at = models.DateTimeField(null=True, blank=True)
    amount = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "cargo de alquiler"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="charge_positive"),
            models.CheckConstraint(
                condition=(
                    Q(kind="INITIAL", rental_request__isnull=False)
                    | Q(
                        kind__in=["LEGACY", "EXTRA"],
                        rental_request__isnull=True,
                        loan__isnull=False,
                    )
                ),
                name="charge_origin_valid",
            ),
            models.UniqueConstraint(
                fields=["rental_request"],
                condition=Q(kind="INITIAL"),
                name="one_initial_charge",
            ),
            models.UniqueConstraint(
                fields=["loan"], condition=Q(kind="EXTRA"), name="one_extra_charge"
            ),
            models.UniqueConstraint(
                fields=["loan"], condition=Q(kind="LEGACY"), name="one_legacy_charge"
            ),
            models.CheckConstraint(
                condition=Q(voided_at__isnull=True) | Q(paid_at__isnull=True),
                name="paid_charge_not_voided",
            ),
        ]

    @property
    def contractor(self):
        return (
            self.rental_request.contractor
            if self.rental_request_id
            else self.loan.contractor
        )

    @property
    def contractor_id(self):
        return self.contractor.pk

    def __str__(self):
        return f"Cargo #{self.pk} · ${self.amount}"


class PaymentAttempt(models.Model):
    class Status(models.TextChoices):
        CREATING = "CREATING", "Creando"
        PENDING = "PENDING", "Pendiente"
        UNKNOWN = "UNKNOWN", "Por conciliar"
        APPROVED = "APPROVED", "Aprobado"
        REJECTED = "REJECTED", "Rechazado"
        CANCELLED = "CANCELLED", "Cancelado"
        EXPIRED = "EXPIRED", "Expirado"

    charge = models.ForeignKey(
        Charge, on_delete=models.PROTECT, related_name="attempts"
    )
    order = models.CharField(max_length=26, unique=True)
    session_id = models.UUIDField(default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=200, unique=True, null=True, editable=False)
    redirect_url = models.URLField(blank=True)
    amount = models.PositiveBigIntegerField()
    status = models.CharField(max_length=12, choices=Status, default=Status.CREATING)
    response_code = models.IntegerField(null=True, blank=True)
    authorization = models.CharField(max_length=30, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "intento Webpay"
        constraints = [
            models.UniqueConstraint(
                fields=["charge"],
                condition=Q(status__in=["CREATING", "PENDING", "UNKNOWN"]),
                name="one_active_payment",
            )
        ]
