from django.contrib.auth import get_user_model

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .services import normalize_email, sync_user_permissions


class RoleAwareSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        email = normalize_email(sociallogin.user.email)
        if not email:
            return

        User = get_user_model()
        try:
            existing_user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return

        sociallogin.connect(request, existing_user)
        sync_user_permissions(existing_user)

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        if user.email:
            user.email = normalize_email(user.email)
        if not user.username and user.email:
            user.username = user.email
        sync_user_permissions(user)
        return user
