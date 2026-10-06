from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Response

from ..accounts import Site
from ..accounts.security import Refused
from ..accounts.users import User
from ..config import SESSION_COOKIE, SESSION_SECONDS


def site(request: Request) -> Site:
    return request.app.state.site


def optional_user(request: Request) -> User | None:
    return site(request).session_user(request.cookies.get(SESSION_COOKIE))


def current_user(request: Request) -> User:
    user = optional_user(request)
    if user is None:
        raise Refused("Войдите в систему", 401)
    return user


def admin_user(request: Request) -> User:
    user = current_user(request)
    if not user.is_admin:
        raise Refused("Раздел доступен только администратору", 403)
    return user


def open_session(response: Response, request: Request, user: User) -> None:
    response.set_cookie(SESSION_COOKIE, site(request).token_for(user), max_age=SESSION_SECONDS, httponly=True,
                        samesite="lax", path="/")


def close_session(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


Signed = Annotated[User, Depends(current_user)]
Admin = Annotated[User, Depends(admin_user)]
