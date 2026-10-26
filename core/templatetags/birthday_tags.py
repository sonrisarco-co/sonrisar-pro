from django import template
from django.utils import timezone
from core.birthdays import birthday_rows
register = template.Library()

@register.inclusion_tag("core/_birthday_today.html", takes_context=True)
def birthdays_today(context):
    today = timezone.localdate()
    return {"rows": birthday_rows(today.month, today.day), "request": context["request"], "today": today}
