"""Intervalos de citas. El extremo final no ocupa el turno siguiente."""
from datetime import time
from django.core.exceptions import ValidationError
from django.db import connection


def bloquear_agenda_fecha(fecha):
    # Serializar reservas del mismo día en PostgreSQL hasta guardar la cita.
    if connection.vendor == "postgresql" and connection.in_atomic_block:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [822610, fecha.toordinal()])


def minutos(hora):
    return hora.hour * 60 + hora.minute


def se_cruzan(inicio, fin, otro_inicio, otro_fin):
    return inicio < otro_fin and otro_inicio < fin


def validar_reserva(cita):
    from .models import Appointment, DayBlock, TimeBlock
    if not cita.fecha or not cita.hora or cita.duracion not in {15, 30, 45, 60}:
        return
    if cita.estado == "cancelado":
        return
    bloquear_agenda_fecha(cita.fecha)
    # Permitir corregir datos clínicos/administrativos de turnos históricos,
    # aunque existan superposiciones anteriores a esta funcionalidad.
    if cita.pk:
        anterior = Appointment.objects.filter(pk=cita.pk).first()
        if anterior and anterior.estado != "cancelado" and (
            anterior.fecha, anterior.hora, anterior.duracion
        ) == (cita.fecha, cita.hora, cita.duracion):
            return
    inicio = minutos(cita.hora)
    fin = inicio + cita.duracion
    if inicio < 9 * 60 or fin > 20 * 60:
        raise ValidationError({"hora": "La cita completa debe quedar entre las 09:00 y las 20:00."})
    if DayBlock.objects.filter(fecha=cita.fecha).exists():
        raise ValidationError({"fecha": "Ese día está bloqueado."})
    if cita.fecha.weekday() != 5 and se_cruzan(inicio, fin, 14 * 60, 15 * 60):
        raise ValidationError({"duracion": "La cita se superpone con el descanso de 14:00 a 15:00."})
    # Respetar el ancho de cada bloqueo manual en el esquema mixto vigente.
    from .views import horarios_para_fecha
    horarios = horarios_para_fecha(cita.fecha)
    for bloqueo in TimeBlock.objects.filter(fecha=cita.fecha):
        siguiente = next((h for h in horarios if h > bloqueo.hora), time(20))
        if se_cruzan(inicio, fin, minutos(bloqueo.hora), minutos(siguiente)):
            raise ValidationError({"duracion": "La cita se superpone con un horario bloqueado."})
    for otra in Appointment.objects.filter(fecha=cita.fecha).exclude(pk=cita.pk).exclude(estado="cancelado"):
        otro_inicio = minutos(otra.hora)
        if se_cruzan(inicio, fin, otro_inicio, otro_inicio + otra.duracion):
            raise ValidationError({"hora": (
                f"El horario se superpone con una cita de {otra.hora:%H:%M} "
                f"a {otra.hora_fin:%H:%M}. Elegí otro horario o duración."
            )})


def reservar_grilla(filas, citas, dias):
    """Extender una única tarjeta con rowspan sin esconder conflictos antiguos."""
    citas = [c for c in citas if c.estado != "cancelado"]
    for columna, dia in enumerate(dias):
        del_dia = [c for c in citas if c.fecha == dia]
        for indice, fila in enumerate(filas):
            celda = fila["celdas"][columna]
            if celda.get("ocultar"):
                continue
            inicio = minutos(fila["hora"])
            en_curso = [c for c in del_dia if minutos(c.hora) <= inicio < minutos(c.hora) + c.duracion]
            if not celda.get("ocupado") and en_curso:
                celda.update(bloqueado=True, tipo_bloqueo="reserva",
                             motivo_bloqueo=f"Reservado hasta {max(c.hora_fin for c in en_curso):%H:%M}")
            mostradas = celda.get("citas", [])
            if len(mostradas) != 1:
                continue
            cita = next((c for c in del_dia if c.id == mostradas[0]["id"]), None)
            if not cita or cita.hora != fila["hora"]:
                continue
            fin = minutos(cita.hora) + cita.duracion
            if any(otra.id != cita.id and se_cruzan(inicio, fin, minutos(otra.hora),
                   minutos(otra.hora) + otra.duracion) for otra in del_dia):
                continue
            siguientes = []
            for siguiente in filas[indice + 1:]:
                if minutos(siguiente["hora"]) >= fin:
                    break
                otras = siguiente["celdas"][columna]
                # No ocultar tarjetas de turnos previos aunque se superpongan.
                if otras.get("ocupado") or (otras.get("bloqueado") and otras.get("tipo_bloqueo") != "fuera"):
                    siguientes = []
                    break
                siguientes.append(otras)
            if siguientes:
                celda["rowspan"] = len(siguientes) + 1
                for otras in siguientes:
                    otras["ocultar"] = True
