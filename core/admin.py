from django.contrib import admin
from .models import (
    Patient,
    Appointment,
    Payment,
    Budget,
    BudgetItem,
    Prosthesis,
    Inventory,
)

admin.site.register(Patient)
admin.site.register(Appointment)
admin.site.register(Payment)
admin.site.register(Budget)
admin.site.register(BudgetItem)
admin.site.register(Prosthesis)
admin.site.register(Inventory)

admin.site.site_header = "SONRISAR ADMIN OK"
admin.site.index_title = "MODELOS CARGADOS"