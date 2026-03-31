from django import template

register = template.Library()

@register.filter
def multiplicar(valor1, valor2):
    try:
        return float(valor1) * float(valor2)
    except:
        return 0
