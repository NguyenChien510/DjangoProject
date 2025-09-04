import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Kết nối WebSocket cho thông báo realtime"""
        self.user = self.scope["user"]

        if self.user.is_authenticated:
            # Group cho từng user
            self.group_name = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        """Ngắt kết nối"""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        """Gửi notification xuống client"""
        await self.send(text_data=json.dumps({
            "type": "notification",
            "message": event.get("message"),
            "extra": event.get("extra", {})
        }))

    async def chat_list_update(self, event):
        """Update preview chat list cho user"""
        await self.send(text_data=json.dumps({
            "type": "chat_list_update",
            "conv_id": event["conv_id"],
            "last_text": event["last_text"],
            "time": event["time"],
            "sender_id": event["sender_id"],
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Kết nối WebSocket cho một cuộc trò chuyện"""
        self.conv_id = self.scope['url_route']['kwargs']['conv_id']
        self.group_name = f"chat_{self.conv_id}"
        self.user = self.scope["user"]

        # Tham gia group conversation
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """Ngắt kết nối"""
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Nhận tin nhắn từ client"""
        data = json.loads(text_data)
        message = data.get("message", "").strip()
        user = self.user

        if not user.is_authenticated or not message:
            return

        # Lưu DB
        saved = await self.save_message(user_id=user.id, conv_id=self.conv_id, text=message)

        # Avatar của sender (nếu có)
        avatar_url = await database_sync_to_async(
            lambda: user.avatar.url if getattr(user, "avatar", None) else None
        )()

        # 1. Gửi tin nhắn cho group conversation
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "message": saved["text"],
                "sender_id": saved["sender_id"],
                "sender_name": saved["sender_name"],
                "time": saved["time"],
                "avatar": avatar_url,
            }
        )

        # 2. Gửi update chat list cho cả 2 user trong conversation
        from home.models import Conversation
        conv = await database_sync_to_async(Conversation.objects.get)(id=self.conv_id)
        participants = [conv.user1_id, conv.user2_id]

        for uid in participants:
            await self.channel_layer.group_send(
                f"user_{uid}",
                {
                    "type": "chat_list_update",
                    "conv_id": self.conv_id,
                    "last_text": saved["text"],
                    "time": saved["time"],
                    "sender_id": saved["sender_id"],
                }
            )

    async def chat_message(self, event):
        """Đẩy tin nhắn xuống client"""
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "time": event["time"],
            "is_self": event["sender_id"] == getattr(self.user, "id", None),
            "avatar": event.get("avatar"),
        }))

    @database_sync_to_async
    def save_message(self, user_id, conv_id, text):
        """Lưu tin nhắn xuống DB"""
        from home.models import Conversation, Message, User
        conv = Conversation.objects.get(id=conv_id)

        # Chặn gửi nếu user không thuộc conversation
        if user_id not in [conv.user1_id, conv.user2_id]:
            raise PermissionError("User không thuộc conversation này")

        user = User.objects.get(id=user_id)
        msg = Message.objects.create(conversation=conv, sender=user, text=text)
        return {
            "text": msg.text,
            "sender_id": user.id,
            "sender_name": getattr(user, "full_name", user.username),
            "time": msg.created_at.strftime("%H:%M"),
        }
