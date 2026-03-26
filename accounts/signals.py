from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .services import ensure_default_system_admins


@receiver(post_migrate)
def bootstrap_local_accounts(sender, **kwargs):
    ensure_default_system_admins()
