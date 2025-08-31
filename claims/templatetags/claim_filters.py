from django import template

register = template.Library()

@register.filter
def split(value, delimiter=','):
    return value.split(delimiter) if value else []

@register.filter  
def trim(value):
    return value.strip() if value else ''