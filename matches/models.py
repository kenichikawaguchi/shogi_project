from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.postgres.fields import JSONField

from django.db import models
from django.contrib.auth import get_user_model
from accounts.models import CustomUser


User = get_user_model()

class Move(models.Model):
    """
    対局中の各指し手を記録するモデル。
    - match: 対局ルーム (Match) との外部キー
    - player: この指し手を打ったプレイヤー
    - move_data: JSON形式で指し手の情報を保存
         例: {"src": [src_row, src_col], "dest": [dest_row, dest_col], "piece_type": "pawn", "is_promoted": False}
    - move_number: 対局の何手目かを記録する整数
    - timestamp: 指し手が記録された日時
    """
    match = models.ForeignKey('Match', on_delete=models.CASCADE, related_name='moves')
    player = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    move_data = models.JSONField()
    move_number = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"Move {self.move_number} in Match {self.match.id} by {self.player.username} at {self.timestamp}"

class Match(models.Model):
    RESULT_CHOICES = [
        ('ongoing', '進行中'),
        ('sente_win', '先手勝利'),
        ('gote_win', '後手勝利'),
        ('draw', '引き分け'),
        ('waiting', '開始待ち'),
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
        verbose_name="後手プレイヤー",
        null=True,
        blank=True
    )
    
    # 対局結果（進行中の場合は 'waiting'）
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        default='waiting',
        verbose_name="対局結果"
    )
    
    # 対局開始時刻と終了時刻
    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name="対局開始時刻"
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="対局終了時刻"
    )
    # ここで待った機能が許可されるかどうかのフラグを追加（デフォルトは True）
    allow_undo = models.BooleanField(default=True)
    
    # 任意: 盤面の状態をJSONなどで記録するフィールド
    board_state = models.TextField(
        null=True,
        blank=True,
        verbose_name="盤面状態",
        help_text="盤面の状態をJSON形式などで保存（任意）"
    )
    is_deleted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"#{self.id}: {self.player1.username} vs {self.player2.username if self.player2 else '未割当'}"


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
    last_move = models.JSONField(default=list)

    def __str__(self):
        return f"GameState for Match {self.match.id}"

    def update_last_move(self, move):
        self.last_move = move
        self.save()


class UndoRequest(models.Model):
    """
    待ったリクエストの状態を保存するモデル。
    - match: 対局ルーム（Match）との 1対1 の関係。各対局で最大1件のUndoリクエストが存在する前提。
    - requested_by: 待ったをリクエストしたプレイヤー。
    - status: リクエストの状態。'pending'（未処理）、'accepted'（承認）、'denied'（拒否）
    - timestamp: リクエストの時刻
    """
    match = models.OneToOneField('Match', on_delete=models.CASCADE, related_name='undo_request')
    requested_by = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('denied', 'Denied')
    ], default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UndoRequest for Match {self.match.id} by {self.requested_by.username} ({self.status})"

