from django import forms
from inventory.models import Site


class RentalRequestForm(forms.Form):
    site_name = forms.CharField(label="Nombre de la obra", max_length=140)
    site_address = forms.CharField(label="Dirección de la obra", max_length=250)
    responsible = forms.CharField(label="Responsable de recepción", max_length=140)
    starts_at = forms.DateTimeField(
        label="Inicio previsto",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    ends_at = forms.DateTimeField(
        label="Devolución prevista",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
    )
    notes = forms.CharField(
        label="Observaciones",
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    submit_key = forms.UUIDField(widget=forms.HiddenInput)


class FulfillRequestForm(forms.Form):
    site = forms.ModelChoiceField(
        label="Obra operativa de destino", queryset=Site.objects.filter(active=True)
    )
    responsible = forms.CharField(
        label="Responsable que firma la entrega", max_length=140
    )
    due_at = forms.DateTimeField(
        label="Devolución acordada",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
        ),
    )
    signature = forms.CharField(widget=forms.HiddenInput, max_length=350000)
    quote = forms.CharField(widget=forms.HiddenInput)


class RejectRequestForm(forms.Form):
    reason = forms.CharField(
        label="Motivo del rechazo", max_length=2000, widget=forms.Textarea
    )
