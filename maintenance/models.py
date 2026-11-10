from django.db import models
from django.db.models import Q


class MaintenancePlan(models.Model):
    asset = models.OneToOneField(
        "inventory.Asset",
        on_delete=models.PROTECT,
        related_name="maintenance_plan",
        verbose_name="activo",
    )
    due_at = models.DateTimeField("próxima revisión", null=True, blank=True)
    due_hours = models.DecimalField(
        "umbral de horas acumuladas",
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "plan preventivo"
        constraints = [
            models.CheckConstraint(
                condition=Q(due_at__isnull=False) | Q(due_hours__isnull=False),
                name="plan_requires_limit",
            ),
            models.CheckConstraint(
                condition=Q(due_hours__isnull=True) | Q(due_hours__gte=0),
                name="plan_hours_nonnegative",
            ),
        ]

    def __str__(self):
        return str(self.asset)


class MaintenanceJob(models.Model):
    asset = models.ForeignKey(
        "inventory.Asset", on_delete=models.PROTECT, related_name="maintenance_jobs"
    )
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField()
    finished_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    hours_at_finish = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = "mantenimiento"
        constraints = [
            models.UniqueConstraint(
                fields=["asset"],
                condition=Q(finished_at__isnull=True),
                name="one_active_maintenance",
            )
        ]
