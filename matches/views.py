import json
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_GET, require_POST
from .models import Match, GameState
from django.contrib.auth.decorators import login_required


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
        player2=user,  # サンプル用。実際は適切な対戦相手に置き換えます。
        result='ongoing'
    )
    
    GameState.objects.create(
        match=match,
        board=initial_board(),
        pieces_in_hand=initial_pieces_in_hand()
    )
    
    # 新規対局の盤面表示ページへリダイレクト（match_id を URL パラメータで渡す）
    return redirect('board_view', match_id=match.id)

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
    # 現在のユーザーが player1 なら先手、そうでなければ後手とする例
    context = {
        'sample_board_json': json.dumps(game_state.board),
        'pieces_in_hand_json': json.dumps(game_state.pieces_in_hand),
        'match_id': match_id,
        'turn': game_state.turn,
    }
    return render(request, 'matches/board.html', context)


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

    受け取った情報に基づき、GameState.board の状態を更新し、
    更新後の盤面状態をJSONで返す。
    """
    try:
        data = json.loads(request.body)
        match_id = int(data.get('match_id'))
        src_row = int(data.get('src_row'))
        src_col = int(data.get('src_col'))
        dest_row = int(data.get('dest_row'))
        dest_col = int(data.get('dest_col'))
    except Exception as e:
        return JsonResponse({'error': 'Invalid parameters'}, status=400)

    # 指定された match_id の GameState を取得
    game_state = get_object_or_404(GameState, match_id=match_id)
    board = game_state.board  # 盤面は 2次元リスト

    # 移動元に駒が存在するかチェック
    piece = board[src_row][src_col]
    if piece is None:
        return JsonResponse({'error': 'No piece at source'}, status=400)

    # 手番チェック: 移動しようとする駒のプレイヤーが現在の手番でなければエラー
    if piece["player"] != game_state.turn:
        return JsonResponse({'error': 'Not your turn'}, status=400)

    # （必要ならここで有効移動先かどうかを追加チェック）

    # 敵駒があれば捕獲
    target_cell = board[dest_row][dest_col]
    if target_cell is not None and target_cell["player"] != piece["player"]:
        target_cell["is_promoted"] = False
        captured_piece_type = target_cell["piece_type"]
        capturing_player = piece["player"]
        # 持ち駒は、game_state.pieces_in_hand で管理（例: {"sente": {"pawn": 2, ...}, "gote": {...}})
        hand = game_state.pieces_in_hand.get(capturing_player, {})
        hand[captured_piece_type] = hand.get(captured_piece_type, 0) + 1
        game_state.pieces_in_hand[capturing_player] = hand

    board[dest_row][dest_col] = piece
    board[src_row][src_col] = None

    # 手番の交代: 先手なら後手、後手なら先手に
    game_state.turn = 'gote' if game_state.turn == 'sente' else 'sente'

    # 更新した盤面状態を保存
    game_state.board = board
    game_state.save()

    return JsonResponse({'board': board, 'pieces_in_hand': game_state.pieces_in_hand})


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

    game_state.board = board
    game_state.save()

    return JsonResponse({
        'board': board,
        'pieces_in_hand': game_state.pieces_in_hand
    })

