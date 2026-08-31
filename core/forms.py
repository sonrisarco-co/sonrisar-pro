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

    MOTIVOS_NOMBRES = [
        "Consulta / diagnóstico",
        "Limpieza",
        "Resina",
        "Ajuste (ortodoncia)",
        "Segunda colocación + ajuste",
        "Segunda colocación",
        "Colocación nueva",
        "Provisorio",
        "Contenciones",
        "Placa NMR",
        "Control",
        "Corona",
        "Puente fijo",
        "Despegados",
        "Blanqueamiento",
        "Retiro de brackets",
        "Ajuste + limpieza",
        "Endodoncia",
        "Extracción",
        "Prótesis",
        "Urgencia",
    ]

    MOTIVOS = [(nombre, nombre) for nombre in MOTIVOS_NOMBRES]

    motivo = forms.CharField(
        required=False,
        widget=forms.HiddenInput()
    )

    procedimientos = forms.ModelMultipleChoiceField(
        queryset=Procedure.objects.all().order_by("nombre"),
        required=True,
        error_messages={
            "required": "Seleccioná al menos un motivo para la cita.",
        },
        widget=forms.CheckboxSelectMultiple(attrs={
            "class": "motivo-grid",
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

        # Mantiene Motivo principal y Procedimientos adicionales con
        # exactamente las mismas opciones, sin requerir migraciones.
        for nombre in self.MOTIVOS_NOMBRES:
            Procedure.objects.get_or_create(nombre=nombre)

        self.fields["procedimientos"].queryset = (
            Procedure.objects
            .filter(nombre__in=self.MOTIVOS_NOMBRES)
            .order_by("nombre")
        )

        if (
            not self.is_bound
            and self.instance
            and self.instance.pk
            and not self.instance.procedimientos.exists()
            and self.instance.motivo
        ):
            procedimiento = self.fields["procedimientos"].queryset.filter(
                nombre=self.instance.motivo
            ).first()
            if procedimiento:
                self.initial["procedimientos"] = [procedimiento.pk]

        self.fields["fecha"].input_formats = ["%Y-%m-%d"]
        self.fields["hora"].input_formats = ["%H:%M", "%H:%M:%S"]

    def clean(self):
        cleaned_data = super().clean()
        motivos_seleccionados = cleaned_data.get("procedimientos")

        # Conserva un motivo de referencia para colores y pantallas antiguas;
        # la relación de procedimientos guarda la selección completa.
        if motivos_seleccionados:
            cleaned_data["motivo"] = motivos_seleccionados[0].nombre

        return cleaned_data



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
    TRABAJOS_POR_TIPO = {
        "removible": [
            ("protesis_completa", "Prótesis completa"),
            ("parcial_cromo", "Prótesis parcial cromo"),
            ("parcial_acrilica", "Prótesis parcial acrílica"),
            ("protesis_flexible", "Prótesis flexible"),
            ("provisorio_placa", "Provisorio a placa"),
        ],
        "fija": [
            ("corona_unitaria", "Corona unitaria"),
            ("puente_fijo", "Puente fijo"),
            ("jacket", "Jacket"),
            ("perno_munon", "Perno muñón"),
            ("incrustacion", "Incrustación"),
            ("provisorio_fijo", "Provisorio fijo"),
        ],
        "ortodoncia": [
            ("contencion", "Contención"),
            ("placa_neuromiorrelajante", "Placa neuromiorrelajante"),
        ],
        "reparacion": [
            ("reparacion", "Reparación"),
            ("rebase", "Rebase"),
            ("agregado_diente", "Agregado de diente"),
            ("agregado_gancho", "Agregado de gancho"),
        ],
        "otro": [
            ("otro", "Otro trabajo"),
        ],
    }

    trabajo = forms.ChoiceField(
        label="Trabajo principal",
        required=True,
        choices=[("", "Primero seleccioná el tipo de prótesis")],
        widget=forms.Select(attrs={
            "class": "form-select",
            "data-current": "",
        }),
    )

    class Meta:
        model = Prosthesis
        fields = [
            "paciente",
            "tipo_protesis",
            "trabajo",
            "color",
            "fecha_inicio",
            "monto_total",
            "estado",
            "fecha_retorno",
            "observaciones",
        ]

        widgets = {
            "paciente": forms.Select(attrs={
                "class": "form-select paciente-search",
            }),
            "tipo_protesis": forms.Select(attrs={
                "class": "form-select",
            }),
            "color": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ej.: A2, A3, B1...",
            }),
            "fecha_inicio": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
            "monto_total": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "Monto total de la prótesis",
            }),
            "estado": forms.Select(attrs={
                "class": "form-select",
            }),
            "fecha_retorno": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Indicaciones, detalles o información importante del trabajo...",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["paciente"].queryset = Patient.objects.all().order_by(
            "apellido",
            "nombre",
        )

        tipo = ""
        if self.is_bound:
            tipo = (self.data.get("tipo_protesis") or "").strip()
        elif self.instance and self.instance.pk:
            tipo = (self.instance.tipo_protesis or "").strip()
        else:
            tipo = (
                self.initial.get("tipo_protesis")
                or self.fields["tipo_protesis"].initial
                or ""
            )

        trabajo_actual = ""
        if self.is_bound:
            trabajo_actual = (self.data.get("trabajo") or "").strip()
        elif self.instance and self.instance.pk:
            trabajo_actual = (self.instance.trabajo or "").strip()
        else:
            trabajo_actual = (self.initial.get("trabajo") or "").strip()

        opciones = list(self.TRABAJOS_POR_TIPO.get(tipo, []))

        # Conserva trabajos históricos aunque no estén en la lista nueva.
        valores_disponibles = {valor for valor, _ in opciones}
        if trabajo_actual and trabajo_actual not in valores_disponibles:
            opciones.append((trabajo_actual, trabajo_actual))

        if opciones:
            self.fields["trabajo"].choices = [
                ("", "Seleccionar trabajo principal"),
                *opciones,
            ]
        else:
            self.fields["trabajo"].choices = [
                ("", "Primero seleccioná el tipo de prótesis"),
            ]

        self.fields["trabajo"].widget.attrs["data-current"] = trabajo_actual

        self.fields["fecha_inicio"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_retorno"].input_formats = ["%Y-%m-%d"]

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo_protesis")
        trabajo = cleaned_data.get("trabajo")

        if not tipo or not trabajo:
            return cleaned_data

        opciones_validas = {
            valor for valor, _ in self.TRABAJOS_POR_TIPO.get(tipo, [])
        }

        # En edición se permite conservar un valor histórico ya guardado.
        trabajo_historico = ""
        if self.instance and self.instance.pk:
            trabajo_historico = (self.instance.trabajo or "").strip()

        if trabajo not in opciones_validas and trabajo != trabajo_historico:
            self.add_error(
                "trabajo",
                "El trabajo seleccionado no corresponde al tipo de prótesis.",
            )

        return cleaned_data


# -------------------------
# ORDEN DE LABORATORIO
# -------------------------

class OrdenLaboratorioForm(forms.ModelForm):
    class Meta:
        model = OrdenLaboratorio
        exclude = (
            "protesis",
            "fecha",
            # Campos antiguos que se conservan solo por compatibilidad.
            "protesis_completa_sup", "protesis_completa_inf",
            "protesis_parcial", "protesis_parcial_sup", "protesis_parcial_inf",
            "protesis_flexible_sup", "protesis_flexible_inf",
            "cromo", "cromo_sup", "cromo_inf",
            "provisorio_placa_sup", "provisorio_placa_inf",
            "cubeta_individual", "placa_articular", "enfilado", "terminacion",
            "removible_otros", "removible_otros_texto",
            "corona",
            "contencion_sup", "contencion_inf",
            "placa_relajacion_sup", "placa_relajacion_inf",
            "ortodoncia_otros", "ortodoncia_otros_texto",
            "impresion_inicial", "impresion_inicial_sup", "impresion_inicial_inf",
            "impresion_definitiva_sup", "impresion_definitiva_inf",
            "modelo", "modelo_sup", "modelo_inf",
            "material_otros", "material_otros_texto",
        )

        widgets = {
            "estado": forms.Select(attrs={"class": "form-select"}),
            "arcada": forms.Select(attrs={"class": "form-select"}),
            "piezas_removible": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: 11, 12, 21"}),
            "piezas_fija": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: 24-26"}),
            "odontologo": forms.TextInput(attrs={"class": "form-control"}),
            "indicaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "fecha_envio": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"}
            ),
            "fecha_entrega_prometida": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"}
            ),
            "hora_entrega_solicitada": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "time",
                    "step": "900",
                },
            ),
            "fecha_recepcion": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "form-check-input"})

        for nombre_fecha in [
            "fecha_envio",
            "fecha_entrega_prometida",
            "fecha_recepcion",
        ]:
            if nombre_fecha in self.fields:
                self.fields[nombre_fecha].input_formats = ["%Y-%m-%d"]

        if "hora_entrega_solicitada" in self.fields:
            self.fields["hora_entrega_solicitada"].input_formats = [
                "%H:%M",
                "%H:%M:%S",
            ]

    def clean(self):
        cleaned = super().clean()
        trabajo_marcado = any(
            cleaned.get(nombre)
            for nombre in [
                "protesis_completa", "parcial_cromo", "parcial_acrilica",
                "protesis_flexible", "provisorio_placa", "reparacion",
                "rebasado", "agregado_diente", "agregado_gancho",
                "corona_unitaria", "puente_fijo", "jacket", "perno_metalico",
                "incrustacion", "provisorio_fijo", "contencion",
                "placa_relajacion",
            ]
        )
        if not trabajo_marcado:
            raise forms.ValidationError("Seleccioná al menos un trabajo solicitado.")
        return cleaned

