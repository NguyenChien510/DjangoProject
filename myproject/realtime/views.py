from django.shortcuts import render

# Create your views here.
# myapp/views.py
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from home.models import Posts,PostLike
from .utils import send_notification
from django.contrib.auth.decorators import login_required
from .models import Notification

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Posts, id=post_id)

    # Kiểm tra đã like chưa
    existing_like = PostLike.objects.filter(post=post, user=request.user).first()

    if existing_like:
        # Nếu đã like → unlike
        existing_like.delete()
        post.likeCount = PostLike.objects.filter(post=post).count()
        post.save(update_fields=["likeCount"])
        return JsonResponse({
            "status": "unliked",
            "likeCount": post.likeCount
        })
    else:
        # Nếu chưa like → like
        PostLike.objects.create(post=post, user=request.user)
        post.likeCount = PostLike.objects.filter(post=post).count()
        post.save(update_fields=["likeCount"])

        # Chỉ gửi noti nếu người like KHÔNG phải là chủ bài viết
        if post.user != request.user:
            send_notification(
                user=post.user,
                message=f"❤️ {request.user.full_name} đã thích bài viết của bạn",
                post =post
            )

        return JsonResponse({
            "status": "liked",
            "likeCount": post.likeCount
        })


@login_required
def mark_notification_read(request):
    notification_id = request.GET.get('id')
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return JsonResponse({'status': 'ok'})
    except Notification.DoesNotExist:
        return JsonResponse({'status': 'error'})
