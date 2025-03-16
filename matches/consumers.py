import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from .utils import perform_undo_move


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.match_id = self.scope['url_route']['kwargs']['match_id']
        self.group_name = f'match_{self.match_id}'
        
        # グループに参加
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()
    
    async def disconnect(self, close_code):
        # グループから退出
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """
        クライアントからのメッセージを処理する。
        ここでは、"undo_request", "undo_accepted", "undo_denied" の各メッセージタイプと、
        それ以外のゲーム更新メッセージを受け取り、グループにブロードキャストする仕組みを実装しています。
        """
        data = json.loads(text_data)
        message_type = data.get("type")

        if message_type == "undo_request":
            # 待ったリクエストを受信
            # 送信者（sender）が含まれていると仮定
            sender = data.get("sender")
            # ここでは、対局相手にのみ確認を促すため、
            # 自分がリクエストした場合は（sender == 自分のユーザー名）何もしない。
            print(f'sender:{sender}, username:{self.scope["user"].username}')
            # グループ内全員に undo_request をブロードキャストする
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "send_undo_request",
                    "sender": sender
                }
            )
        elif message_type == "undo_accepted":
            # 待ったが承認された場合、サーバー側で Undo 処理を実行する
            print("undo_accepted!!!")
            try:
                new_state = await sync_to_async(perform_undo_move)(self.match_id, self.scope["user"])
                print(f'new_state:{new_state}')
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        "type": "game_update",
                        "message": {
                            "board": new_state["board"],
                            "pieces_in_hand": new_state["pieces_in_hand"],
                            "turn": new_state["turn"],
                            "last_move": new_state["last_move"],
                            "action": "undo_move",
                            "type": "undo_success"
                        }
                    }
                )
            except Exception as e:
                await self.send(text_data=json.dumps({
                    "type": "undo_error",
                    "error": str(e)
                }))
        elif message_type == "undo_denied":
            # 待ったが拒否された場合
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "send_undo_denied"
                }
            )
        else:
            # その他のメッセージ（例: game_update や move_piece, drop_piece など）
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "game_update",
                    "message": data
                }
            )

    # グループからのメッセージを受け取るハンドラ
    async def game_update(self, event):
        message = event['message']
        # クライアントにメッセージを送信
        await self.send(text_data=json.dumps(message))

    # 待ったリクエスト用のハンドラ
    async def send_undo_request(self, event):
        # 送信者の名前を含む undo_request をクライアントに送信
        await self.send(text_data=json.dumps({
            "type": "undo_request",
            "sender": event.get("sender", "")
        }))

    # 待った承認用のハンドラ
    async def send_undo_accepted(self, event):
        await self.send(text_data=json.dumps({
            "type": "undo_accepted"
        }))

    # 待った拒否用のハンドラ
    async def send_undo_denied(self, event):
        await self.send(text_data=json.dumps({
            "type": "undo_denied"
        }))

    # 画面リロード指示用のハンドラ
    async def reload_game(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))


class MatchListConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "match_list"
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # グループからの更新メッセージを受信した際のハンドラ
    async def send_update(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))

    # 画面リロード指示用のハンドラ
    async def reload_game(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps(message))

