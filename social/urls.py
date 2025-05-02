from django.urls import path
from .views import my_posts_view, post_edit, post_delete, like_post, add_comment

urlpatterns = [
    path('my_posts/', my_posts_view, name='my_posts'),
    path('posts/<int:post_id>/', post_edit, name='post_edit'),
    path('posts/<int:pk>/delete/', post_delete, name='post_delete'),
    path('like/<int:post_id>/', like_post, name='like_post'),
    path('comment/<int:post_id>/', add_comment, name='add_comment'),
]
