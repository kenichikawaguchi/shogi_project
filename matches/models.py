from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.postgres.fields import JSONField


class Match(models.Model):
    RESULT_CHOICES = [
        ('ongoing', '進行中'),
        ('win', '勝利'),
        ('lose', '敗北'),
        ('draw', '引き分け'),
    ]
    
    # 対局参加者（先手と後手）
    player1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_player1',
        verbose_name="先手プレイヤー"
    )
    player2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_player2',
        verbose_name="後手プレイヤー"
    )
    
    # 対局結果（進行中の場合は 'ongoing'）
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default='ongoing',
        verbose_name="対局結果"
    )
    
    # 対局開始時刻と終了時刻
    start_time = models.DateTimeField(
        default=timezone.now,
        verbose_name="対局開始時刻"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="対局終了時刻"
    )
    
    # 任意: 盤面の状態をJSONなどで記録するフィールド
    board_state = models.TextField(
        null=True,
        blank=True,
        verbose_name="盤面状態",
        help_text="盤面の状態をJSON形式などで保存（任意）"
    )
    
    def __str__(self):
        return f"{self.player1.username} vs {self.player2.username} - {self.get_result_display()}"


def initial_board():
    return [[None for _ in range(9)] for _ in range(9)]


def initial_pieces_in_hand():
    return {"sente": {}, "gote": {}}


class GameState(models.Model):
    """
    対局の盤面状態と持ち駒情報を管理するモデル。
    - board: 9x9 の盤面状態を JSON 形式で保存（例：各セルが null または駒情報の dict）
    - pieces_in_hand: 各プレイヤーの持ち駒情報を JSON 形式で保存
      例: { "sente": {"pawn": 2, "lance": 0, ...}, "gote": {"pawn": 1, ...} }
    """
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name="game_state")
    board = models.JSONField(default=initial_board)
    pieces_in_hand = models.JSONField(default=initial_pieces_in_hand)
    turn = models.CharField(max_length=10, choices=[('sente', '先手'), ('gote', '後手')], default='sente')

    def __str__(self):
        return f"GameState for Match {self.match.id}"

