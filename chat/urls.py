from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('conv/<int:chat_id>/', views.direct_msg, name='direct_msg'),
    path('send-message/', views.send_message, name='send_message'),
    path('start-chat/', views.start_chat, name='start_chat'),
    path('delete-text/<int:text_id>/', views.delete_text, name='delete_text'),
    path('delete-chat/<int:chat_id>/', views.delete_chat, name='delete_chat'),
    path('search-users/', views.search_users, name='search_users'),
    path('edit-text/<int:text_id>/', views.edit_text, name='edit_text'),
    path('get_unread_count/', views.get_unread_count, name='get_unread_count'),
]
