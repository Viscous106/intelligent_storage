"""
Django Template Tags for Intelligent Storage System.
Custom tags and filters for templates.
"""

from django import template
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.utils.timesince import timesince
from django.utils import timezone
import json

register = template.Library()


# ===== Filters =====

@register.filter
def filesize(bytes_value):
    """
    Convert bytes to human-readable file size.
    Usage: {{ file.file_size|filesize }}
    """
    try:
        bytes_value = int(bytes_value)
    except (ValueError, TypeError):
        return '0 bytes'

    if bytes_value < 1024:
        return f'{bytes_value} bytes'
    elif bytes_value < 1024 ** 2:
        return f'{bytes_value / 1024:.2f} KB'
    elif bytes_value < 1024 ** 3:
        return f'{bytes_value / (1024 ** 2):.2f} MB'
    else:
        return f'{bytes_value / (1024 ** 3):.2f} GB'


@register.filter
def percentage(value, total):
    """
    Calculate percentage.
    Usage: {{ used|percentage:total }}
    """
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            return 0
        return round((value / total) * 100, 1)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary by key.
    Usage: {{ metadata|get_item:'category' }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''


@register.filter
def prettify_json(value):
    """
    Pretty print JSON.
    Usage: {{ metadata|prettify_json }}
    """
    try:
        if isinstance(value, str):
            value = json.loads(value)
        return json.dumps(value, indent=2, ensure_ascii=False)
    except (json.JSONDecodeError, TypeError):
        return value


@register.filter
def truncate_chars(value, length):
    """
    Truncate string to specified length.
    Usage: {{ text|truncate_chars:50 }}
    """
    try:
        length = int(length)
        value = str(value)
        if len(value) <= length:
            return value
        return value[:length] + '...'
    except (ValueError, TypeError):
        return value


@register.filter
def file_icon(file_type):
    """
    Get icon class for file type.
    Usage: {{ file.detected_type|file_icon }}
    """
    icons = {
        'document': '📄',
        'image': '🖼️',
        'video': '🎬',
        'audio': '🎵',
        'code': '💻',
        'compressed': '📦',
        'other': '📎',
    }
    return icons.get(file_type, '📎')


@register.filter
def status_badge(status):
    """
    Get Bootstrap badge class for status.
    Usage: {{ store.status|status_badge }}
    """
    badges = {
        'active': 'success',
        'inactive': 'secondary',
        'processing': 'warning',
        'completed': 'success',
        'failed': 'danger',
        'pending': 'info',
    }
    return badges.get(status.lower(), 'secondary')


@register.filter
def quota_status(percentage):
    """
    Get quota status based on percentage.
    Usage: {{ usage|quota_status }}
    """
    try:
        percentage = float(percentage)
        if percentage >= 100:
            return 'exceeded'
        elif percentage >= 90:
            return 'critical'
        elif percentage >= 70:
            return 'warning'
        else:
            return 'ok'
    except (ValueError, TypeError):
        return 'ok'


# ===== Tags =====

@register.simple_tag
def progress_bar(value, total, show_percentage=True):
    """
    Render a progress bar.
    Usage: {% progress_bar used total %}
    """
    try:
        value = float(value)
        total = float(total)
        if total == 0:
            pct = 0
        else:
            pct = min((value / total) * 100, 100)

        # Determine color
        if pct >= 90:
            color = 'danger'
        elif pct >= 70:
            color = 'warning'
        else:
            color = 'success'

        html = f'''
        <div class="progress" style="height: 25px;">
            <div class="progress-bar bg-{color}" role="progressbar"
                 style="width: {pct}%"
                 aria-valuenow="{pct}" aria-valuemin="0" aria-valuemax="100">
                {f"{pct:.1f}%" if show_percentage else ""}
            </div>
        </div>
        '''
        return mark_safe(html)
    except (ValueError, TypeError, ZeroDivisionError):
        return ''


@register.simple_tag
def storage_badge(store):
    """
    Render storage usage badge.
    Usage: {% storage_badge store %}
    """
    pct = store.storage_used_percentage
    status = quota_status(pct)

    badge_class = {
        'ok': 'success',
        'warning': 'warning',
        'critical': 'danger',
        'exceeded': 'danger',
    }.get(status, 'secondary')

    html = f'<span class="badge bg-{badge_class}">{pct:.1f}% Used</span>'
    return mark_safe(html)


@register.simple_tag
def file_type_badge(file_type):
    """
    Render file type badge with icon.
    Usage: {% file_type_badge file.detected_type %}
    """
    icon = file_icon(file_type)
    html = f'<span class="badge bg-info">{icon} {file_type.capitalize()}</span>'
    return mark_safe(html)


@register.simple_tag
def indexed_badge(is_indexed):
    """
    Render indexed status badge.
    Usage: {% indexed_badge file.is_indexed %}
    """
    if is_indexed:
        html = '<span class="badge bg-success">✓ Indexed</span>'
    else:
        html = '<span class="badge bg-secondary">Not Indexed</span>'
    return mark_safe(html)


@register.simple_tag
def time_ago(dt):
    """
    Render time ago in human-readable format.
    Usage: {% time_ago file.uploaded_at %}
    """
    if not dt:
        return ''

    now = timezone.now()
    if dt > now:
        return 'just now'

    return f'{timesince(dt)} ago'


@register.simple_tag
def store_card(store):
    """
    Render store card with statistics.
    Usage: {% store_card store %}
    """
    usage_pct = store.storage_used_percentage
    status = quota_status(usage_pct)

    badge_class = {
        'ok': 'success',
        'warning': 'warning',
        'critical': 'danger',
        'exceeded': 'danger',
    }.get(status, 'secondary')

    html = f'''
    <div class="card mb-3">
        <div class="card-body">
            <h5 class="card-title">
                {store.display_name}
                <span class="badge bg-{badge_class} float-end">{usage_pct:.1f}%</span>
            </h5>
            <p class="card-text text-muted">{store.description or "No description"}</p>
            <div class="row text-center">
                <div class="col">
                    <strong>{store.total_files}</strong><br>
                    <small class="text-muted">Files</small>
                </div>
                <div class="col">
                    <strong>{store.total_chunks}</strong><br>
                    <small class="text-muted">Chunks</small>
                </div>
                <div class="col">
                    <strong>{filesize(store.storage_size_bytes + store.embeddings_size_bytes)}</strong><br>
                    <small class="text-muted">Used</small>
                </div>
            </div>
        </div>
    </div>
    '''
    return mark_safe(html)


@register.inclusion_tag('storage/tags/search_form.html', takes_context=True)
def search_form(context):
    """
    Render search form.
    Usage: {% search_form %}
    """
    return {
        'request': context.get('request'),
    }


@register.inclusion_tag('storage/tags/file_list.html', takes_context=True)
def file_list(context, files, show_store=True):
    """
    Render file list.
    Usage: {% file_list files %}
    """
    return {
        'files': files,
        'show_store': show_store,
        'request': context.get('request'),
    }


# ===== Utility Tags =====

@register.simple_tag(takes_context=True)
def query_string(context, **kwargs):
    """
    Update query string with new parameters.
    Usage: {% query_string page=2 sort='name' %}
    """
    request = context.get('request')
    if not request:
        return ''

    params = request.GET.copy()
    for key, value in kwargs.items():
        if value:
            params[key] = value
        elif key in params:
            del params[key]

    return f'?{params.urlencode()}' if params else ''


@register.simple_tag
def get_verbose_name(instance, field_name):
    """
    Get verbose name for model field.
    Usage: {% get_verbose_name file 'file_size' %}
    """
    try:
        return instance._meta.get_field(field_name).verbose_name
    except Exception:
        return field_name.replace('_', ' ').title()


@register.filter
def add_class(field, css_class):
    """
    Add CSS class to form field.
    Usage: {{ form.field|add_class:'form-control' }}
    """
    return field.as_widget(attrs={'class': css_class})


@register.filter
def field_type(field):
    """
    Get form field widget type.
    Usage: {{ form.field|field_type }}
    """
    return field.field.widget.__class__.__name__
