from datetime import date, timedelta
from core.models import Appointment
from core.utils.wati import enviar_whatsapp, generar_mensaje_recordatorio

def enviar_recordatorios_automaticos():
    mañana = date.today() + timedelta(days=1)
    citas = Appointment.objects.filter(fecha=mañana)

    for cita in citas:
        nombre = f"{cita.paciente.nombre} {cita.paciente.apellido}"
        fecha_str = cita.fecha.strftime("%d/%m/%Y")
        hora_str = cita.hora.strftime("%H:%M")

        mensaje = generar_mensaje_recordatorio(nombre, fecha_str, hora_str)

        numero = cita.paciente.telefono.replace(" ", "").replace("-", "")

        numero = cita.paciente.telefono.strip()

        # limpiamos espacios y caracteres raros
        solo_numeros = "".join([c for c in numero if c.isdigit()])

        # si NO tiene 8 dígitos → NO enviar WhatsApp (pero no se borra nada)
        if len(solo_numeros) != 8:
            print("Número inválido — no se envía:", numero)
            continue

        # formateo correcto para Uruguay
        numero = "598" + solo_numeros


        status, result = enviar_whatsapp(numero, mensaje)
        print("Enviado a:", numero, "→", status, result)
