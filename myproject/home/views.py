from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from pymysql import IntegrityError
from .models import Friendship, PostForm, ProfileEditForm, User
from .models import Posts
from django.contrib.auth.hashers import check_password
from django.contrib.auth.hashers import make_password
from django.contrib.auth import logout
from .decorators import login_required_session
from django.db.models import Q

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
            
             # check email is existed
            if User.objects.filter(email=email).exists():
                messages.error(request, "Email đã được đăng ký!")
                return render(request, 'login/login.html')
            
            password_hash = make_password(password)
            User.objects.create(email=email,full_name=name,password=password_hash)
            messages.success(request, "Đăng ký thành công! Vui lòng đăng nhập.")
            return redirect('login')
            
        elif form_type == 'sign_in':
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            try:
                user = User.objects.get(email=email)
                if check_password(password, user.password):
                    request.session['user_id'] = user.id
                    return redirect('home')
                else:
                    messages.error(request, "Mật khẩu không đúng!")
            except User.DoesNotExist:
                messages.error(request, "Email không tồn tại!")
    return render(request,'login/login.html')

@login_required_session
def home(request):
    return render(request,'home/home.html',{'user':request.user_obj})

# @login_required_session
# def personal(request):    
#     return render(request, 'personal/personal.html', {'user': request.user_obj})

@login_required_session
def create_post(request):
    form = PostForm(request.POST, request.FILES)
    if form.is_valid():
        post = form.save(commit=False)
        post.user = request.user_obj
        post.save()
    return redirect('home')

@login_required_session
def profile_view(request, user_id =None):
    if(user_id):
        profile_user = get_object_or_404(User,id=user_id)
    else:
        profile_user = get_object_or_404(User,id=request.user_obj.id)
    
    posts = Posts.objects.filter(user = profile_user).order_by('-created_at')
    
    form = ProfileEditForm(instance=request.user_obj)
    
    relationship = Friendship.objects.filter(
        Q(user1=request.user_obj, user2=profile_user) |
        Q(user1=profile_user, user2=request.user_obj)
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
        
    context = {
        'profile_user': profile_user,
        'current_user': request.user_obj,
        'posts': posts,
        'form': form,
        'friendship_status': friendship_status,
        'friendship_sender_id': friendship_sender_id,
        'friends':friends,
    }
    return render(request,'personal/personal.html',context)

@login_required_session
def edit_profile(request):
    form = ProfileEditForm(request.POST, request.FILES, instance=request.user_obj)
    if form.is_valid():
        form.save()
            # Có thể thêm messages nếu muốn
    else:
        # Xử lý lỗi nếu cần, hoặc bỏ qua
        pass
    return redirect('personal')

@login_required_session
def add_friend(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)

    success = request.user_obj.send_friend_request(other_user)
    if not success:
        # Nếu đã có request hoặc là bạn rồi → reload lại trang trước
        return redirect(request.META.get('HTTP_REFERER', '/'))

    return redirect('personal_with_id', user_id=other_user.id)

@login_required_session
def accpet_request(request,user_id):
    other_user = get_object_or_404(User, pk=user_id)

    # Chỉ xử lý khi có lời mời kết bạn từ other_user → request.user_obj
    friendship = Friendship.objects.filter(
        user1=other_user,
        user2=request.user_obj,
        status='pending'
    ).first()

    if friendship:
        friendship.status = 'accepted'
        friendship.save()

    return redirect(request.META.get('HTTP_REFERER', '/'))


@login_required_session
def cancel_request(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    Friendship.objects.filter(
        Q(user1=request.user_obj, user2=other_user, status='pending') |
        Q(user1=other_user, user2=request.user_obj, status='pending')
    ).delete()
    return redirect('personal_with_id', user_id=other_user.id)

@login_required_session
def delete_friend(request, user_id):
    other_user = get_object_or_404(User, pk=user_id)
    Friendship.objects.filter(
        Q(user1=request.user_obj, user2=other_user, status='accepted') |
        Q(user1=other_user, user2=request.user_obj, status='accepted')
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