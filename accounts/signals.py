
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs) -> None:
    """Create a profile for every new user."""
    if not created:
        return

    default_role = UserProfile.Role.ADMIN if instance.is_superuser else UserProfile.Role.STUDENT
    UserProfile.objects.create(user=instance, role=default_role)


@receiver(post_save, sender=User)
def sync_superuser_profile_role(sender, instance, **kwargs) -> None:
    """Keep the admin role aligned for superusers."""
    profile, _ = UserProfile.objects.get_or_create(
        user=instance,
        defaults={
            'role': UserProfile.Role.ADMIN if instance.is_superuser else UserProfile.Role.STUDENT,
        },
    )

    if instance.is_superuser and profile.role != UserProfile.Role.ADMIN:
        profile.role = UserProfile.Role.ADMIN
        profile.save(update_fields=['role', 'updated_at'])