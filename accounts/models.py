from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.db.models.functions import Lower


class BuildUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra):
        extra["role"] = "ADMIN"
        return super().create_superuser(username, email, password, **extra)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Administrador"
        STORE = "BODEGUERO", "Bodeguero"
        CONTRACTOR = "CONTRATISTA", "Contratista"

    role = models.CharField(max_length=12, choices=Role, default=Role.CONTRACTOR)
    contractor = models.ForeignKey(
        "inventory.Contractor",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name="contratista",
    )
    objects = BuildUserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("username"), name="username_ci"),
            models.CheckConstraint(
                condition=models.Q(role__in=["ADMIN", "BODEGUERO", "CONTRATISTA"]),
                name="user_role_valid",
            ),
        ]
