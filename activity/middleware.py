from contextvars import ContextVar
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils.cache import patch_cache_control
current_request = ContextVar('activity_request', default=None)
def manager(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Responsables Sonrisar').exists())
class ActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        token = current_request.set(request)
        try:
            with transaction.atomic():
                response = self.get_response(request)
                if response.status_code >= 400:
                    transaction.set_rollback(True)
            if request.user.is_authenticated or request.path.startswith('/cuentas/'):
                patch_cache_control(response, private=True, no_store=True)
            return response
        finally:
            current_request.reset(token)
    def process_view(self, request, view, args, kwargs):
        name = request.resolver_match.url_name
        public = name in {'login', 'token_obtain_pair', 'token_refresh', 'service-worker'} or request.path.startswith('/static/')
        # JWT endpoints keep their existing DRF authentication.
        if not request.user.is_authenticated and not public and not request.path.startswith('/api/'):
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if name in {'patient_delete', 'clinical_record_delete'} and not manager(request.user):
            raise PermissionDenied('No tenés permiso para eliminar pacientes o historias clínicas.')
