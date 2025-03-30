# matches/utils.py
import copy
from django.shortcuts import get_object_or_404
from .models import GameState, Match, Move

def perform_undo_move(match_id, user, approved=False):
    """
    指定された対局(match_id)で Undo（待った）処理を実行する関数。
    approved が False の場合は、最後の指し手を打ったユーザーであるか確認する。
    この処理では、Move モデルに記録された指し手情報をもとに、盤面および持ち駒の状態を元に戻します。

    捕獲があった指し手の場合、move_data に "captured" キーが含まれているので、
    その情報を利用して、Undo 時に持ち駒から該当する駒のカウントを減らし、盤面上に復元します。
    """
    match = get_object_or_404(Match, id=match_id)
    game_state = get_object_or_404(GameState, match=match)

    print(f'game_state:{game_state}')
    last_move_obj = match.moves.order_by('-move_number').first()
    print(f'last_move_obj:{last_move_obj}')
    if not last_move_obj:
        raise Exception("取り消す指し手がありません。")
    if not approved and last_move_obj.player != user:
        print(f'last_move_obj.player:{last_move_obj.player} != user:{user}')
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
        piece = board[dest[0]][dest[1]]
        board[src[0]][src[1]] = piece
        captured = move_data.get("captured")  # 捕獲情報があれば
        if captured:
            # Undo 時に、捕獲していた場合は、持ち駒から捕獲した駒のカウントを1減らす
            # capturing_player = last_move_obj.player.username  # この手を打ったプレイヤー
            # hand = game_state.pieces_in_hand.get(capturing_player, {})
            turn = 'gote' if game_state.turn == 'sente' else 'sente'
            hand = game_state.pieces_in_hand.get(turn, {})
            if hand.get(captured["piece_type"], 0) > 0:
                hand[captured["piece_type"]] -= 1
                if hand[captured["piece_type"]] == 0:
                    del hand[captured["piece_type"]]
                # game_state.pieces_in_hand[capturing_player] = hand
                game_state.pieces_in_hand[turn] = hand
            # 盤面のdest に、捕獲された駒を復元する
            board[dest[0]][dest[1]] = captured
        else:
            # もし捕獲がなければ、dest は空にする
            board[dest[0]][dest[1]] = None

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

