from functools import wraps

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404

helpdesk_staff_member_required = user_passes_test(
    lambda u: u.is_authenticated and u.is_active and u.is_staff
)


def require_setting(name):
    """Return 404 for the decorated view unless the named setting is set."""

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not getattr(settings, name, None):
                raise Http404
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
