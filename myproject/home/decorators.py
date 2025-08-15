from django.shortcuts import redirect
from functools import wraps
from .models import User

def login_required_session(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get('user_id')
        if not user_id:
            return redirect('login')
        try:
            request.user_obj = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
