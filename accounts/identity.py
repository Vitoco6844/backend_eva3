import re
from django.core.exceptions import ValidationError
from django.db.models import Value
from django.db.models.functions import Replace, Upper


def normalize_tax_id(value):
    return str(value).strip().upper().replace(".", "").replace(" ", "").replace("-", "")


def tax_id_expression():
    expression = Upper("tax_id")
    for character in (".", " ", "-"):
        expression = Replace(expression, Value(character), Value(""))
    return expression


def validate_rut(value):
    key = normalize_tax_id(value)
    if not re.fullmatch(r"[1-9][0-9]{6,7}[0-9K]", key):
        raise ValidationError(
            "Ingresa un RUT chileno válido con su dígito verificador."
        )
    total = sum(
        int(digit) * (2 + index % 6) for index, digit in enumerate(reversed(key[:-1]))
    )
    check = 11 - total % 11
    expected = "0" if check == 11 else "K" if check == 10 else str(check)
    if key[-1] != expected:
        raise ValidationError("El dígito verificador del RUT no es válido.")
    return key[:-1] + "-" + key[-1]
