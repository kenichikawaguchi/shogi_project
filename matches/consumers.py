import json
from channels.generic.websocket import AsyncWebsocketConsumer

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
    
    # クライアントからのメッセージを受け取った場合（必要に応じて実装）
    async def receive(self, text_data):
        # ここでは主にサーバーからのブロードキャストを行うので、receive はオーバーライドしなくてもよい
        data = json.loads(text_data)
        # 例：メッセージをグループに再送信する場合
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'game_update',
                'message': data
            }
        )
    
    # グループからのメッセージを受け取るハンドラ
    async def game_update(self, event):
        message = event['message']
        # クライアントにメッセージを送信
        await self.send(text_data=json.dumps(message))

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

