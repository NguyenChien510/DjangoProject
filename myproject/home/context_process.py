from django.http import JsonResponse
from realtime.models import Notification
from django.contrib.auth.decorators import login_required

def notifications(request):
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
        unread_count = notifications.filter(is_read=False).count()
    else:
        notifications = []
        unread_count = 0
    return {
        'notifications': notifications,
        'unread_count': unread_count
    }
    
