from allauth.account.forms import LoginForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomLoginForm(LoginForm):
    def clean_login(self):
        """ ユーザー名またはメールアドレスでログインできるようにする """
        login = self.cleaned_data["login"]
        if "@" in login:
            # メールアドレスの場合
            user = User.objects.filter(email=login).first()
            if user:
                return user.username  # Django-allauth は username で認証するので変換
        return login

