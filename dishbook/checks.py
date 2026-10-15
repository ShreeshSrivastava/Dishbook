import os

from django.conf import settings
from django.core.checks import Error, register


@register()
def persistent_storage_check(app_configs, **kwargs):
    if not getattr(settings, "ON_RAILWAY", False):
        return []
    if os.environ.get("RAILWAY_VOLUME_MOUNT_PATH") or os.environ.get("DJANGO_DATA_DIR"):
        return []
    return [
        Error(
            "No Railway volume is attached, so the database and uploaded photos "
            "would be erased on every deploy.",
            hint="Attach a volume to this service (mount path /data) and redeploy.",
            id="dishbook.E001",
        )
    ]
