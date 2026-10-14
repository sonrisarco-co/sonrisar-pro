from datetime import date
from urllib.parse import urlsplit
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils import timezone
from .middleware import manager
from .models import Activity
@login_required
def daily(request):
    if not manager(request.user): raise PermissionDenied
    try: day = date.fromisoformat(request.GET.get('fecha', ''))
    except ValueError: day = timezone.localdate()
    return_url = request.GET.get('volver', '').strip()
    if (not return_url.startswith('/') or return_url.startswith('//')
            or not url_has_allowed_host_and_scheme(return_url, allowed_hosts={request.get_host()}, require_https=request.is_secure())
            or urlsplit(return_url).path.startswith('/actividad/')):
        return_url = reverse('home')
    records = Activity.objects.filter(created__date=day)
    username = request.GET.get('usuario', '')
    if username: records = records.filter(username=username)
    section = request.GET.get('seccion', '')
    if section: records = records.filter(section=section)
    return render(request, 'activity/daily.html', {'page': Paginator(records, 50).get_page(request.GET.get('page')),
        'day': day.isoformat(), 'username': username, 'section': section,
        'sonrisar_activity_return_url': return_url,
        'users': Activity.objects.values_list('username', flat=True).distinct().order_by('username'),
        'sections': Activity.objects.values_list('section', flat=True).distinct().order_by('section')})


from django.http import JsonResponse
from django.views.decorators.http import require_GET
from .live import agenda_revision

@login_required
@require_GET
def agenda_updates(request):
    response = JsonResponse({'revision': agenda_revision()})
    response['Cache-Control'] = 'private, no-store'
    return response


from .live import patients_revision

@login_required
@require_GET
def patients_updates(request):
    response = JsonResponse({'revision': patients_revision()})
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_GET
def system_updates(request):
    from .system_live import SCOPES, revision
    scope = request.GET.get('seccion', '')
    if scope not in SCOPES:
        return JsonResponse({'error': 'Sección inválida'}, status=400)
    if scope == 'actividad' and not manager(request.user):
        raise PermissionDenied
    response = JsonResponse({'revision': revision(scope)})
    response['Cache-Control'] = 'private, no-store'
    return response
