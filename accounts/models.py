from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now

class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # メールアドレス（ユニーク）
    password_hash = models.TextField()  # ハッシュ化されたパスワード
    rating = models.IntegerField(null=True, blank=True, default=1200)  # レーティング（デフォルト1200）
    created_at = models.DateTimeField(default=now)  # アカウント作成日時
    updated_at = models.DateTimeField(auto_now=True)  # 最終更新日時

    def __str__(self):
        return self.username

