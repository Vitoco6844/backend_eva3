from django import template

register = template.Library()


@register.filter
def clp(value):
    try:
        return "$" + format(int(value), ",").replace(",", ".")
    except (ValueError, TypeError):
        return "—"
