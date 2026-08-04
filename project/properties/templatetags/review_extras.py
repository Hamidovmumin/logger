from django import template

register = template.Library()

@register.filter
def get_range(value):
    try:
        return range(int(value))
    except (TypeError, ValueError):
        return range(0)

@register.filter
def sub(value, arg):
    try:
        return int(value) - int(arg)
    except (TypeError, ValueError):
        return 0

@register.filter
def initials(review):
    name = (review.name or '')[:1]
    surname = (review.surname or '')[:1]
    return f'{name}{surname}'.upper()