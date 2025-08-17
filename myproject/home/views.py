from imaplib import _Authenticator
import random
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from realtime.models import Notification
from .models import Friendship, PostComment, PostForm, PostLike, ProfileEditForm, User
from .models import Posts
from django.contrib.auth.hashers import make_password
from django.contrib.auth import logout,authenticate,login as auth_login
from django.db.models import Q
from django.contrib.auth.decorators import login_required

# Create your views here.
def logout_view(request):
    logout(request)  # Xóa toàn bộ session + đăng xuất user
    return redirect('login')  # Chuyển về trang login

def login(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'sign_up':
            name = request.POST.get('fullname')
            email = request.POST.get('email')
            password = request.POST.get('password')

            if User.objects.filter(email=email).exists():
                messages.error(request, "Email đã được đăng ký!")
                return render(request, 'login/login.html')

            User.objects.create_user(email=email, full_name=name, password=password)
            messages.success(request, "Đăng ký thành công! Vui lòng đăng nhập.")
            return redirect('login')

        elif form_type == 'sign_in':
            email = request.POST.get('email')
            password = request.POST.get('password')

            from django.contrib.auth import authenticate, login as auth_login
            user = authenticate(request, email=email, password=password)
            if user is not None:
                auth_login(request, user)
                return redirect('home')
            else:
                messages.error(request, "Email hoặc mật khẩu không đúng!")

    return render(request, 'login/login.html')


@login_required(login_url='login')
def home(request):
    posts = list(Posts.objects.all())
    random.shuffle(posts)
    posts = posts[:100]
    
    liked_posts = set(
        PostLike.objects.filter(user=request.user)
                        .values_list('post_id', flat=True)
    )
    
    context = {
        'user' : request.user,
        'posts': posts,
        'user_liked_posts':liked_posts,
    }
    
    return render(request,'home/home.html',context)

@login_required(login_url='login')
def create_post(request):
    form = PostForm(request.POST, request.FILES)
    if form.is_valid():
        post = form.save(commit=False)
        post.user = request.user
        post.save()
    return redirect('home')

@login_required(login_url='login')
def profile_view(request, user_id =None):
    if(user_id):
        profile_user = get_object_or_404(User,id=user_id)
    else:
        profile_user = get_object_or_404(User,id=request.user.id)
    
    posts = Posts.objects.filter(user = profile_user).order_by('-created_at')
    
    form = ProfileEditForm(instance=request.user)
    
    relationship = Friendship.objects.filter(
        Q(user1=request.user, user2=profile_user) |
        Q(user1=profile_user, user2=request.user)
    ).first()
    friendship_status = None
    if relationship:
        friendship_status = relationship.status  # 'pending' hoặc 'accepted'
        friendship_sender_id = relationship.user1.id
    else:
        friendship_status = None
        friendship_sender_id = None
        
        
    friendships = Friendship.objects.filter(
        status='accepted'
    ).filter(
        Q(user1=profile_user) | Q(user2=profile_user)
    )

    friends = []
    for f in friendships:
        friend = f.user2 if f.user1 == profile_user else f.user1
        friends.append({
            'name': friend.full_name,
            'avatar': friend.avatar.url if friend.avatar else None,
            'id': friend.id,
        })
        
    liked_posts = set(
        PostLike.objects.filter(user=request.user)
                        .values_list('post_id', flat=True)
    )    
    
    highlight_post_id = request.GET.get('highlight')
    
    context = {
        'profile_user': profile_user,
        'current_user': request.user,
        'posts': posts,
        'user_liked_posts':liked_posts,
        'form': form,
        'friendship_status': friendship_status,
        'friendship_sender_id': friendship_sender_id,
        'friends':friends,
        'highlight_post_id': highlight_post_id, 
    }
    return render(request,'personal/personal.html',context)

@login_required(login_url='login')
def edit_profile(request):
    form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
    if form.is_valid():
        form.save()
            # Có thể thêm messages nếu muốn
    else:
        # Xử lý lỗi nếu cần, hoặc bỏ qua
        pass
    return redirect('personal')

@login_required(login_url='login')
def add_friend(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)

    success = request.user.send_friend_request(other_user)
    if not success:
        # Nếu đã có request hoặc là bạn rồi → reload lại trang trước
        return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect('personal_with_id', user_id=other_user.id)

@login_required(login_url='login')
def accpet_request(request,user_id):
    other_user = get_object_or_404(User, pk=user_id)

    # Chỉ xử lý khi có lời mời kết bạn từ other_user → request.user
    friendship = Friendship.objects.filter(
        user1=other_user,
        user2=request.user,
        status='pending'
    ).first()

    if friendship:
        friendship.status = 'accepted'
        friendship.save()

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required(login_url='login')
def cancel_request(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    Friendship.objects.filter(
        Q(user1=request.user, user2=other_user, status='pending') |
        Q(user1=other_user, user2=request.user, status='pending')
    ).delete()
    return redirect('personal_with_id', user_id=other_user.id)

@login_required(login_url='login')
def delete_friend(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    Friendship.objects.filter(
        Q(user1=request.user, user2=other_user, status='accepted') |
        Q(user1=other_user, user2=request.user, status='accepted')
    ).delete()
    return redirect('personal_with_id', user_id=other_user.id)


def friends_list_view(request):
    # Lấy các friendship đã được chấp nhận
    friendships = Friendship.objects.filter(
        status='accepted'
    ).filter(
        (Q(user1=request.user) | Q(user2=request.user))
    )

    friends = []
    for f in friendships:
        # Nếu user hiện tại là user1 thì bạn là user2, ngược lại thì bạn là user1
        friend = f.user2 if f.user1 == request.user else f.user1
        friends.append({
            'name': friend.get_full_name() or friend.username,
            'initials': ''.join([p[0].upper() for p in (friend.get_full_name() or friend.username).split()]),
        })

    return render(request, 'friends_modal.html', {'friends': friends})



@login_required(login_url='login')
def delete_post(request, post_id):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Phương thức không hợp lệ'})

    try:
        post = Posts.objects.get(id=post_id)
    except Posts.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Bài viết không tồn tại'})

    # Chỉ cho user chủ bài xóa
    if post.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Bạn không có quyền xóa bài viết này'})

    post.delete()
    return JsonResponse({'status': 'ok'})


def get_comments(request, post_id):
    comments = PostComment.objects.filter(post_id=post_id).select_related("user").order_by("-created_at")
    return render(request, "base/comments_list.html", {"comments": comments})


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

    return JsonResponse({
        "id": comment.id,
        "user": request.user.full_name,
        "avatar": request.user.avatar.url if hasattr(request.user, "avatar") and request.user.avatar else None,
        "content": comment.content,
        "image": comment.image.url if comment.image else None,
        "created_at": comment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "likeCount": comment.likeCount,
        "parent_id": comment.parent.id if comment.parent else None,
    })

