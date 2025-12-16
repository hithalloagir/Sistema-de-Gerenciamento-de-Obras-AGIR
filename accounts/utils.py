from typing import Iterable, Optional

from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet

from .models import UserProfile, ObraAlocacao


def get_or_create_profile(user):
    if isinstance(user, AnonymousUser) or user is None:
        return None
    profile = getattr(user, "profile", None)
    if profile is None:
        profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def get_user_level(user) -> Optional[str]:
    profile = get_or_create_profile(user)
    return getattr(profile, "role", None)


def is_admin(user) -> bool:
    return get_user_level(user) == UserProfile.Level.ADMIN


def is_level2(user) -> bool:
    return get_user_level(user) == UserProfile.Level.NIVEL2


def is_level1(user) -> bool:
    return get_user_level(user) == UserProfile.Level.NIVEL1


def _user_obra_ids(user) -> Iterable[int]:
    if not getattr(user, "is_authenticated", False):
        return ObraAlocacao.objects.none().values_list("obra_id", flat=True)
    return ObraAlocacao.objects.filter(usuario=user).values_list("obra_id", flat=True)


def filter_obras_for_user(qs: QuerySet, user):
    if not getattr(user, "is_authenticated", False):
        return qs.none()
    if is_admin(user):
        return qs
    return qs.filter(pk__in=_user_obra_ids(user))


def filter_queryset_by_user_obras(qs: QuerySet, user, obra_lookup: str = "obra"):
    if not getattr(user, "is_authenticated", False):
        return qs.none()
    if is_admin(user):
        return qs
    lookup = f"{obra_lookup}__in"
    return qs.filter(**{lookup: _user_obra_ids(user)})


def user_has_obra_access(user, obra) -> bool:
    if obra is None or not getattr(user, "is_authenticated", False):
        return False
    if is_admin(user):
        return True
    return ObraAlocacao.objects.filter(obra=obra, usuario=user).exists()
