from django import template

register = template.Library()


@register.filter
def dict_get(mapping, key):
    if isinstance(mapping, dict):
        return mapping.get(key)
    return None


@register.simple_tag
def liquid_rect_y(percent, top_y=36, max_height=88):
    """Return top Y integer coordinate inside an SVG vessel for a given 0..100 fill percentage."""
    pct = max(0, min(100, int(percent or 0)))
    fill_h = round((pct / 100.0) * max_height)
    return int(top_y + max_height - fill_h)


@register.simple_tag
def liquid_rect_h(percent, max_height=88):
    """Return filled integer height inside an SVG vessel for a given 0..100 fill percentage."""
    pct = max(0, min(100, int(percent or 0)))
    return int(round((pct / 100.0) * max_height))
