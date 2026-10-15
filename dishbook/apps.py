from django.apps import AppConfig


class DishbookConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dishbook'

    def ready(self):
        from . import checks  # noqa: F401
