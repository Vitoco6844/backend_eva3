from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from .identity import validate_rut


class CustomerRegistrationForm(UserCreationForm):
    first_name = forms.CharField(label="Nombre del responsable", max_length=150)
    last_name = forms.CharField(label="Apellido", max_length=150)
    email = forms.EmailField(label="Correo electrónico")
    tax_id = forms.CharField(
        label="RUT personal o de la empresa",
        max_length=20,
        help_text="Usa tu RUT si arriendas a tu nombre, o el de tu empresa.",
    )
    company_name = forms.CharField(label="Nombre o razón social", max_length=140)
    phone = forms.CharField(label="Teléfono de contacto", max_length=30)

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "tax_id",
            "company_name",
            "phone",
            "password1",
            "password2",
        )

    def clean_tax_id(self):
        return validate_rut(self.cleaned_data["tax_id"])

    def clean(self):
        data = super().clean()
        if any(
            key in self.data
            for key in (
                "role",
                "is_staff",
                "is_superuser",
                "contractor",
                "contractor_id",
            )
        ):
            raise forms.ValidationError(
                "El registro público solo permite cuentas de cliente."
            )
        return data
