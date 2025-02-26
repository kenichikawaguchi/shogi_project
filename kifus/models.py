from django.db import models
from django.utils import timezone
from matches.models import Match  # 対局モデルをインポート

class Kifu(models.Model):
    match = models.OneToOneField(
        Match,
        on_delete=models.CASCADE,
        related_name="kifu",
        verbose_name="対局"
    )
    moves = models.TextField(
        verbose_name="指し手データ",
        help_text="対局の指し手をJSON形式などで保存"
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        verbose_name="保存日時"
    )

    def __str__(self):
        return f"Kifu for Match {self.match.id}"

