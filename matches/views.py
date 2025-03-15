import json, copy
import datetime
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from .models import Match, GameState
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from django.db.models import Q

from django.utils import timezone


# 初期盤面状態を返す関数
def initial_board():
    # ここでは空の9×9盤を返す例です。
    # 実際の将棋初期配置に合わせて変更してください。
    board = [[None for _ in range(9)] for _ in range(9)]

    board[0] = [
        {"player": "gote", "piece_type": "lance", "is_promoted": False},
        {"player": "gote", "piece_type": "knight", "is_promoted": False},
        {"player": "gote", "piece_type": "silver", "is_promoted": False},
        {"player": "gote", "piece_type": "gold", "is_promoted": False},
        {"player": "gote", "piece_type": "king", "is_promoted": False},
        {"player": "gote", "piece_type": "gold", "is_promoted": False},
        {"player": "gote", "piece_type": "silver", "is_promoted": False},
        {"player": "gote", "piece_type": "knight", "is_promoted": False},
        {"player": "gote", "piece_type": "lance", "is_promoted": False},
    ]

    board[1][1] = {"player": "gote", "piece_type": "rook", "is_promoted": False}
    board[1][7] = {"player": "gote", "piece_type": "bishop", "is_promoted": False}

    for c in range(9):
        board[2][c] = {"player": "gote", "piece_type": "pawn", "is_promoted": False}

    for c in range(9):
        board[6][c] = {"player": "sente", "piece_type": "pawn", "is_promoted": False}

    board[7][1] = {"player": "sente", "piece_type": "bishop", "is_promoted": False}
    board[7][7] = {"player": "sente", "piece_type": "rook", "is_promoted": False}

    board[8] = [
        {"player": "sente", "piece_type": "lance", "is_promoted": False},
        {"player": "sente", "piece_type": "knight", "is_promoted": False},
        {"player": "sente", "piece_type": "silver", "is_promoted": False},
        {"player": "sente", "piece_type": "gold", "is_promoted": False},
        {"player": "sente", "piece_type": "king", "is_promoted": False},
        {"player": "sente", "piece_type": "gold", "is_promoted": False},
        {"player": "sente", "piece_type": "silver", "is_promoted": False},
        {"player": "sente", "piece_type": "knight", "is_promoted": False},
        {"player": "sente", "piece_type": "lance", "is_promoted": False},
    ]

    return board


# 初期持ち駒情報を返す関数
def initial_pieces_in_hand():
    # ここでは各プレイヤーの持ち駒が無い状態を返します。
    return {"sente": {}, "gote": {}}

@login_required
def new_match(request):
    """
    新規対局開始のためのビュー。
    現在のユーザーを player1 として、新しい対局（Match）とゲーム状態（GameState）を作成し、
    対局盤面表示ビュー（board_view）にリダイレクトします。
    
    ※ 実際の運用では、対局相手（player2）はマッチングなどで決定する必要がありますが、
      ここではサンプルとして player2 も同じユーザーにしています。
    """
    user = request.user
    match = Match.objects.create(
        player1=user,
        player2=None,  # サンプル用。実際は適切な対戦相手に置き換えます。
        result='waiting'
    )
    
    GameState.objects.create(
        match=match,
        board=initial_board(),
        pieces_in_hand=initial_pieces_in_hand(),
        turn='sente'
    )
    
    # 新規対局の盤面表示ページへリダイレクト（match_id を URL パラメータで渡す）
    # return redirect('board_view', match_id=match.id)
    broadcast_match_list_update(user)
    return redirect('home')

# ----- ゲームロジックの実装 -----

def sliding_moves_with_obstacles(pos, direction, board, board_size, player):
    """
    指定された方向 (dr, dc) に沿って、盤上の端または障害物までの有効な移動先を返す。
      ・空マスならその座標を追加
      ・敵駒があればその座標も追加し、そこで止まる
      ・自陣の駒があれば追加せずにそこで停止
    """
    moves = []
    row, col = pos
    dr, dc = direction
    new_row = row + dr
    new_col = col + dc
    while 0 <= new_row < board_size and 0 <= new_col < board_size:
        cell = board[new_row][new_col]
        if cell is None:
            moves.append((new_row, new_col))
        else:
            if cell["player"] != player:
                moves.append((new_row, new_col))
            break
        new_row += dr
        new_col += dc
    return moves

def get_directional_offsets(piece_type, player, is_promoted=False):
    """
    非スライディングまたは成った場合の1マス分の相対オフセットを返す。
    歩、香車、桂馬が成った場合は金将と同じ動きにする。
    """
    if player == 'sente':
        forward = -1
        backward = 1
    else:
        forward = 1
        backward = -1

    def gold_offsets():
        return [
            (forward, 0),
            (forward, -1),
            (forward, 1),
            (0, -1),
            (0, 1),
            (backward, 0)
        ]
    if piece_type == 'pawn':
        return gold_offsets() if is_promoted else [(forward, 0)]
    elif piece_type == 'lance':
        return gold_offsets() if is_promoted else [(forward, 0)]  # 非成はスライディングで扱う
    elif piece_type == 'knight':
        return gold_offsets() if is_promoted else [(forward * 2, -1), (forward * 2, 1)]
    elif piece_type == 'silver':
        return gold_offsets() if is_promoted else [(forward, -1), (forward, 0), (forward, 1), (backward, -1), (backward, 1)]
    elif piece_type == 'gold':
        return gold_offsets()
    elif piece_type == 'king':
        return [(-1, -1), (-1, 0), (-1, 1),
                (0, -1),           (0, 1),
                (1, -1),  (1, 0),  (1, 1)]
    elif piece_type == 'bishop':
        if not is_promoted:
            return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        else:
            return [(-1, -1), (-1, 1), (1, -1), (1, 1),
                    (-1, 0), (1, 0), (0, -1), (0, 1)]
    elif piece_type == 'rook':
        if not is_promoted:
            return [(-1, 0), (1, 0), (0, -1), (0, 1)]
        else:
            return [(-1, 0), (1, 0), (0, -1), (0, 1),
                    (-1, -1), (-1, 1), (1, -1), (1, 1)]
    else:
        return []

def get_valid_moves(piece_type, pos, player, board, is_promoted=False, board_size=9):
    """
    指定された駒の種類、位置、プレイヤー、盤面状態、成り状態に基づき、
    有効な移動先（絶対座標）のリストを返す。
    
    ・スライディング駒（bishop, rook, lance）の非成の場合は、障害物を考慮して盤上の端までの移動先を算出する。
    ・それ以外の場合は1マス移動先を計算する。
    """
    row, col = pos
    moves = []
    if piece_type in ('bishop', 'rook', 'lance') and not is_promoted:
        if piece_type == 'bishop':
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif piece_type == 'rook':
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        elif piece_type == 'lance':
            directions = [(-1, 0)] if player == 'sente' else [(1, 0)]
        for d in directions:
            moves.extend(sliding_moves_with_obstacles(pos, d, board, board_size, player))
        return moves
    elif piece_type in ('bishop', 'rook') and is_promoted:
        if piece_type == 'bishop':
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif piece_type == 'rook':
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for d in directions:
            moves.extend(sliding_moves_with_obstacles(pos, d, board, board_size, player))
        offsets = get_directional_offsets(piece_type, player, is_promoted)
        for dr, dc in offsets:
            new_row = row + dr
            new_col = col + dc
            if 0 <= new_row < board_size and 0 <= new_col < board_size:
                cell = board[new_row][new_col]
                if cell is None or cell["player"] != player:
                    moves.append((new_row, new_col))
        return moves
    else:
        offsets = get_directional_offsets(piece_type, player, is_promoted)
        for dr, dc in offsets:
            new_row = row + dr
            new_col = col + dc
            if 0 <= new_row < board_size and 0 <= new_col < board_size:
                cell = board[new_row][new_col]
                if cell is None or cell["player"] != player:
                    moves.append((new_row, new_col))
        return moves

@require_POST
@login_required
def resign_match(request):
    """
    投了処理：
    ログインユーザーが対局中の対局において投了した場合、
    そのユーザーの対局は負けとし、勝者を決定する。
    WebSocketを利用して、対局ルーム内の全クライアントに対局終了と勝者情報を通知する。
    POSTパラメータ:
      - match_id: 対局ID
    """
    try:
        data = json.loads(request.body)
        match_id = int(data.get('match_id'))
    except Exception:
        return JsonResponse({'error': 'パラメータが正しくありません。'}, status=400)

    match = get_object_or_404(Match, id=match_id)

    # 投了するユーザーが対局に参加しているか確認
    if request.user != match.player1 and request.user != match.player2:
        return JsonResponse({'error': 'あなたはこの対局に参加していません。'}, status=400)

    # 投了したユーザーが player1（先手）なら、後手勝利；player2（後手）なら先手勝利
    if request.user == match.player1:
        winner = 'gote'
        match.result = 'gote_win'
    else:
        winner = 'sente'
        match.result = 'sente_win'

    match.end_time = timezone.now()
    match.save()

    # WebSocketブロードキャスト
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"match_{match_id}",
        {
            "type": "game_update",
            "message": {
                "game_over": True,
                "winner": winner,
                "action": "resign",
                "message": "投了が行われました。"
            }
        }
    )

    return JsonResponse({
        "message": "投了しました。",
        "winner": winner,
        "game_over": True,
    })

# ----- Django View -----
@require_GET
def get_moves(request):
    """
    GETパラメータ:
      row: 数値, 駒の現在の行（0-indexed）
      col: 数値, 駒の現在の列（0-indexed）
      piece_type: 駒の種類（例: pawn, lance, knight, bishop, rook など）
      player: "sente" または "gote"
      is_promoted: "1"（成り）または "0"（非成）
      
    サンプル盤面状態はハードコードされています（実際はゲームセッションから取得）。
    """
    try:
        row = int(request.GET.get('row', 0))
        col = int(request.GET.get('col', 0))
        piece_type = request.GET.get('piece_type', 'pawn')
        player = request.GET.get('player', 'sente')
        is_promoted = request.GET.get('is_promoted', '0') == '1'
        match_id = int(request.GET.get('match_id', 0))
    except Exception as e:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    game_state = get_object_or_404(GameState, match_id=match_id)
    board = game_state.board
    # board = SAMPLE_BOARD
    pos = (row, col)
    moves = get_valid_moves(piece_type, pos, player, board, is_promoted, board_size=9)
    return JsonResponse({'moves': moves})


def board_view(request, match_id):
    game_state = get_object_or_404(GameState, match_id=match_id)
    match = game_state.match
    # 現在のユーザーがどちら側かを判定（例: player1 が先手）
    current_player = "sente" if request.user == match.player1 else "gote"
    context = {
        'sample_board_json': json.dumps(game_state.board),
        'pieces_in_hand_json': json.dumps(game_state.pieces_in_hand),
        'match_id': match_id,
        'turn': game_state.turn,
        'last_move': game_state.last_move,
        'match': match,
        'current_user': request.user,
        'current_player': current_player,
    }
    return render(request, 'matches/board.html', context)


# プロモーションゾーンの判定（9x9盤の場合）
def is_in_promotion_zone(row, player):
    if player == 'sente':
        return row <= 2  # 0,1,2 行目
    else:  # gote
        return row >= 6  # 6,7,8 行目

# 成り可能な駒の種類
PROMOTABLE_PIECES = ['pawn', 'lance', 'knight', 'silver', 'bishop', 'rook']


@require_POST
@login_required
def move_piece(request):
    """
    POSTパラメータ（JSON）:
      - match_id: 対局ID
      - src_row: 移動元の行（0-indexed）
      - src_col: 移動元の列（0-indexed）
      - dest_row: 移動先の行（0-indexed）
      - dest_col: 移動先の列（0-indexed）
      - promote: オプション。成る場合は "1"、成らない場合は "0"。（対象駒がプロモーション可能な場合）

    対象駒がプロモーション可能かどうかは、
    ・移動元または移動先が該当するプロモーションゾーンに入っているか
    ・駒の種類が PROMOTABLE_PIECES に含まれるか
    により判定する。
    ユーザーの選択に応じて、駒の is_promoted を更新する。
    """
    try:
        data = json.loads(request.body)
        match_id = int(data.get('match_id'))
        src_row = int(data.get('src_row'))
        src_col = int(data.get('src_col'))
        dest_row = int(data.get('dest_row'))
        dest_col = int(data.get('dest_col'))
        # promote パラメータはオプション。文字列 "1" なら True、"0" なら False
        promote_flag = data.get('promote')
        if promote_flag is not None:
            promote = promote_flag == "1"
        else:
            promote = False  # デフォルトは False（フロント側で選択済みと仮定）
    except Exception as e:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    # 指定された match_id の GameState を取得
    game_state = get_object_or_404(GameState, match_id=match_id)
    match = game_state.match
    board = game_state.board  # 盤面は 2次元リスト
    moving_piece = board[src_row][src_col]

    if moving_piece is None:
        return JsonResponse({'error': 'No piece at source'}, status=400)

    # 手番チェック: 移動しようとする駒のプレイヤーが現在の手番でなければエラー
    if moving_piece["player"] != game_state.turn:
        return JsonResponse({'error': 'Not your turn'}, status=400)

    # プロモーション可能かどうかの判定
    if moving_piece["piece_type"] in PROMOTABLE_PIECES:
        if not moving_piece["is_promoted"]:
            src_in_zone = is_in_promotion_zone(src_row, moving_piece["player"])
            dest_in_zone = is_in_promotion_zone(dest_row, moving_piece["player"])
            promotion_possible = src_in_zone or dest_in_zone
        else:
            promotion_possible = False
    else:
        promotion_possible = False

    # ユーザーが promote パラメータを送信している場合、かつプロモーションが可能なら反映
    if promotion_possible:
        moving_piece["is_promoted"] = promote

    # ここで、成るか否かの選択が可能な場合は promote_flag を利用する
    if not moving_piece["is_promoted"]:
        if moving_piece["piece_type"] == "pawn":
            # 強制成り条件: 先手なら dest_row == 0、後手なら dest_row == 8
            if (moving_piece["player"] == "sente" and dest_row == 0) or (moving_piece["player"] == "gote" and dest_row == 8):
                moving_piece["is_promoted"] = True
            else:
                # 強制成りでない場合は、ユーザーの選択に委ねる
                moving_piece["is_promoted"] = (promote_flag == "1")
        elif moving_piece["piece_type"] == "lance":
            if (moving_piece["player"] == "sente" and dest_row == 0) or (moving_piece["player"] == "gote" and dest_row == 8):
                moving_piece["is_promoted"] = True
            else:
                moving_piece["is_promoted"] = (promote_flag == "1")
        elif moving_piece["piece_type"] == "knight":
            if (moving_piece["player"] == "sente" and (dest_row == 0 or dest_row == 1)) or (moving_piece["player"] == "gote" and (dest_row == 7 or dest_row == 8)):
                moving_piece["is_promoted"] = True
            else:
                moving_piece["is_promoted"] = (promote_flag == "1")


    # まず、移動をシミュレーションした盤面を作成
    simulated_board = copy.deepcopy(board)
    simulated_board[dest_row][dest_col] = moving_piece
    simulated_board[src_row][src_col] = None

    # シミュレーション後、自分の王がチェック状態になっているか判定
    if is_in_check(simulated_board, moving_piece["player"]):
        return JsonResponse({'error': 'その指し手は自分の王が捕獲されるため不正です。'}, status=400)

    # 敵駒があれば捕獲
    target_cell = board[dest_row][dest_col]
    game_over = False
    winner = None

    if target_cell is not None and target_cell["player"] != moving_piece["player"]:
        # もし相手の駒が王なら、捕獲して対局終了
        if target_cell["piece_type"] == "king":
            # 捕獲された王は、持ち駒に加えず、対局終了とする
            winner = moving_piece["player"]
            match.result = f"{winner}_win"
            match.end_time = timezone.now()
            match.save()
            game_over = True
        else:
            # 王以外の場合は、捕獲処理を通常通り行う
            target_cell["is_promoted"] = False
            captured_piece_type = target_cell["piece_type"]
            capturing_player = moving_piece["player"]
            hand = game_state.pieces_in_hand.get(capturing_player, {})
            hand[captured_piece_type] = hand.get(captured_piece_type, 0) + 1
            game_state.pieces_in_hand[capturing_player] = hand

    board[dest_row][dest_col] = moving_piece
    board[src_row][src_col] = None

    # 手番の交代: 先手なら後手、後手なら先手に
    if not game_over:
        game_state.turn = 'gote' if game_state.turn == 'sente' else 'sente'

    # 詰み判定（ここでは簡易チェック関数 is_checkmate を使用）
    # 例えば、現在の手番側の王が詰んでいる場合、その対局は終了するものとする
    if is_checkmate(board, game_state.pieces_in_hand, game_state.turn, game_state.match):
        game_over = True
        # 手番が交代した直後なので、今打とうとしている側の次の手番が詰んでいるということは、
        # 直前の手番（対局を指した側）が勝者となる
        match = game_state.match
        if not (match.result == "sente_win" or match.result == "gote_win"):
            winner = 'sente' if game_state.turn == 'gote' else 'gote'
            # 対局終了時刻を設定
            match.end_time = datetime.datetime.now()
            # 結果を更新（例: "sente_win" または "gote_win"）
            match.result = f"{winner}_win"
            match.save()

    game_state.last_move = [dest_row, dest_col];
    game_state.board = board
    game_state.save()

    # チャンネルレイヤーを取得し、グループにブロードキャスト
    channel_layer = get_channel_layer()
    print(f'channel_layer:  {channel_layer}')
    async_to_sync(channel_layer.group_send)(
        f'match_{match_id}',
        {
            'type': 'game_update',
            'message': {
                'board': board,
                'pieces_in_hand': game_state.pieces_in_hand,
                'turn': game_state.turn,
                'game_over': game_over,
                'winner': winner if game_over else None,
                'last_move': game_state.last_move,
                'action': 'move_piece'
            }
        }
    )

    response_data = {
        'board': board,
        'pieces_in_hand': game_state.pieces_in_hand,
        'last_move': game_state.last_move,
        'turn': game_state.turn
    }

    if game_over:
        response_data['game_over'] = True
        response_data['winner'] = winner
    else:
        response_data['game_over'] = False

    return JsonResponse(response_data)

@require_POST
@login_required
def drop_piece(request):
    """
    持ち駒ドロップ用のビュー

    POSTパラメータ（JSON）:
      - match_id: 対局ID
      - piece_type: ドロップする駒の種類（例: pawn, lance, knight, silver, bishop, rook, gold, king）
      - player: ドロップするプレイヤー（"sente" または "gote"）
      - dest_row: ドロップ先の行（0-indexed）
      - dest_col: ドロップ先の列（0-indexed）

    ・移動先セルが空であることを確認
    ・プレイヤーの持ち駒情報に該当駒があることを確認
    ・歩の場合、同じ列に未成の歩があれば二歩禁止により打てない
    ・歩、香車、桂馬の場合、ドロップ先が打てない位置（必ず前方に進む駒の打てない段）であればエラーを返す
    ・持ち駒から1個減らし、盤面に駒（未成状態）を配置
    ・更新後の盤面状態と持ち駒情報をJSONで返す
    """
    try:
        data = json.loads(request.body)
        match_id = int(data.get('match_id'))
        piece_type = data.get('piece_type')
        player = data.get('player')
        dest_row = int(data.get('dest_row'))
        dest_col = int(data.get('dest_col'))
    except Exception:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    # 指定された match_id の GameState を取得
    game_state = get_object_or_404(GameState, match_id=match_id)
    board = game_state.board  # 盤面は 2 次元リスト

    # ドロップ先セルが空であるか確認
    if board[dest_row][dest_col] is not None:
        return JsonResponse({'error': 'Destination is not empty'}, status=400)

    # 持ち駒情報のチェック
    hand = game_state.pieces_in_hand.get(player, {})
    if hand.get(piece_type, 0) <= 0:
        return JsonResponse({'error': 'No such piece in hand'}, status=400)

    # 二歩禁止チェック：歩の場合、同じ列に既に未成の歩があるかをチェック
    if piece_type == "pawn":
        for r in range(len(board)):
            cell = board[r][dest_col]
            if cell is not None and cell["player"] == player and cell["piece_type"] == "pawn" and not cell["is_promoted"]:
                return JsonResponse({'error': '二歩は禁止されています。'}, status=400)
        # 打ち歩詰め禁止のチェック：歩を打った場合の盤面をシミュレーションし、相手の玉が詰むかどうかを判定
        simulated_board = copy.deepcopy(board)
        simulated_board[dest_row][dest_col] = {
            "player": player,
            "piece_type": "pawn",
            "is_promoted": False
        }
        opponent = "gote" if player == "sente" else "sente"
        # ここで、相手側の詰み判定を行う
        if is_checkmate(simulated_board, game_state.pieces_in_hand, opponent):
            return JsonResponse({'error': '打ち歩詰めは禁止されています。'}, status=400)
    # --- ここまで打ち歩詰めチェック ---

    # 駒の打てる位置の制限
    # 先手は盤面上部（行0に打てない）、後手は盤面下部（行8に打てない）
    if piece_type in ("pawn", "lance"):
        if player == "sente" and dest_row == 0:
            return JsonResponse({'error': f"歩や香車は最上段には打てません。"}, status=400)
        elif player == "gote" and dest_row == 8:
            return JsonResponse({'error': f"歩や香車は最上段には打てません。"}, status=400)
    elif piece_type == "knight":
        if player == "sente" and (dest_row == 0 or dest_row == 1):
            return JsonResponse({'error': "桂馬は最上段およびその下段には打てません。"}, status=400)
        elif player == "gote" and (dest_row == 7 or dest_row == 8):
            return JsonResponse({'error': "桂馬は最上段およびその下段には打てません。"}, status=400)

    # まず、移動をシミュレーションした盤面を作成
    simulated_board = copy.deepcopy(board)
    simulated_board[dest_row][dest_col] = {
        "player": player,
        "piece_type": piece_type,
        "is_promoted": False
    }
    simulated_board[src_row][src_col] = None

    # シミュレーション後、自分の王がチェック状態になっているか判定
    if is_in_check(simulated_board, player):
        return JsonResponse({'error': 'その指し手は自分の王が捕獲されるため不正です。'}, status=400)

    # 持ち駒から該当駒を1個減らす
    hand[piece_type] -= 1
    if hand[piece_type] <= 0:
        del hand[piece_type]
    game_state.pieces_in_hand[player] = hand

    # ドロップされた駒は未成状態で盤上に配置
    board[dest_row][dest_col] = {
        "player": player,
        "piece_type": piece_type,
        "is_promoted": False
    }

    # 手番の交代: 先手なら後手、後手なら先手に
    game_state.turn = 'gote' if game_state.turn == 'sente' else 'sente'

    # 詰み判定（ここでは簡易チェック関数 is_checkmate を使用）
    # 例えば、現在の手番側の王が詰んでいる場合、その対局は終了するものとする
    game_over = False
    winner = None
    if is_checkmate(board, game_state.pieces_in_hand, game_state.turn, game_state.match):
        game_over = True
        # 手番が交代した直後なので、今打とうとしている側の次の手番が詰んでいるということは、
        # 直前の手番（対局を指した側）が勝者となる
        winner = 'sente' if game_state.turn == 'gote' else 'gote'
        match = game_state.match
        # 対局終了時刻を設定
        match.end_time = datetime.datetime.now()
        # 結果を更新（例: "sente_win" または "gote_win"）
        match.result = f"{winner}_win"
        match.save()

    game_state.last_move = [dest_row, dest_col];
    game_state.board = board
    game_state.save()

    response_data = {
        'board': board,
        'pieces_in_hand': game_state.pieces_in_hand,
        'last_move': game_state.last_move,
        'turn': game_state.turn
    }

    if game_over:
        response_data['game_over'] = True
        response_data['winner'] = winner
    else:
        response_data['game_over'] = False

    # チャンネルレイヤーを取得し、グループにブロードキャスト
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'match_{match_id}',
        {
            'type': 'game_update',
            'message': {
                'board': board,
                'pieces_in_hand': game_state.pieces_in_hand,
                'turn': game_state.turn,
                'winner': winner if game_over else None,
                'last_move': game_state.last_move,
                'action': 'move_piece'
            }
        }
    )

    return JsonResponse(response_data)


import copy

def is_in_check(board, player):
    """
    指定された盤面(board)において、player側の王が敵の駒の攻撃範囲にあるかを判定する。
    敵のすべての駒について、get_valid_moves() を用いて王の位置が攻撃可能かどうかをチェックする。
    """
    rows = len(board)
    cols = len(board[0]) if rows > 0 else 0
    king_pos = None
    for r in range(rows):
        for c in range(cols):
            cell = board[r][c]
            if cell is not None and cell["player"] == player and cell["piece_type"] == "king":
                king_pos = (r, c)
                break
        if king_pos is not None:
            break
    # 王が見つからなければチェック状態と判断
    if king_pos is None:
        return True
    print(king_pos)

    enemy = "gote" if player == "sente" else "sente"
    for r in range(rows):
        for c in range(cols):
            cell = board[r][c]
            if cell is not None and cell["player"] == enemy:
                moves = get_valid_moves(cell["piece_type"], (r, c), enemy, board, cell.get("is_promoted", False), board_size=rows)
                if king_pos in moves:
                    return True
    return False

def is_checkmate(board, pieces_in_hand, player, match):
    """
    盤面(board)と持ち駒(pieces_in_hand)に基づいて、player側がどの手を打っても王を守れない場合 True を返す。
    1. まず現在の盤面で王がチェック状態か確認。
    2. 自分の盤上のすべての駒について、各合法手をシミュレーションしてチェックが回避できるか確認。
    3. 持ち駒からの打ち駒についても、盤上の空セルすべてでシミュレーションし、チェック回避が可能か確認。
    どちらの手段でも回避できる手があれば詰みではないと判断する。
    """

    if match.result == "sente_win" or match.result == "gote_win":
        return True

    rows = len(board)
    cols = len(board[0]) if rows > 0 else 0

    # まず、現盤面でチェック状態でなければ詰みではない
    if not is_in_check(board, player):
        return False

    # 1. 盤上の駒の移動を全てシミュレーション
    for r in range(rows):
        for c in range(cols):
            cell = board[r][c]
            if cell is not None and cell["player"] == player:
                moves = get_valid_moves(cell["piece_type"], (r, c), player, board, cell.get("is_promoted", False), board_size=rows)
                for move in moves:
                    new_board = copy.deepcopy(board)
                    # シミュレーション：移動を適用
                    new_board[move[0]][move[1]] = new_board[r][c]
                    new_board[r][c] = None
                    if not is_in_check(new_board, player):
                        return False

    # 2. 持ち駒の打ち駒のシミュレーション
    # 持ち駒情報は、例えば {"sente": {"pawn": 2, ...}, "gote": {...}} の形式
    hand = pieces_in_hand.get(player, {})
    for piece_type, count in hand.items():
        if count <= 0:
            continue
        # 各空セルについて打ち駒を試す
        for r in range(rows):
            for c in range(cols):
                if board[r][c] is not None:
                    continue
                # ドロップ制限：例えば歩は二歩、最終段の打ちなどは既に検証されていると仮定
                # ここで必要なら、drop_move の合法性チェックを追加する
                new_board = copy.deepcopy(board)
                new_board[r][c] = {"player": player, "piece_type": piece_type, "is_promoted": False}
                if not is_in_check(new_board, player):
                    return False

    # どの合法手もチェック回避できなければ詰み
    return True


def home(request):
    """
    トップページ（ホーム）ビュー
    待機中の対局ルーム（result='waiting'）の一覧を取得して表示する。
    """
    waiting_matches = Match.objects.filter(result='waiting').order_by('-start_time')
    my_matches = []
    if request.user.is_authenticated:
        my_matches = Match.objects.filter(result='ongoing').filter(Q(player1=request.user) | Q(player2=request.user)).order_by('-start_time')
    context = {
        'waiting_matches': waiting_matches,
        'my_matches': my_matches,
    }
    return render(request, 'home.html', context)


@login_required
def join_match(request, match_id):
    """
    待機中の対局ルームに後手として参加する。
    """
    match = get_object_or_404(Match, id=match_id, player2__isnull=True)
    match.player2 = request.user
    match.result = 'ongoing'
    match.save()
    broadcast_match_list_update(request.user)
    return redirect('board_view', match_id=match.id)


def broadcast_match_list_update(user):
    """
    現在の待機中対局ルームと、ログインユーザーの対局一覧をシリアライズして、
    WebSocket の "match_list" グループに更新メッセージを送信する。
    """
    waiting_matches_qs = Match.objects.filter(result='waiting').order_by('-start_time')
    my_matches_qs = Match.objects.filter(result='ongoing').filter(Q(player1=user) | Q(player2=user)).order_by('-start_time')

    def serialize_match(match):
        return {
            'id': match.id,
            'player1': {'username': match.player1.username, 'id': match.player1.id},
            'player2': {'username': match.player2.username, 'id': match.player2.id} if match.player2 else None,
            'start_time': match.start_time.isoformat(),
            'result': match.result,
        }

    data = {
        'my_matches': [serialize_match(m) for m in my_matches_qs],
        'waiting_matches': [serialize_match(m) for m in waiting_matches_qs],
    }
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "match_list",
        {
            'type': 'send_update',
            # 'message': data,
            'message': {
                "action": "reload"
            }
        }
    )

