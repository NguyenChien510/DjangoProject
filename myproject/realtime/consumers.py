# myapp/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from channels.db import database_sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        """Kết nối WebSocket cho thông báo realtime"""
        if self.scope["user"].is_authenticated:
            self.group_name = f"user_{self.scope['user'].id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        """Ngắt kết nối"""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        """Gửi thông báo xuống client"""
        await self.send(text_data=json.dumps(event))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conv_id = self.scope['url_route']['kwargs']['conv_id']
        self.group_name = f"chat_{self.conv_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()  # KHÔNG cập nhật online/offline ở đây

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message", "").strip()
        user = self.scope["user"]

        if not user.is_authenticated or not message:
            return

        saved = await self.save_message(user_id=user.id, conv_id=self.conv_id, text=message)
    
            # Lấy avatar URL trong async context
        avatar_url = await database_sync_to_async(
        lambda: user.avatar.url if user.avatar else None
        )()
    
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

    async def chat_message(self, event):
        
        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": event["message"],
            "sender_id": event["sender_id"],
            "sender_name": event["sender_name"],
            "time": event["time"],
            "is_self": event["sender_id"] == getattr(self.scope["user"], "id", None),
            "avatar": event.get("avatar"), 
        }))

    @database_sync_to_async
    def save_message(self, user_id, conv_id, text):
        from home.models import Conversation, Message, User
        conv = Conversation.objects.get(id=conv_id)

        # Chặn gửi nếu user không thuộc cuộc trò chuyện
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