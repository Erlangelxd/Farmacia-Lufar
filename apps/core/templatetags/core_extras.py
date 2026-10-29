"""Filtros de plantilla compartidos."""

from django import template

register = template.Library()


@register.filter
def has_group(user, group_name: str) -> bool:
    """Indica si el usuario pertenece al grupo indicado."""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()
