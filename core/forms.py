from django import forms
from .models import (
    Patient,
    Appointment,
    Budget,
    Payment,
    Prosthesis,
    OrdenLaboratorio,
    ClinicalRecord,
    Inventory,   # ← ESTE ES EL MODELO CORRECTO DEL INVENTARIO
    InventoryMovement,
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

    MOTIVOS = [
        ("Consulta / diagnóstico", "Consulta / diagnóstico"),
        ("Limpieza", "Limpieza"),
        ("Resina", "Resina"),
        ("Ajuste (ortodoncia)", "Ajuste (ortodoncia)"),
        ("Segunda colocación + ajuste", "Segunda colocación + ajuste"),
        ("Colocación nueva", "Colocación nueva"),
        ("Despegados", "Despegados"),
        ("Blanqueamiento", "Blanqueamiento"),
        ("Retiro de brackets", "Retiro de brackets"),
        ("Ajuste + limpieza", "Ajuste + limpieza"),
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
            "monto_total",
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
            "monto_total": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Monto total del tratamiento",
                "step": "0.01",
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


class InventoryMovementForm(forms.ModelForm):
    class Meta:
        model = InventoryMovement
        fields = ["producto", "tipo", "cantidad", "observacion"]
        widgets = {
            "producto": forms.Select(attrs={
                "class": "form-select"
            }),
            "tipo": forms.Select(attrs={
                "class": "form-select"
            }),
            "cantidad": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "placeholder": "Cantidad"
            }),
            "observacion": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej: Compra Impodent, ajuste de inventario, uso clínico..."
            }),
        }

    def clean_cantidad(self):
        cantidad = self.cleaned_data.get("cantidad")

        if cantidad is None or cantidad <= 0:
            raise forms.ValidationError("La cantidad debe ser mayor a cero.")

        return cantidad



# -------------------------
# HISTORIA CLÍNICA
# -------------------------

class ClinicalRecordForm(forms.ModelForm):
    class Meta:
        model = ClinicalRecord

        fields = [
            # 1 🩺 ANTECEDENTES
            "diabetes",
            "hta",
            "cardiopatia",
            "ninguno",
            "otros_antecedentes",
            "medicacion_actual",
            "alergias",
            "cirugias_previas",

            # 2 📝 MOTIVO
            "motivo",

            # 3 🔍 DIAGNÓSTICO
            "diagnostico",

            # 4 📈 PRONÓSTICO
            "pronostico",

            # 5 🛠️ PLAN DE TRATAMIENTO
            "tratamiento",

            # 6 ✍️ CONSENTIMIENTO
            "consentimiento_explicado",
            "consentimiento_aceptado",
            "consentimiento_firma",

            # 8 📋 EVOLUCIÓN
            "evolucion",
        ]

        widgets = {
            "motivo": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Motivo de consulta"
            }),

            "diagnostico": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Diagnóstico clínico"
            }),

            "tratamiento": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Plan de tratamiento"
            }),

            "evolucion": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 5,
                "placeholder": "Evolución clínica"
            }),

            "otros_antecedentes": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Otros antecedentes"
            }),

            "medicacion_actual": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Medicación actual"
            }),

            "alergias": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Alergias"
            }),

            "cirugias_previas": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Cirugías previas"
            }),

            "pronostico": forms.Select(attrs={
                "class": "form-select"
            }),

            "diabetes": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "hta": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "cardiopatia": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "ninguno": forms.CheckboxInput(attrs={"class": "form-check-input"}),

            "consentimiento_explicado": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "consentimiento_aceptado": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "consentimiento_firma": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        

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
            "tipo_protesis",
            "monto_total",
            "fecha_inicio",
            "etapa",
            "estado",
            "fecha_retorno",
            "observaciones",
        ]

        widgets = {
            "paciente": forms.Select(attrs={
                "class": "form-select paciente-search",
            }),
            "tipo_protesis": forms.Select(attrs={"class": "form-select"}),

            "monto_total": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "placeholder": "Monto total de la prótesis"
            }),

            "fecha_inicio": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            
            "etapa": forms.Select(attrs={"class": "form-select"}),
            "estado": forms.Select(attrs={"class": "form-select"}),

            "fecha_retorno": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),

            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3
            }),
        }


# -------------------------
# ORDEN DE LABORATORIO
# -------------------------

class OrdenLaboratorioForm(forms.ModelForm):
    class Meta:
        model = OrdenLaboratorio
        exclude = ("protesis", "fecha", "estado")

        widgets = {
            "estado": forms.Select(attrs={"class": "form-select"}),

            "removible_otros_texto": forms.TextInput(attrs={"class": "form-control"}),
            "ortodoncia_otros_texto": forms.TextInput(attrs={"class": "form-control"}),
            "material_otros_texto": forms.TextInput(attrs={"class": "form-control"}),

            "indicaciones": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),

            "fecha_envio": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_entrega_prometida": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "fecha_recepcion": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        }

