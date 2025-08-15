from django import forms
from django.db import models
from pymysql import IntegrityError

class User(models.Model):
    full_name = models.CharField(max_length=100)              # Họ tên
    email = models.EmailField(unique=True)                    # Email duy nhất
    password = models.CharField(max_length=255)               # Mật khẩu (nếu tự quản lý, cần hash)
    bio = models.TextField(blank=True, null=True)              # Giới thiệu
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)  # Ảnh đại diện
    date_of_birth = models.DateField(blank=True, null=True)    # Ngày sinh
    gender = models.CharField(
        max_length=10,
        choices=[('male', 'Nam'), ('female', 'Nữ'), ('other', 'Khác')],
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)       # Ngày tạo tài khoản
    
    def get_friends(self):
        friendships = Friendship.objects.filter(
        models.Q(user1=self) | models.Q(user2=self),  # SELECT * FROM friendship WHERE (user1_id = self.id OR user2_id = self.id) AND status = 'accepted';
        status='accepted'
    )
        friends = []
        for f in friendships:
            if f.user1 == self:
                friends.append(f.user2)
            else:
                friends.append(f.user1)
        return friends
    
    def get_friends_count(self):
        return len(self.get_friends())
    
    def send_friend_request(self, other_user):
        """
        Gửi lời mời kết bạn tới other_user.
        Trả về True nếu gửi thành công, False nếu đã tồn tại hoặc lỗi.
        """
        # Kiểm tra nếu đã có mối quan hệ tồn tại (pending hoặc accepted)
        existing = Friendship.objects.filter(
            models.Q(user1=self, user2=other_user) |
            models.Q(user1=other_user, user2=self)
        ).first()

        if existing:
            # Đã có request hoặc đã là bạn → không tạo mới
            return False

        try:
            Friendship.objects.create(
                user1=self,
                user2=other_user,
                status="pending"
            )
            return True
        except IntegrityError:
            return False
    

class Posts(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    content = models.TextField(blank=True, null=True)
    media = models.ImageField(upload_to='posts/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likeCount = models.IntegerField(default=0)
    commentCount = models.IntegerField(default=0)
    
class PostLike(models.Model):
    post = models.ForeignKey(Posts, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')  # 1 người chỉ like 1 lần
        
class Comment(models.Model):
    post = models.ForeignKey(Posts, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    

class PostForm(forms.ModelForm):
    class Meta:
        model = Posts
        fields = ['content','media']
        

class ProfileEditForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',  # HTML5 date picker (calendar)
            'class': 'form-control',
        })
    )
    
    gender = forms.ChoiceField(
        choices=[('', 'Chọn giới tính')] + list(User._meta.get_field('gender').choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = ['full_name', 'bio', 'date_of_birth', 'avatar', 'gender']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Họ và tên'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Giới thiệu về bạn'}),
            'avatar': forms.ClearableFileInput(attrs={'class': 'form-control-file'}),
        }  

    
class Friendship(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_initiated')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships_received')
    created_at = models.DateTimeField(auto_now_add=True)  # Ngày trở thành bạn
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Chờ xác nhận'),
            ('accepted', 'Đã chấp nhận'),
        ],
        default='pending'
    )

    class Meta:
        unique_together = ('user1', 'user2')  # Tránh trùng cặp bạn bè
        
    def save(self, *args, **kwargs):
        # Đảm bảo luôn lưu theo thứ tự ID tăng dần
        if self.user1_id > self.user2_id:
            self.user1, self.user2 = self.user2, self.user1
        super().save(*args, **kwargs)
