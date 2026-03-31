from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import ClinicalRecord

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_clinical_records(request, patient_id):
    records = ClinicalRecord.objects.filter(
        paciente_id=patient_id
    ).order_by("-fecha")

    data = [
        {
            "id": r.id,
            "fecha": r.fecha.strftime("%d/%m/%Y"),
            "motivo": r.motivo,
            "diagnostico": r.diagnostico,
            "tratamiento": r.tratamiento,
        }
        for r in records
    ]

    return Response(data)