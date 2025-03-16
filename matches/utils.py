# matches/utils.py
import copy
from django.shortcuts import get_object_or_404
from .models import GameState, Match, Move

def perform_undo_move(match_id, user):
    match = get_object_or_404(Match, id=match_id)
    game_state = get_object_or_404(GameState, match=match)

    print(f'game_state:{game_state}')
    last_move_obj = match.moves.order_by('-move_number').first()
    print(f'last_move_obj:{last_move_obj}')
    if not last_move_obj:
        raise Exception("取り消す指し手がありません。")
    if last_move_obj.player != user:
        raise Exception("あなたは最後の指し手を打っていません。")

    move_data = last_move_obj.move_data
    board = game_state.board

    print(f'move_data:{move_data}')

    if move_data.get("drop", False):
        # drop move の場合：盤面から駒を削除し、持ち駒を回復
        dest = move_data.get("dest")
        if dest is None:
            raise Exception("不正な指し手データです。")
        board[dest[0]][dest[1]] = None
        piece_type = move_data.get("piece_type")
        turn = 'gote' if game_state.turn == 'sente' else 'sente'
        hand = game_state.pieces_in_hand.get(turn, {})
        hand[piece_type] = hand.get(piece_type, 0) + 1
        game_state.pieces_in_hand[turn] = hand
    else:
        # 通常の移動の場合：駒を元の位置に戻し、捕獲されていた場合は復元
        src = move_data.get("src")
        dest = move_data.get("dest")
        captured = move_data.get("captured")  # 捕獲情報があれば
        piece = board[dest[0]][dest[1]]
        board[src[0]][src[1]] = piece
        board[dest[0]][dest[1]] = captured if captured else None

    # 手番を元に戻す
    game_state.turn = 'gote' if game_state.turn == 'sente' else 'sente'
    # 更新: 前の指し手があればその "dest" を last_move に、それがなければ空リスト
    previous_move_obj = match.moves.filter(move_number__lt=last_move_obj.move_number).order_by('-move_number').first()
    game_state.last_move = previous_move_obj.move_data.get("dest") if previous_move_obj else []
    game_state.board = board
    game_state.save()

    # 最新の指し手を削除
    last_move_obj.delete()

    return {
        "board": board,
        "pieces_in_hand": game_state.pieces_in_hand,
        "turn": game_state.turn,
        "last_move": game_state.last_move,
    }

