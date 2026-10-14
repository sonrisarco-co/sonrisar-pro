from .middleware import manager
def permissions(request):
    return {'sonrisar_manager': manager(request.user)}
