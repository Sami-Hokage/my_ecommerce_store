from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        # Social users don't need OTP, so we make them active immediately
        user.is_active = True

        # If you have a custom 'is_verified' field in your model, set it here too
        if hasattr(user, 'is_verified'):
            user.is_verified = True

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        data = sociallogin.account.extra_data

        if sociallogin.account.provider == 'google':
            user.first_name = data.get('given_name', '')
            user.last_name = data.get('family_name', '')


            if not user.username:
                email = data.get('email', '')
                user.username = email.split('@')[0]

        user.is_active = True
        user.save()
        return user