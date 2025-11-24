from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from members.models import Member
from .models import UserProfile


@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create UserProfile when User is created.
    Link to Member by email if exists, or create new Member.
    """
    if created:
        # Try to find existing member by email
        member = None
        try:
            member = Member.objects.get(email=instance.email)
        except Member.DoesNotExist:
            # Create new member if doesn't exist
            member = Member.objects.create(
                email=instance.email,
                first_name=instance.first_name,
                last_name=instance.last_name
            )
        
        # Create user profile linked to member
        UserProfile.objects.create(user=instance, member=member)


@receiver(post_save, sender=Member)
def update_member_profile_complete(sender, instance, **kwargs):
    """
    When Member is updated, check if profile is complete.
    """
    if hasattr(instance, 'user_profile'):
        instance.user_profile.check_profile_complete()
