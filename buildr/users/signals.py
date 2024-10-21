from django.dispatch import receiver
from allauth.account.signals import user_signed_up, user_logged_in
from django.contrib.auth.models import User
from .models import customUser

@receiver(user_signed_up)
def create_custom_user(sender, request, user, **kwargs):
    custom_user, created = customUser.objects.get_or_create(user=user)
    
    if created:
        social_account = user.socialaccount_set.filter(provider='google').first()
        if social_account:
            custom_user.google_profile_pic_url = social_account.get_avatar_url()
            custom_user.save()

@receiver(user_logged_in)
def ensure_custom_user_exists(sender, request, user, **kwargs):
    custom_user, created = customUser.objects.get_or_create(user=user)
    social_account = user.socialaccount_set.filter(provider='google').first()
    if social_account:
        custom_user.google_profile_pic_url = social_account.get_avatar_url()
    
    if created:
        custom_user.save()
