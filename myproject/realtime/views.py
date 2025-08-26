from django.shortcuts import render

# Create your views here.
# myapp/views.py
from django.shortcuts import get_object_or_404,redirect
from django.http import JsonResponse
from home.models import Posts,PostLike,PostComment,User
from .utils import send_notification
from django.contrib.auth.decorators import login_required
from .models import Notification
from django.template.loader import render_to_string

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
def add_comment(request, post_id):
    try:
        post = Posts.objects.get(id=post_id)
    except Posts.DoesNotExist:
        return JsonResponse({"error": "Post not found"}, status=404)

    content = request.POST.get("content", "").strip()
    parent_id = request.POST.get("parent_id")  # Nếu là reply
    image = request.FILES.get("image")  # file ảnh

    parent = None
    if parent_id:
        try:
            parent = PostComment.objects.get(id=parent_id, post=post)
        except PostComment.DoesNotExist:
            return JsonResponse({"error": "Parent comment not found"}, status=404)

    # Tạo comment mới
    comment = PostComment.objects.create(
        post=post,
        user=request.user,
        content=content,
        image=image if image else None,
        parent=parent
    )

    # Tăng commentCount của post
    post.commentCount = (post.commentCount or 0) + 1
    post.save(update_fields=['commentCount'])

    # Gửi noti cho chủ bài viết (nếu không phải tự comment)
    if post.user != request.user:
        send_notification(
            user=post.user,
            message=f"💬 {request.user.full_name} đã bình luận bài viết của bạn",
            post=post,
            comment=comment,
        )

    # render partial template
    html = render_to_string("base/comment_item.html", {"c": comment}, request=request)

    return JsonResponse({
        "success": True,
        "html": html,
        "commentCount": post.commentCount
    })




@login_required(login_url='login')
def add_friend(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)

    success = request.user.send_friend_request(other_user)

    # Redirect về lại trang gốc
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER", "/")

    if success:
        # Gọi hàm tiện ích gửi notification
        send_notification(
            user=other_user,
            sender=request.user,
            message=f"👥 {request.user.full_name} đã gửi cho bạn lời mời kết bạn.",
            post=None,
            comment=None
        )

    return redirect(next_url)















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
