from .middleware import manager
def permissions(request):
    return {'sonrisar_manager': manager(request.user),
            'sonrisar_live': getattr(request, 'sonrisar_live', None)}
