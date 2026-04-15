from functools import wraps
from typing import Callable

from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied


def user_has_any_role(user, allowed_roles: tuple[str, ...]) -> bool:
    """Return True when the authenticated user has one of the allowed roles."""
    if not user.is_authenticated:
        return False

    if user.is_superuser and 'admin' in allowed_roles:
        return True

    profile = getattr(user, 'profile', None)
    return bool(profile and profile.role in allowed_roles)


def role_required(*allowed_roles: str) -> Callable:
    """Restrict a function-based view to users with one of the supplied roles."""
    if not allowed_roles:
        raise ValueError('role_required expects at least one role.')

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not user_has_any_role(request.user, tuple(allowed_roles)):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator


class RoleRequiredMixin(UserPassesTestMixin):
    """Class Based Views mixin that restricts access to users with allowed roles."""

    allowed_roles: tuple[str, ...] = ()

    def test_func(self) -> bool:
        if not self.allowed_roles:
            raise ValueError('RoleRequiredMixin.allowed_roles must be configured.')
        return user_has_any_role(self.request.user, self.allowed_roles)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()
