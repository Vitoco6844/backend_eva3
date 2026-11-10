import uuid
from django.db import models
from django.db.models import Q


class Charge(models.Model):
    loan = models.OneToOneField(
        "rentals.Loan", on_delete=models.PROTECT, related_name="charge"
    )
    amount = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "cargo de alquiler"
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="charge_positive")
        ]

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
