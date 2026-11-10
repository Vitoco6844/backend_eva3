from django import forms
from inventory.models import Contractor, Site, Warehouse, Asset
from maintenance.models import MaintenancePlan


class SignatureMixin(forms.Form):
    signature = forms.CharField(widget=forms.HiddenInput, max_length=350000)


class IssueForm(SignatureMixin):
    contractor = forms.ModelChoiceField(
        label="Contratista",
        queryset=Contractor.objects.filter(active=True, manual_block=False),
    )
    site = forms.ModelChoiceField(
        label="Obra de destino", queryset=Site.objects.filter(active=True)
    )
    responsible = forms.CharField(
        label="Nombre del responsable que firma", max_length=140
    )
    due_at = forms.DateTimeField(
        label="Devolución prevista",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    assets = forms.ModelMultipleChoiceField(
        label="Herramientas disponibles",
        queryset=Asset.objects.filter(status="DISPONIBLE"),
        widget=forms.CheckboxSelectMultiple,
    )


class ReturnForm(SignatureMixin):
    def __init__(self, *args, loan, **kwargs):
        super().__init__(*args, **kwargs)
        for line in loan.items.filter(returned_at=None).select_related("asset"):
            self.fields[f"select_{line.pk}"] = forms.BooleanField(
                label=str(line.asset), required=False
            )
            self.fields[f"hours_{line.pk}"] = forms.DecimalField(
                label="Horas utilizadas en este préstamo",
                min_value=0,
                max_digits=12,
                decimal_places=2,
                required=False,
                initial=0,
            )
            self.fields[f"damaged_{line.pk}"] = forms.BooleanField(
                label="Requiere revisión por daño", required=False
            )
            self.fields[f"notes_{line.pk}"] = forms.CharField(
                label="Observaciones", required=False, max_length=2000
            )


class StartForm(forms.Form):
    asset = forms.ModelChoiceField(
        label="Herramienta a revisar",
        queryset=Asset.objects.filter(status__in=["DISPONIBLE", "MANTENIMIENTO"]),
    )
    notes = forms.CharField(
        label="Trabajo a realizar", widget=forms.Textarea, max_length=2000
    )


class FinishForm(forms.Form):
    notes = forms.CharField(
        label="Trabajo realizado", widget=forms.Textarea, max_length=2000
    )
    next_due_at = forms.DateTimeField(
        label="Próxima revisión por fecha",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}),
        input_formats=["%Y-%m-%dT%H:%M"],
    )
    next_due_hours = forms.DecimalField(
        label="Próximo umbral de horas acumuladas",
        required=False,
        min_value=0,
        max_digits=12,
        decimal_places=2,
    )


class PlanForm(forms.ModelForm):
    class Meta:
        model = MaintenancePlan
        fields = ["asset", "due_at", "due_hours"]
        widgets = {
            "due_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            )
        }


class TransferForm(forms.Form):
    warehouse = forms.ModelChoiceField(
        label="Bodega de destino", queryset=Warehouse.objects.filter(active=True)
    )
    reason = forms.CharField(label="Motivo", widget=forms.Textarea, max_length=1000)


class ReasonForm(forms.Form):
    reason = forms.CharField(
        label="Motivo de la baja", widget=forms.Textarea, max_length=1000
    )
