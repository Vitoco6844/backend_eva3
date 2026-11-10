from django.db import models
from django.db.models import Q, F


class RentalRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDIENTE", "Pendiente de revisión"
        APPROVED = "APROBADA", "Aprobada: pendiente de pago"
        PAID = "PAGADA", "Pagada: pendiente de entrega"
        FULFILLED = "ENTREGADA", "Entregada"
        REJECTED = "RECHAZADA", "Rechazada"
        CANCELLED = "CANCELADA", "Cancelada"

    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="rental_requests"
    )
    contractor = models.ForeignKey(
        "inventory.Contractor", on_delete=models.PROTECT, related_name="rental_requests"
    )
    site_name = models.CharField("obra solicitada", max_length=140)
    site_address = models.CharField("dirección de la obra", max_length=250)
    responsible = models.CharField("responsable", max_length=140)
    starts_at = models.DateTimeField("inicio previsto")
    ends_at = models.DateTimeField("devolución prevista")
    notes = models.TextField("observaciones", blank=True, max_length=2000)
    estimated_amount = models.PositiveBigIntegerField("estimación CLP")
    submit_key = models.UUIDField(editable=False)
    fingerprint = models.CharField(max_length=64, editable=False)
    status = models.CharField(
        "estado", max_length=12, choices=Status, default=Status.PENDING
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    approved_site = models.ForeignKey(
        "inventory.Site",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    approved_amount = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    resolution_reason = models.TextField("motivo", blank=True)
    loan = models.OneToOneField(
        "rentals.Loan",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="source_request",
    )

    class Meta:
        ordering = ["-pk"]
        verbose_name = "solicitud de alquiler"
        verbose_name_plural = "solicitudes de alquiler"
        constraints = [
            models.UniqueConstraint(
                fields=["requested_by", "submit_key"], name="request_submit_key_unique"
            ),
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")), name="request_dates_valid"
            ),
            models.CheckConstraint(
                condition=Q(estimated_amount__gt=0), name="request_estimate_positive"
            ),
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "PENDIENTE",
                        "APROBADA",
                        "PAGADA",
                        "ENTREGADA",
                        "RECHAZADA",
                        "CANCELADA",
                    ]
                ),
                name="request_status_valid",
            ),
        ]

    def __str__(self):
        return f"Solicitud #{self.pk} · {self.contractor}"

    @property
    def is_expired(self):
        from django.utils import timezone

        return self.status == self.Status.PENDING and self.ends_at <= timezone.now()

    @property
    def display_status(self):
        return "Plazo vencido" if self.is_expired else self.get_status_display()


class RentalRequestItem(models.Model):
    request = models.ForeignKey(
        RentalRequest, on_delete=models.PROTECT, related_name="items"
    )
    asset = models.ForeignKey(
        "inventory.Asset", on_delete=models.PROTECT, related_name="rental_requests"
    )
    estimated_daily_rate = models.PositiveIntegerField("tarifa diaria estimada")
    approved_daily_rate = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["pk"]
        verbose_name = "herramienta solicitada"
        constraints = [
            models.UniqueConstraint(
                fields=["request", "asset"], name="request_asset_unique"
            ),
            models.CheckConstraint(
                condition=Q(estimated_daily_rate__gt=0),
                name="request_item_rate_positive",
            ),
        ]


class AssetHold(models.Model):
    request = models.ForeignKey(
        RentalRequest, on_delete=models.PROTECT, related_name="holds"
    )
    asset = models.OneToOneField(
        "inventory.Asset", on_delete=models.PROTECT, related_name="rental_hold"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "retención de herramienta"
