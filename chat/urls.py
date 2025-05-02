from django.urls import path
from . import views

urlpatterns = [
    path('', views.inbox, name='inbox'),
    path('chat/<int:chat_id>/', views.direct_msg, name='direct_msg'),
    path('send-message/', views.send_message, name='send_message'),
    path('new/', views.start_chat, name='start_chat'),
    path('text/<int:text_id>/delete/', views.delete_message, name='delete_message'),
    path('text/<int:text_id>/edit/', views.edit_text, name='edit_text'),
    path('delete-chat/<int:chat_id>/', views.delete_chat, name='delete_chat'),
    path('messages/<int:text_id>/forward/<int:target_chat_id>/', views.forward_text, name='forward_message'),
    path('api/chats/available/', views.available_chats, name='available_chats'),
]
