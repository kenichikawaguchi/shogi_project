def sliding_moves_with_obstacles(pos, direction, board, board_size, player):
    """
    指定された方向 (dr, dc) に沿って、盤上の端までの有効な移動先（障害物考慮）のリストを返す。
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
    成り状態も考慮して、非スライディングの場合の1マス分の相対オフセットを返す。
    ※歩、香車、桂馬は、成っている場合は金将と同じ動きとする。
    """
    if player == 'sente':
        forward = -1  # sente: 上方向
        backward = 1
    else:
        forward = 1   # gote: 下方向
        backward = -1

    def gold_offsets():
        return [
            (forward, 0),   # 前
            (forward, -1),  # 前左
            (forward, 1),   # 前右
            (0, -1),        # 左
            (0, 1),         # 右
            (backward, 0)   # 後直進
        ]

    if piece_type == 'pawn':
        return gold_offsets() if is_promoted else [(forward, 0)]
    elif piece_type == 'lance':
        return gold_offsets() if is_promoted else [(forward, 0)]  # 非成はスライディング処理で扱う
    elif piece_type == 'knight':
        return gold_offsets() if is_promoted else [(forward * 2, -1), (forward * 2, 1)]
    elif piece_type == 'silver':
        return gold_offsets() if is_promoted else [
            (forward, -1), (forward, 0), (forward, 1), (backward, -1), (backward, 1)
        ]
    elif piece_type == 'gold':
        return gold_offsets()
    elif piece_type == 'king':
        return [
            (-1, -1), (-1, 0), (-1, 1),
            (0, -1),           (0, 1),
            (1, -1),  (1, 0),  (1, 1)
        ]
    elif piece_type == 'bishop':
        if not is_promoted:
            return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        else:
            # 成角：角行のスライディングに加え、上下左右に1マスずつ移動可能
            return [(-1, -1), (-1, 1), (1, -1), (1, 1),
                    (-1, 0), (1, 0), (0, -1), (0, 1)]
    elif piece_type == 'rook':
        if not is_promoted:
            return [(-1, 0), (1, 0), (0, -1), (0, 1)]
        else:
            # 成飛：飛車のスライディングに加え、斜めに1マス分移動可能
            return [(-1, 0), (1, 0), (0, -1), (0, 1),
                    (-1, -1), (-1, 1), (1, -1), (1, 1)]
    else:
        return []

def get_valid_moves(piece_type, pos, player, board, is_promoted=False, board_size=9):
    """
    指定された駒の種類、現在の位置、プレイヤー、成り状態、および盤の状態に基づき、
    移動可能な絶対座標のリストを返す。
    
    ・スライディング駒（角行、飛車、香車の非成の場合）は、障害物を考慮して端まで移動可能なマスを計算する。
    ・それ以外の駒は、1マス分の相対オフセットを元に移動先を計算し、障害物チェックを行う。
    """
    row, col = pos
    moves = []
    
    # スライディング駒（非成）の処理
    if piece_type in ('bishop', 'rook', 'lance') and not is_promoted:
        if piece_type == 'bishop':
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        elif piece_type == 'rook':
            directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        elif piece_type == 'lance':
            directions = [( -1, 0 )] if player == 'sente' else [(1, 0)]
        for d in directions:
            moves.extend(sliding_moves_with_obstacles(pos, d, board, board_size, player))
        return moves
    else:
        # 非スライディングまたは成った場合（1マス移動）
        offsets = get_directional_offsets(piece_type, player, is_promoted)
        for dr, dc in offsets:
            new_row, new_col = row + dr, col + dc
            if 0 <= new_row < board_size and 0 <= new_col < board_size:
                cell = board[new_row][new_col]
                if cell is None:
                    moves.append((new_row, new_col))
                else:
                    # 敵駒なら捕獲可能
                    if cell["player"] != player:
                        moves.append((new_row, new_col))
        return moves

# 動作確認用のテスト
if __name__ == "__main__":
    # 盤面（9x9）の例。全て空の盤を作成。
    board_size = 9
    board = [[None for _ in range(board_size)] for _ in range(board_size)]
    
    # 例として、(6,4) にsenteの歩があり、(4,4) にgoteの駒が置かれているとする。
    board[6][4] = {"player": "sente", "piece_type": "pawn"}
    board[4][4] = {"player": "gote", "piece_type": "pawn"}
    
    pos = (6, 4)
    
    # 歩の有効移動先（非成）
    moves_pawn = get_valid_moves('pawn', pos, 'sente', board, is_promoted=False, board_size=board_size)
    print("Sente Pawn moves:", moves_pawn)
    
    # 香車（非成、sente）のスライディング移動
    moves_lance = get_valid_moves('lance', pos, 'sente', board, is_promoted=False, board_size=board_size)
    print("Sente Lance sliding moves:", moves_lance)
    
    # 桂馬（非成、sente）の移動
    moves_knight = get_valid_moves('knight', pos, 'sente', board, is_promoted=False, board_size=board_size)
    print("Sente Knight moves:", moves_knight)
    
    # 角行（非成、sente）のスライディング移動
    moves_bishop = get_valid_moves('bishop', pos, 'sente', board, is_promoted=False, board_size=board_size)
    print("Sente Bishop sliding moves:", moves_bishop)
    
    # 飛車（非成、sente）のスライディング移動
    moves_rook = get_valid_moves('rook', pos, 'sente', board, is_promoted=False, board_size=board_size)
    print("Sente Rook sliding moves:", moves_rook)

