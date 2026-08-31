from django.db import models
from django import forms
from django.core.exceptions import ValidationError

# 🧑‍⚕️ PACIENTES
class Patient(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    ci = models.CharField(max_length=30)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    telefono = models.CharField(max_length=50)
    email = models.EmailField(blank=True)
    direccion = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.apellido}, {self.nombre}"


class Procedure(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Procedimiento"
        verbose_name_plural = "Procedimientos"

    def __str__(self):
        return self.nombre


class Appointment(models.Model):
    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("En espera", "En espera"),
        ("confirmado", "Confirmado"),
        ("asistio", "Asistió"),
        ("no_asistio", "No asistió"),
        ("cancelado", "Cancelado"),
    ]

    paciente = models.ForeignKey(Patient, on_delete=models.CASCADE)
    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.CharField(max_length=200)
    procedimientos = models.ManyToManyField(
        Procedure,
        blank=True,
        related_name="appointments",
        verbose_name="Procedimientos"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    pagado = models.BooleanField(default=False)
    observaciones = models.TextField(blank=True)

    # Indica que desde esta cita se guardó/actualizó la Historia Clínica.
    # Es independiente del estado de asistencia de la cita.
    historia_actualizada = models.BooleanField(default=False)

    monto_total = models.DecimalField(
        "Monto total",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=0
    )

    class Meta:
        ordering = ["fecha", "hora"]

    def __str__(self):
        return f"{self.paciente} - {self.fecha} {self.hora}"


# 🚫 BLOQUEO DE DÍAS

class DayBlock(models.Model):
    fecha = models.DateField(unique=True)

    motivo = models.CharField(
        max_length=200,
        default="Día bloqueado"
    )

    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha} - {self.motivo}"


# ⏰ BLOQUEO DE HORARIOS INDIVIDUALES
class TimeBlock(models.Model):
    fecha = models.DateField()
    hora = models.TimeField()
    motivo = models.CharField(
        max_length=200,
        default="Horario bloqueado"
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "hora"]
        constraints = [
            models.UniqueConstraint(
                fields=["fecha", "hora"],
                name="unique_time_block_fecha_hora"
            )
        ]

    def __str__(self):
        return f"{self.fecha} {self.hora.strftime('%H:%M')} - {self.motivo}"




# 📝 RECORDATORIOS DE AGENDA
class AgendaReminder(models.Model):

    PRIORIDADES = [
        ("normal", "Normal"),
        ("importante", "Importante"),
        ("urgente", "Urgente"),
    ]

    fecha = models.DateField()
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    prioridad = models.CharField(
        max_length=20,
        choices=PRIORIDADES,
        default="normal"
    )
    paciente = models.ForeignKey(
        Patient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agenda_recordatorios"
    )
    realizado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["realizado", "fecha", "-id"]
        verbose_name = "Recordatorio de agenda"
        verbose_name_plural = "Recordatorios de agenda"

    def __str__(self):
        return f"{self.fecha} - {self.titulo}"

# 📋 HISTORIA CLÍNICA

class ClinicalRecord(models.Model):
    paciente = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="clinical_records"
    )
    fecha = models.DateField(auto_now_add=True)

    # -------------------------
    # 📝 CLÍNICO BÁSICO
    # -------------------------
    motivo = models.CharField(max_length=200)
    diagnostico = models.TextField(blank=True)

    # 👉 AHORA SOLO PLAN
    tratamiento = models.TextField(blank=True)

    # 👉 NUEVO CAMPO
    evolucion = models.TextField(blank=True)

    observaciones = models.TextField(blank=True)

    # -------------------------
    # 🩺 ANTECEDENTES
    # -------------------------
    diabetes = models.BooleanField(default=False)
    hta = models.BooleanField(default=False)
    cardiopatia = models.BooleanField(default=False)
    ninguno = models.BooleanField(default=False)
    otros_antecedentes = models.CharField(max_length=200, blank=True)

    medicacion_actual = models.TextField(blank=True)
    alergias = models.TextField(blank=True)
    cirugias_previas = models.TextField(blank=True)

    # -------------------------
    # 📈 PRONÓSTICO
    # -------------------------
    PRONOSTICO_CHOICES = [
        ("bueno", "Bueno"),
        ("reservado", "Reservado"),
        ("malo", "Malo"),
    ]
    pronostico = models.CharField(
        max_length=10,
        choices=PRONOSTICO_CHOICES,
        blank=True
    )

    # -------------------------
    # ✍️ CONSENTIMIENTO
    # -------------------------
    consentimiento_explicado = models.BooleanField(default=False)
    consentimiento_aceptado = models.BooleanField(default=False)
    consentimiento_firma = models.BooleanField(default=False)

    def __str__(self):
        return f"Historia {self.paciente} ({self.fecha})"
        

# 📌 AVISOS CLÍNICOS IMPORTANTES DEL PACIENTE
class ClinicalAlert(models.Model):
    paciente = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="clinical_alerts"
    )
    titulo = models.CharField(max_length=200)
    detalle = models.TextField(blank=True)
    fecha_revision = models.DateField(null=True, blank=True)
    realizado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["realizado", "fecha_revision", "-creado"]
        verbose_name = "Aviso clínico"
        verbose_name_plural = "Avisos clínicos"

    def __str__(self):
        return f"{self.paciente} - {self.titulo}"


class OdontogramTooth(models.Model):

    ESTADOS = [
        ("sano", "Sano"),
        ("caries", "Caries"),
        ("obturado", "Obturado"),
        ("corona", "Corona"),
        ("endodoncia", "Endodoncia"),
        ("implante", "Implante"),
        ("extraccion", "Extracción"),
        ("ausente", "Ausente"),
        ("movilidad", "Movilidad"),
    ]

    paciente = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="odontograma"
    )

    numero = models.CharField(max_length=5)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="sano")

    pos_x = models.FloatField(default=0)
    pos_y = models.FloatField(default=0)

    def __str__(self):
        return f"{self.numero} - {self.estado}"


class OdontogramaCara(models.Model):

    CARAS = [
        ("vestibular", "Vestibular"),
        ("mesial", "Mesial"),
        ("distal", "Distal"),
        ("oclusal", "Oclusal / Incisal"),
        ("palatino_lingual", "Palatino / Lingual"),
    ]

    ESTADOS = [
        ("caries", "Caries"),
        ("obturado", "Obturado"),
        ("corona", "Corona"),
        ("endodoncia", "Endodoncia"),
        ("implante", "Implante"),
        ("extraccion", "Extracción indicada"),
        ("ausente", "Ausente"),
        ("sano", "Sano"),
    ]

    paciente = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="odontograma_caras"
    )

    pieza = models.CharField(max_length=5)
    cara = models.CharField(max_length=30, choices=CARAS)
    estado = models.CharField(max_length=30, choices=ESTADOS)

    observacion = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["pieza", "cara"]
        unique_together = ("paciente", "pieza", "cara")

    def __str__(self):
        return f"{self.paciente} - {self.pieza} - {self.cara} - {self.estado}"



# 💰 PRESUPUESTOS
from decimal import Decimal

class Budget(models.Model):
    ESTADO_CHOICES = [
        ("pendiente", "Pendiente"),
        ("confirmado", "Confirmado"),
        ("en_proceso", "En proceso"),
        ("entregado", "Entregado"),
        ("cancelado", "Cancelado"),
    ]

    paciente = models.ForeignKey(Patient, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    diagnostico = models.TextField()
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    observaciones = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="pendiente"
    )

    def __str__(self):
        return f"Presupuesto {self.paciente} - ${self.total}"

    @property
    def total_pagado(self):
        return sum((p.monto for p in self.pagos.all()), Decimal("0.00"))

    @property
    def total_ajustes(self):
        return sum((a.monto for a in self.ajustes.all()), Decimal("0.00"))

    @property
    def total_efectivo(self):
        return max((self.total or Decimal("0.00")) + self.total_ajustes, Decimal("0.00"))

    @property
    def credito_recibido(self):
        return sum((t.monto for t in self.transferencias_recibidas.all()), Decimal("0.00"))

    @property
    def credito_transferido(self):
        return sum((t.monto for t in self.transferencias_enviadas.all()), Decimal("0.00"))

    @property
    def credito_disponible(self):
        disponible = (
            self.total_pagado
            + self.credito_recibido
            - self.total_efectivo
            - self.credito_transferido
        )
        return max(disponible, Decimal("0.00"))

    @property
    def saldo_pendiente(self):
        saldo = self.total_efectivo - self.total_pagado - self.credito_recibido
        return max(saldo, Decimal("0.00"))


class BudgetItem(models.Model):
    presupuesto = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="items")
    concepto = models.CharField(max_length=200)
    cantidad = models.IntegerField(default=1)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    total_item = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.concepto} ({self.cantidad} x {self.valor})"


from django.utils import timezone

class BudgetPayment(models.Model):
    METODO_CHOICES = [
        ("efectivo", "Efectivo"),
        ("transferencia", "Transferencia"),
        ("debito", "Débito"),
        ("credito", "Crédito"),
    ]

    TIPO_CHOICES = [
        ("sena", "Seña"),
        ("pago_parcial", "Pago parcial"),
        ("pago_final", "Pago final"),
    ]

    presupuesto = models.ForeignKey(
        Budget,
        on_delete=models.CASCADE,
        related_name="pagos"
    )
    fecha = models.DateField(default=timezone.now)
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.CharField(
        max_length=30,
        choices=METODO_CHOICES,
        blank=True,
        null=True
    )
    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES,
        default="sena"
    )
    observacion = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Pago {self.monto} - Presupuesto #{self.presupuesto.id}"


class BudgetAdjustment(models.Model):
    presupuesto = models.ForeignKey(
        Budget,
        on_delete=models.PROTECT,
        related_name="ajustes",
    )
    fecha = models.DateField(default=timezone.now)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(max_length=255)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def clean(self):
        super().clean()
        if self.monto is None or self.monto == 0:
            raise ValidationError({"monto": "El ajuste no puede ser cero."})
        total_resultante = (self.presupuesto.total or Decimal("0.00")) + self.monto
        otros = self.presupuesto.ajustes.exclude(pk=self.pk).aggregate(
            total=models.Sum("monto")
        )["total"] or Decimal("0.00")
        total_efectivo_resultante = total_resultante + otros
        if total_efectivo_resultante < 0:
            raise ValidationError({"monto": "El ajuste no puede dejar el presupuesto con total negativo."})
        fondos = self.presupuesto.total_pagado + self.presupuesto.credito_recibido
        if self.presupuesto.credito_transferido > max(
            fondos - total_efectivo_resultante,
            Decimal("0.00"),
        ):
            raise ValidationError({
                "monto": "El ajuste dejaría sin respaldo una transferencia de crédito ya registrada."
            })

    def __str__(self):
        return f"Ajuste {self.monto} - Presupuesto #{self.presupuesto_id}"


class BudgetCreditTransfer(models.Model):
    presupuesto_origen = models.ForeignKey(
        Budget,
        on_delete=models.PROTECT,
        related_name="transferencias_enviadas",
    )
    presupuesto_destino = models.ForeignKey(
        Budget,
        on_delete=models.PROTECT,
        related_name="transferencias_recibidas",
    )
    fecha = models.DateField(default=timezone.now)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(max_length=255)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(monto__gt=0),
                name="budget_credit_transfer_monto_positivo",
            ),
            models.CheckConstraint(
                condition=~models.Q(presupuesto_origen=models.F("presupuesto_destino")),
                name="budget_credit_transfer_presupuestos_distintos",
            ),
        ]

    def clean(self):
        super().clean()
        if self.monto is None or self.monto <= 0:
            raise ValidationError({"monto": "El monto debe ser mayor a cero."})
        if self.presupuesto_origen_id == self.presupuesto_destino_id:
            raise ValidationError("El presupuesto de origen y destino deben ser distintos.")
        if (
            self.presupuesto_origen_id
            and self.presupuesto_destino_id
            and self.presupuesto_origen.paciente_id != self.presupuesto_destino.paciente_id
        ):
            raise ValidationError("Solo se puede transferir crédito entre presupuestos del mismo paciente.")

    def __str__(self):
        return (
            f"Transferencia {self.monto}: presupuesto "
            f"#{self.presupuesto_origen_id} a #{self.presupuesto_destino_id}"
        )
        

# 💳 PAGOS
class Payment(models.Model):
    paciente = models.ForeignKey(Patient, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)
    concepto = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=50, choices=[
        ("efectivo", "Efectivo"),
        ("tarjeta", "Tarjeta"),
        ("transferencia", "Transferencia"),
    ])

    def __str__(self):
        return f"Pago {self.paciente} - ${self.monto}"


# 🦷 PRÓTESIS
class Prosthesis(models.Model):

    TIPOS_PROTESIS = [
        ("removible", "Prótesis removible"),
        ("fija", "Rehabilitación fija"),
        ("ortodoncia", "Ortodoncia y otros"),
        ("reparacion", "Reparación / Rebase"),
        ("otro", "Otro"),
    ]

    ETAPAS_PROTESIS = [
        ("impresion", "Impresión / toma de impresión"),
        ("cubeta", "Cubeta individual"),
        ("rodete", "Rodete / placa articular"),
        ("prueba_dientes", "Prueba de dientes"),
        ("enfilado", "Enfilado"),
        ("terminacion", "Terminación"),
        ("entrega", "Entrega"),
    ]

    ESTADOS_PROTESIS = [
        ("laboratorio", "En laboratorio"),
        ("proceso", "En proceso"),
        ("prueba", "Lista para prueba"),
        ("entrega", "Lista para entrega"),
        ("entregada", "Entregada"),
    ]

    paciente = models.ForeignKey(Patient, on_delete=models.CASCADE)

    tipo_protesis = models.CharField(
        "Tipo de prótesis",
        max_length=50,
        choices=TIPOS_PROTESIS,
        default="otro"
    )

    trabajo = models.CharField(
        "Trabajo solicitado",
        max_length=200,
        blank=True
    )

    color = models.CharField(
        "Color",
        max_length=100,
        blank=True,
        default="",
    )

    monto_total = models.DecimalField(
        "Monto total",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=0
    )

    fecha_inicio = models.DateField(
        "Fecha de inicio / toma de impresión",
        blank=True,
        null=True
    )

    etapa = models.CharField(
        "Etapa actual",
        max_length=50,
        choices=ETAPAS_PROTESIS,
        default="impresion"
    )

    estado = models.CharField(
        "Estado",
        max_length=20,
        choices=ESTADOS_PROTESIS,
        default="laboratorio"
    )

    # Se mantiene para no romper órdenes o pantallas anteriores.
    fecha_envio = models.DateField(blank=True, null=True)
    fecha_retorno = models.DateField(blank=True, null=True)

    observaciones = models.TextField(blank=True)

    @property
    def total_pagado(self):
        import json
        from urllib.request import urlopen
        from urllib.error import URLError, HTTPError
        from django.conf import settings

        cobros_base_url = getattr(
            settings,
            "SONRISAR_COBROS_BASE_URL",
            "http://127.0.0.1:8001"
        ).rstrip("/")

        api_url = (
            f"{cobros_base_url}"
            f"/pagos/api/por-protesis/"
            f"?protesis_id={self.id}"
        )

        try:
            with urlopen(api_url, timeout=4) as response:
                data = json.loads(response.read().decode("utf-8"))

            if data.get("ok"):
                return Decimal(str(data.get("total_pagado", "0")))

        except (URLError, HTTPError, TimeoutError, ValueError, json.JSONDecodeError):
            return Decimal("0.00")

        return Decimal("0.00")


    @property
    def saldo_pendiente(self):
        total = self.monto_total or Decimal("0.00")
        saldo = total - self.total_pagado

        if saldo < Decimal("0.00"):
            return Decimal("0.00")

        return saldo

    def __str__(self):
        return f"{self.get_tipo_protesis_display()} - {self.paciente}"

class OrdenLaboratorio(models.Model):

    ESTADOS = [
        ("pendiente", "Pendiente"),
        ("laboratorio", "En laboratorio"),
        ("lista", "Lista para retirar"),
        ("entregada", "Entregada"),
    ]

    ARCADAS = [
        ("", "Seleccionar arcada"),
        ("superior", "Superior"),
        ("inferior", "Inferior"),
        ("ambas", "Ambas"),
    ]

    protesis = models.ForeignKey(
        Prosthesis,
        on_delete=models.CASCADE,
        related_name="ordenes_laboratorio"
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="pendiente"
    )

    fecha = models.DateField(auto_now_add=True)

    # =========================
    # ORDEN DE LABORATORIO V2
    # =========================
    arcada = models.CharField(
        "Arcada",
        max_length=20,
        choices=ARCADAS,
        blank=True,
        default=""
    )
    piezas_removible = models.CharField(max_length=100, blank=True)
    piezas_fija = models.CharField(max_length=100, blank=True)
    odontologo = models.CharField(max_length=150, blank=True, default="Dr. Rodrigo Suma")

    # Removible
    parcial_cromo = models.BooleanField(default=False)
    parcial_acrilica = models.BooleanField(default=False)
    agregado_diente = models.BooleanField(default=False)
    agregado_gancho = models.BooleanField(default=False)

    # Fija
    corona_unitaria = models.BooleanField(default=False)
    provisorio_fijo = models.BooleanField(default=False)

    # Material enviado V2
    impresion_primaria = models.BooleanField(default=False)
    antagonista = models.BooleanField(default=False)
    enfilado_enviado = models.BooleanField(default=False)
    modelo_trabajo = models.BooleanField(default=False)

    # Solicito V2
    solicita_cubeta_individual = models.BooleanField(default=False)
    solicita_placa_articular = models.BooleanField(default=False)
    solicita_enfilado = models.BooleanField(default=False)
    solicita_terminacion = models.BooleanField(default=False)
    solicita_cromo = models.BooleanField(default=False)
    prueba_estructura = models.BooleanField(default=False)
    prueba_estetica = models.BooleanField(default=False)
    glaseado = models.BooleanField(default=False)
    solicita_bizcocho = models.BooleanField(default=False)

    # Material de prótesis fija
    material_metal = models.BooleanField(default=False)
    material_acrilico = models.BooleanField(default=False)
    material_ceromero = models.BooleanField(default=False)
    material_ceramica = models.BooleanField(default=False)
    material_zirconio = models.BooleanField(default=False)
    material_disilicato = models.BooleanField(default=False)

    # =========================
    # CAMPOS ANTERIORES
    # Se conservan para no perder órdenes existentes.
    # =========================
    protesis_completa = models.BooleanField(default=False)
    protesis_completa_sup = models.BooleanField(default=False)
    protesis_completa_inf = models.BooleanField(default=False)

    protesis_parcial = models.BooleanField(default=False)
    protesis_parcial_sup = models.BooleanField(default=False)
    protesis_parcial_inf = models.BooleanField(default=False)

    protesis_flexible = models.BooleanField(default=False)
    protesis_flexible_sup = models.BooleanField(default=False)
    protesis_flexible_inf = models.BooleanField(default=False)

    cromo = models.BooleanField(default=False)
    cromo_sup = models.BooleanField(default=False)
    cromo_inf = models.BooleanField(default=False)

    provisorio_placa = models.BooleanField(default=False)
    provisorio_placa_sup = models.BooleanField(default=False)
    provisorio_placa_inf = models.BooleanField(default=False)

    reparacion = models.BooleanField(default=False)
    rebasado = models.BooleanField(default=False)
    cubeta_individual = models.BooleanField(default=False)
    placa_articular = models.BooleanField(default=False)
    enfilado = models.BooleanField(default=False)
    terminacion = models.BooleanField(default=False)
    removible_otros = models.BooleanField(default=False)
    removible_otros_texto = models.CharField(max_length=255, blank=True)

    perno_metalico = models.BooleanField(default=False)
    incrustacion = models.BooleanField(default=False)
    jacket = models.BooleanField(default=False)
    corona = models.BooleanField(default=False)
    puente_fijo = models.BooleanField(default=False)

    contencion = models.BooleanField(default=False)
    contencion_sup = models.BooleanField(default=False)
    contencion_inf = models.BooleanField(default=False)

    placa_relajacion = models.BooleanField(default=False)
    placa_relajacion_sup = models.BooleanField(default=False)
    placa_relajacion_inf = models.BooleanField(default=False)

    ortodoncia_otros = models.BooleanField(default=False)
    ortodoncia_otros_texto = models.CharField(max_length=255, blank=True)

    impresion_inicial = models.BooleanField(default=False)
    impresion_inicial_sup = models.BooleanField(default=False)
    impresion_inicial_inf = models.BooleanField(default=False)

    impresion_definitiva = models.BooleanField(default=False)
    impresion_definitiva_sup = models.BooleanField(default=False)
    impresion_definitiva_inf = models.BooleanField(default=False)

    modelo = models.BooleanField(default=False)
    modelo_sup = models.BooleanField(default=False)
    modelo_inf = models.BooleanField(default=False)

    registro_mordida = models.BooleanField(default=False)
    protesis_a_reparar = models.BooleanField(default=False)

    material_otros = models.BooleanField(default=False)
    material_otros_texto = models.CharField(max_length=255, blank=True)

    indicaciones = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    fecha_envio = models.DateField(null=True, blank=True)
    fecha_entrega_prometida = models.DateField(
        "Solicitado para",
        null=True,
        blank=True
    )
    hora_entrega_solicitada = models.TimeField(
        "Hora solicitada",
        null=True,
        blank=True
    )
    fecha_recepcion = models.DateField(null=True, blank=True)

    @property
    def resumen_trabajo(self):
        trabajos = []
        opciones = [
            (self.protesis_completa, "Prótesis completa"),
            (self.parcial_cromo or self.cromo, "Prótesis parcial cromo"),
            (self.parcial_acrilica or self.protesis_parcial, "Prótesis parcial acrílica"),
            (self.protesis_flexible, "Prótesis flexible"),
            (self.provisorio_placa, "Provisorio a placa"),
            (self.corona_unitaria or self.corona, "Corona unitaria"),
            (self.puente_fijo, "Puente fijo"),
            (self.jacket, "Jacket"),
            (self.perno_metalico, "Perno muñón"),
            (self.incrustacion, "Incrustación"),
            (self.provisorio_fijo, "Provisorio fijo"),
            (self.contencion, "Contención"),
            (self.placa_relajacion, "Placa neuromiorrelajante"),
            (self.reparacion, "Reparación"),
            (self.rebasado, "Rebase"),
            (self.agregado_diente, "Agregado de diente"),
            (self.agregado_gancho, "Agregado de gancho"),
        ]
        for marcado, nombre in opciones:
            if marcado:
                trabajos.append(nombre)
        return ", ".join(trabajos) if trabajos else "Orden de laboratorio"

    def __str__(self):
        return f"Orden #{self.id} - {self.protesis.paciente}"


class Inventory(models.Model):
    codigo = models.CharField(max_length=50, blank=True, null=True)
    nombre = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100, blank=True, null=True)

    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=0)

    precio = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    proveedor = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    @property
    def valor_total(self):
        return self.stock * self.precio

    @property
    def semaforo(self):
        if self.stock <= self.stock_minimo:
            return "rojo"
        elif self.stock <= self.stock_minimo + 2:
            return "amarillo"
        return "verde"

    def __str__(self):
        return self.nombre

class InventoryMovement(models.Model):
    producto = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name="movimientos"
    )

    fecha = models.DateTimeField(auto_now_add=True)

    tipo = models.CharField(
        max_length=10,
        choices=[
            ("entrada", "Entrada"),
            ("salida", "Salida"),
        ]
    )

    cantidad = models.IntegerField(default=1)

    observacion = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.producto.nombre} - {self.tipo} ({self.cantidad})"



class RayosX(models.Model):
    paciente = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="rayos_x"
    )
    imagen = models.ImageField(upload_to="rayos_x/")
    descripcion = models.CharField(max_length=255, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rayos X - {self.paciente}"






