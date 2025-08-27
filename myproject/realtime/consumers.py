# myapp/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from .utils import get_user_status  # dùng chung


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_authenticated:
            self.group_name = f"user_{self.scope['user'].id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        await self.send(text_data=json.dumps(event))
        


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"chat_{self.room_name}"

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        user = self.scope["user"]
        if user.is_authenticated:
            await self.set_user_online(user)

        await self.accept()

        # Broadcast status update
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "status_message",
                "status": get_user_status(user)
            }
        )

    async def disconnect(self, close_code):
        user = self.scope["user"]
        if user.is_authenticated:
            await self.set_user_offline(user)

            # Broadcast offline status
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "status_message",
                    "status": get_user_status(user)
                }
            )

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']

        user = self.scope["user"]
        sender_name = user.username if user.is_authenticated else "Ẩn danh"

        # Broadcast tới group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": message,
                "sender": sender_name
            }
        )

    async def chat_message(self, event):
        message = event["message"]
        sender = event["sender"]

        await self.send(text_data=json.dumps({
            "type": "chat_message",
            "message": message,
            "sender": sender,
            "is_self": sender == self.scope["user"].username
        }))

    async def status_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "status_update",
            "status": event["status"]
        }))

    async def set_user_online(self, user):
        user.is_online = True
        user.last_seen = timezone.now()
        await sync_to_async(user.save)()

    async def set_user_offline(self, user):
        user.is_online = False
        user.last_seen = timezone.now()
        await sync_to_async(user.save)()

