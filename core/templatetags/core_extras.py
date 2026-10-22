import re
from django import template

register = template.Library()

@register.filter
def formato_ci(value):
    """Format a complete Uruguayan CI for display without changing stored data."""
    original = str(value) if value is not None else ""
    if not re.fullmatch(r"[0-9.\-\s]*", original):
        return original
    digits = re.sub(r"\D", "", original)
    if len(digits) not in (7, 8):
        return original
    body = re.sub(r"\B(?=(\d{3})+(?!\d))", ".", digits[:-1])
    return f"{body}-{digits[-1]}"

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, [])


@register.filter
def motivo_actual(value):
    """Display the current label for legacy appointment reasons."""
    return re.sub(r"\bconsulta\s*/\s*diagn[oó]stico\b", "Valoración", str(value or ""), flags=re.IGNORECASE)
