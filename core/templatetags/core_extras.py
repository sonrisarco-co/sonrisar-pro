import re
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, [])


@register.filter
def motivo_actual(value):
    """Display the current label for legacy appointment reasons."""
    return re.sub(r"\bconsulta\s*/\s*diagn[oó]stico\b", "Valoración", str(value or ""), flags=re.IGNORECASE)
