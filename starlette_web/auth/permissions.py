from starlette.types import Scope

from starlette_web.auth.models import User
from starlette_web.common.authorization.permissions import BasePermission
from starlette_web.common.http.requests import PRequest
from starlette_web.common.http.exceptions import PermissionDeniedError


class IsSuperuserPermission(BasePermission):
    async def has_permission(self, request: PRequest, scope: Scope) -> bool:
        user: User = scope.get('user')
        if (not user) or (not getattr(user, 'is_superuser', False)):
            raise PermissionDeniedError("You don't have an admin privileges.")

        return True
