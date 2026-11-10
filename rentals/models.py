from django.db import models
from django.db.models import Q


class Loan(models.Model):
    contractor = models.ForeignKey(
        "inventory.Contractor", on_delete=models.PROTECT, verbose_name="contratista"
    )
    site = models.ForeignKey(
        "inventory.Site", on_delete=models.PROTECT, verbose_name="obra"
    )
    responsible = models.CharField("responsable", max_length=140)
    issued_at = models.DateTimeField("entrega")
    due_at = models.DateTimeField("vencimiento")
    closed_at = models.DateTimeField("cierre", null=True, blank=True)
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT)

    class Meta:
        ordering = ["-pk"]
        verbose_name = "préstamo"
        constraints = [
            models.CheckConstraint(
                condition=Q(due_at__gt=models.F("issued_at")),
                name="loan_due_after_issue",
            )
        ]

    def __str__(self):
        return f"Préstamo #{self.pk} · {self.contractor}"


class Signature(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="signatures")
    kind = models.CharField(
        max_length=12, choices=[("ENTREGA", "Entrega"), ("DEVOLUCION", "Devolución")]
    )
    name = models.CharField(max_length=140)
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    at = models.DateTimeField(auto_now_add=True)
    image = models.BinaryField()
    digest = models.CharField(max_length=64)

    class Meta:
        verbose_name = "firma de documento"


class LoanItem(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, related_name="items")
    asset = models.ForeignKey(
        "inventory.Asset", on_delete=models.PROTECT, related_name="loan_items"
    )
    daily_rate = models.PositiveIntegerField()
    returned_at = models.DateTimeField(null=True, blank=True)
    usage_hours = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    damaged = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    return_signature = models.ForeignKey(
        Signature, on_delete=models.PROTECT, null=True, blank=True, related_name="items"
    )

    class Meta:
        verbose_name = "línea de préstamo"
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=Q(returned_at__isnull=True),
                name="one_open_loan_per_asset",
            ),
            models.UniqueConstraint(
                fields=["loan", "asset"], name="one_asset_per_loan"
            ),
            models.CheckConstraint(
                condition=Q(usage_hours__isnull=True) | Q(usage_hours__gte=0),
                name="return_hours_nonnegative",
            ),
        ]


class OverdueAlert(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "alerta de morosidad"
        constraints = [
            models.UniqueConstraint(
                fields=["loan"],
                condition=Q(resolved_at__isnull=True),
                name="one_open_alert",
            )
        ]
