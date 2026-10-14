from django.urls import path
from django.contrib.auth import views
from .views import daily, agenda_updates
urlpatterns = [path('actividad/agenda/cambios/', agenda_updates, name='agenda_updates'),
    path('cuentas/ingresar/', views.LoginView.as_view(template_name='activity/login.html'), name='login'),
    path('cuentas/salir/', views.LogoutView.as_view(), name='logout'),
    path('cuentas/clave/', views.PasswordChangeView.as_view(template_name='activity/password.html', success_url='/'), name='password_change'),
    path('actividad/', daily, name='activity_daily')]
