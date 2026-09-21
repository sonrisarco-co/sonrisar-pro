from django.conf import settings


class MobileUploadCSRFMiddleware:
    """Completa el token CSRF en cargas móviles del módulo Rayos X."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_upload = (
            request.method == "POST"
            and request.path.startswith("/pacientes/")
            and request.path.endswith("/rayos-x/nuevo/")
        )

        if is_upload and not request.META.get("HTTP_X_CSRFTOKEN"):
            origin = request.headers.get("Origin", "")
            referer = request.headers.get("Referer", "")
            expected_origin = f"{request.scheme}://{request.get_host()}"
            same_origin = origin == expected_origin or (
                not origin and referer.startswith(expected_origin + "/")
            )

            if same_origin:
                cookie_token = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
                if cookie_token:
                    request.META["HTTP_X_CSRFTOKEN"] = cookie_token

        return self.get_response(request)
