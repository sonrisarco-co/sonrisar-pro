from rest_framework import serializers
from core.models import Patient, Appointment, Budget

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "nombre",
            "apellido",
            "ci",
            "telefono",
            "email",
        ]
