from django.db import models
from django import forms

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




# 📋 HISTORIA CLÍNICA

class ClinicalRecord(models.Model):
    paciente = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="clinical_records"
    )
    fecha = models.DateField(auto_now_add=True)
    motivo = models.CharField(max_length=200)
    diagnostico = models.TextField(blank=True)
    tratamiento = models.TextField(blank=True)
    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"Historia {self.paciente} ({self.fecha})"




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
    def saldo_pendiente(self):
        total = self.total or Decimal("0.00")
        return total - self.total_pagado


class BudgetItem(models.Model):
    presupuesto = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="items")
    concepto = models.CharField(max_length=200)
    cantidad = models.IntegerField(default=1)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    total_item = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.concepto} ({self.cantidad} x {self.valor})"


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
    fecha = models.DateField(auto_now_add=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
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

    ETAPAS_PROTESIS = [
        ("cubeta", "Cubeta individual"),
        ("placa", "Placa articular (rodete)"),
        ("enfilado", "Enfilado"),
        ("terminacion", "Terminación"),
    ]

    paciente = models.ForeignKey(Patient, on_delete=models.CASCADE)
    trabajo = models.CharField(max_length=200)
    etapa = models.CharField(max_length=200, choices=ETAPAS_PROTESIS)
    fecha_envio = models.DateField(blank=True, null=True)
    fecha_retorno = models.DateField(blank=True, null=True)

    observaciones = models.TextField(blank=True)

    def __str__(self):
        return f"{self.trabajo} - {self.paciente}"


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








