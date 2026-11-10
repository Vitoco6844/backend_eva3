from django.db import models
from django.core.validators import MinValueValidator


class Named(models.Model):
    name = models.CharField("nombre", max_length=140)
    active = models.BooleanField("activo", default=True)

    class Meta:
        abstract = True
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name


class Contractor(Named):
    tax_id = models.CharField("RUT / identificador", max_length=20, unique=True)
    email = models.EmailField("correo", blank=True)
    phone = models.CharField("teléfono", max_length=30, blank=True)
    manual_block = models.BooleanField("bloqueo manual", default=False)

    class Meta(Named.Meta):
        verbose_name = "contratista"
        verbose_name_plural = "contratistas"


class Site(Named):
    address = models.CharField("dirección", max_length=250)

    class Meta(Named.Meta):
        verbose_name = "obra"


class Warehouse(Named):
    site = models.ForeignKey(Site, on_delete=models.PROTECT, verbose_name="obra")

    class Meta(Named.Meta):
        verbose_name = "bodega"


class Category(Named):
    class Meta(Named.Meta):
        verbose_name = "categoría"


class Asset(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "DISPONIBLE", "Disponible"
        IN_USE = "EN_USO", "En uso"
        MAINTENANCE = "MANTENIMIENTO", "Mantenimiento"
        RETIRED = "BAJA", "Dado de baja"

    code = models.CharField("código", max_length=40, unique=True)
    name = models.CharField("herramienta", max_length=140)
    serial = models.CharField("número de serie", max_length=100, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, verbose_name="categoría"
    )
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, verbose_name="bodega"
    )
    description = models.TextField("descripción", blank=True)
    daily_rate = models.PositiveIntegerField(
        "tarifa diaria CLP", validators=[MinValueValidator(1)]
    )
    usage_hours = models.DecimalField(
        "horas acumuladas",
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        "estado", max_length=15, choices=Status, default=Status.AVAILABLE
    )

    class Meta:
        ordering = ["code"]
        verbose_name = "activo"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(daily_rate__gt=0), name="positive_rate"
            ),
            models.CheckConstraint(
                condition=models.Q(usage_hours__gte=0), name="nonnegative_hours"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["DISPONIBLE", "EN_USO", "MANTENIMIENTO", "BAJA"]
                ),
                name="asset_status_valid",
            ),
        ]

    def __str__(self):
        return f"{self.code} · {self.name}"


class AssetEvent(models.Model):
    asset = models.ForeignKey(Asset, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    at = models.DateTimeField(auto_now_add=True)
    kind = models.CharField(max_length=40)
    previous_status = models.CharField(max_length=15, blank=True)
    new_status = models.CharField(max_length=15)
    origin = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="+", null=True
    )
    destination = models.ForeignKey(
        Warehouse, on_delete=models.PROTECT, related_name="+", null=True
    )
    reason = models.TextField()

    class Meta:
        ordering = ["-at", "-pk"]
        verbose_name = "movimiento de activo"
