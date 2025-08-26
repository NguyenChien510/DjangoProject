from django.urls import path
from . import views
from realtime import views as viewrealtime
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('',views.login , name='login'),
    path('logout/',views.logout_view,name = 'logout'),
    path('home',views.home, name='home'),
    path('personal',views.profile_view,name='personal'),
    path('personal/<int:user_id>/', views.profile_view, name='personal_with_id'),
    path('createpost',views.create_post,name='create_post'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('addfriend/<int:user_id>/',viewrealtime.add_friend,name='add_friend'),
    path('cancel_request/<int:user_id>/',views.cancel_request,name='cancel_request'),
    path('deletefriend/<int:user_id>/',views.delete_friend,name='delete_friend'),
    path('acceptrequest/<int:user_id>/',views.accept_request,name = 'accept_request'),
    path('delete_post/<int:post_id>/',views.delete_post,name='delete_post'),
    path('like/<int:post_id>/',viewrealtime.like_post,name='like_post'),
    path('mark_notification_read/', viewrealtime.mark_notification_read, name='mark_notification_read'),
    path('get-comments/<int:post_id>/', views.get_comments, name='get_comments'),
    path("delete_comment/<int:comment_id>/", views.delete_comment, name="delete_comment"),
    
    
    path('postdetail/<int:post_id>', views.profile_view, name='post_detail'),
    path('add-comment/<int:post_id>/', viewrealtime.add_comment, name='add_comment'),
    path('findfriend',views.findfriend,name='findfriend'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)