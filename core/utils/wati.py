import requests
from django.conf import settings


def enviar_whatsapp(numero, mensaje):
    """
    Envía un mensaje de WhatsApp usando WATI.
    El número debe venir sin espacios, sin guiones y sin '+'
    """
    numero = numero.replace("+", "").replace(" ", "").replace("-", "")

    url = f"{settings.WATI_API_URL}/{numero}"

    params = {
        "messageText": mensaje
    }

    headers = {
        "Authorization": settings.WATI_API_TOKEN
    }

    try:
        response = requests.post(url, headers=headers, params=params)
        return response.status_code, response.text
    except Exception as e:
        return None, str(e)


def generar_mensaje_recordatorio(nombre, fecha_str, hora_str):
    return f"""
Hola 👋 Sonrisar Centro Odontológico te recuerda tu turno para {fecha_str} a las {hora_str}.

📍 Dirección:
Cisnes entre Albatros y Granada
Cooperativa Las Maravillas – Casa 33
Maldonado Park – Maldonado

🗺️ Ubicación:
https://maps.app.goo.gl/kjh9CmRmNoUMSpFw6

Para dejar tu turno asegurado, respondé “Confirmo”, por favor. ✅
Si no recibimos confirmación, el turno podría cancelarse y liberarse para otro paciente.

¡Gracias por tu comprensión!
"""
