from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction, IntegrityError
from .models import User
from .identity import validate_rut, normalize_tax_id, tax_id_expression
from inventory.models import Contractor


def register_customer(
    *, username, first_name, last_name, email, tax_id, company_name, phone, password
):
    tax_id = validate_rut(tax_id)
    email = email.strip().lower()
    if not email:
        raise ValidationError("Ingresa tu correo electrónico.")
    if (
        Contractor.objects.annotate(identity=tax_id_expression())
        .filter(identity=normalize_tax_id(tax_id))
        .exists()
    ):
        raise ValidationError(
            "La identificación ya está registrada. Ingresa con tu cuenta o contacta a administración."
        )
    user = User(
        username=username.strip(),
        first_name=first_name.strip(),
        last_name=last_name.strip(),
        email=email,
        role="CONTRATISTA",
        is_staff=False,
        is_superuser=False,
    )
    validate_password(password, user)
    user.set_password(password)
    user.full_clean()
    contractor = Contractor(
        name=company_name.strip(), tax_id=tax_id, email=email, phone=phone.strip()
    )
    contractor.full_clean()
    try:
        with transaction.atomic():
            contractor.save()
            user.contractor = contractor
            user.save()
    except IntegrityError as exc:
        raise ValidationError(
            "El usuario, correo o identificación ya está registrado. Ingresa o contacta a administración."
        ) from exc
    return user
