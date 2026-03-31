from django import forms
from .models import (
    Patient,
    Appointment,
    Budget,
    Payment,
    Prosthesis,
    ClinicalRecord,
    Inventory,   # ← ESTE ES EL MODELO CORRECTO DEL INVENTARIO
    RayosX,
    Procedure,
)

# -------------------------
# PACIENTES
# -------------------------

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            "nombre",
            "apellido",
            "ci",
            "fecha_nacimiento",
            "telefono",
            "email",
            "direccion",
        ]

        widgets = {
            "nombre": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "apellido": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "ci": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "fecha_nacimiento": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "telefono": forms.TextInput(attrs={
                "class": "form-control"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control"
            }),
            "direccion": forms.TextInput(attrs={
                "class": "form-control"
            }),
        }



# -------------------------
# CITAS (AQUÍ SE AGREGA EL DATE Y TIME SELECTOR)
# -------------------------

class AppointmentForm(forms.ModelForm):
    paciente = forms.ModelChoiceField(
        queryset=Patient.objects.all().order_by("apellido", "nombre"),
        empty_label="Buscar paciente...",
        widget=forms.Select(attrs={
            "class": "form-select",
        })
    )

    # --- MOTIVOS POR COLOR ---
    MOTIVOS = [
        ("Consulta / diagnóstico", "Consulta / diagnóstico"),
        ("Limpieza", "Limpieza"),
        ("Resina", "Resina"),
        ("Ajuste (ortodoncia)", "Ajuste (ortodoncia)"),
        ("Segunda colocación + ajuste", "Segunda colocación + ajuste"),
        ("Colocación nueva", "Colocación nueva"),
        ("Endodoncia", "Endodoncia"),
        ("Extracción", "Extracción"),
        ("Prótesis", "Prótesis"),
        ("Urgencia", "Urgencia"),
    ]

    motivo = forms.ChoiceField(
        choices=MOTIVOS,
        widget=forms.Select(attrs={
            "class": "form-select motivo-color"
        })
    )

    procedimientos = forms.ModelMultipleChoiceField(
        queryset=Procedure.objects.all().order_by("nombre"),
        required=False,
        widget=forms.SelectMultiple(attrs={
            "class": "form-select",
            "size": "6",
        })
    )

    class Meta:
        model = Appointment
        fields = [
            "paciente",
            "fecha",
            "hora",
            "motivo",
            "procedimientos",
            "estado",
            "observaciones",
        ]
        widgets = {
            "fecha": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "hora": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "type": "time",
                    "class": "form-control",
                }
            ),
            "estado": forms.Select(attrs={"class": "form-select"}),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.paciente_id:
            self.fields["paciente"].initial = self.instance.paciente_id

        self.fields["paciente"].widget.attrs["data-initial"] = (
            self.instance.paciente_id if self.instance.pk else ""
        )

        self.fields["procedimientos"].queryset = Procedure.objects.all().order_by("nombre")

        # 🔹 IMPORTANTE: formatos que el navegador entiende
        self.fields["fecha"].input_formats = ["%Y-%m-%d"]
        self.fields["hora"].input_formats = ["%H:%M", "%H:%M:%S"]



# -------------------------
# PRESUPUESTOS
# -------------------------
class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["paciente", "diagnostico", "observaciones"]

        widgets = {
            "paciente": forms.Select(attrs={"class": "form-control"}),
            "diagnostico": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


from .models import BudgetPayment


class BudgetPaymentForm(forms.ModelForm):
    class Meta:
        model = BudgetPayment
        fields = ["monto", "metodo_pago", "tipo", "observacion"]
        widgets = {
            "monto": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "Monto"
            }),
            "metodo_pago": forms.Select(attrs={
                "class": "form-control"
            }),
            "tipo": forms.Select(attrs={
                "class": "form-control"
            }),
            "observacion": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Observación"
            }),
        }


# -------------------------
# PAGOS
# -------------------------
class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        exclude = ("fecha",)   # ❗ Campo que NO se puede editar
        widgets = {
            "paciente": forms.Select(attrs={"class": "form-control"}),
            "presupuesto": forms.Select(attrs={"class": "form-control"}),
            "monto": forms.NumberInput(attrs={"class": "form-control"}),
            "metodo": forms.Select(attrs={"class": "form-control"}),
            "fecha": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
        }

# -------------------------
# INVENTARIO
# -------------------------

class InventoryForm(forms.ModelForm):
    class Meta:
        model = Inventory
        fields = ["codigo", "nombre", "categoria", "proveedor", "stock", "stock_minimo", "precio"]
        widgets = {
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "categoria": forms.TextInput(attrs={"class": "form-control"}),
            "proveedor": forms.TextInput(attrs={"class": "form-control"}),
            "stock": forms.NumberInput(attrs={"class": "form-control"}),
            "stock_minimo": forms.NumberInput(attrs={"class": "form-control"}),
            "precio": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
        }


# -------------------------
# HISTORIA CLÍNICA
# -------------------------
class ClinicalRecordForm(forms.ModelForm):
    class Meta:
        model = ClinicalRecord
        # ⛔ NO incluir patient
        fields = [
            "motivo",
            "diagnostico",
            "tratamiento",
            "observaciones",
        ]
        

class RayosXForm(forms.ModelForm):
    class Meta:
        model = RayosX
        fields = ["imagen", "descripcion"]




# 🦷 FORMULARIO DE PRÓTESIS

class ProsthesisForm(forms.ModelForm):
    class Meta:
        model = Prosthesis
        fields = [
            "paciente",
            "trabajo",
            "etapa",
            "fecha_envio",
            "fecha_retorno",
            "observaciones",
        ]
        widgets = {
            "fecha_envio": forms.DateInput(attrs={"type": "date"}),
            "fecha_retorno": forms.DateInput(attrs={"type": "date"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }




