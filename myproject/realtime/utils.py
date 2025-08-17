# myapp/utils.py
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from home.models import Posts

from realtime.consumers import NotificationConsumer
from .models import Notification


def send_notification(user, message, post=None):
    # Tạo noti
    notification = Notification.objects.create(user=user, message=message, post=post)

    layer = get_channel_layer()
    async_to_sync(layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "id": notification.id,
            "message": message,
            "post_id": notification.post.id if notification.post else None,
            "count": Notification.objects.filter(user=user, is_read=False).count(),
        }
    )