from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db.models import Q, Count
import json
from django.core.exceptions import PermissionDenied
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync, sync_to_async

from .models import Chat, Message
from accounts.models import User

@login_required
def inbox(request):
    user = request.user
    
    chats = Chat.objects.filter(
        participants=user
    ).exclude(
        chat_hidden_for=user
    ).annotate(
        message_count=Count('messages')
    ).filter(
        message_count__gt=0
    ).order_by('-created_at')
    
    chat_info = []
    for chat in chats:
        other_user = chat.participants.exclude(id=user.id).first()
        last_message = chat.messages.exclude(
            text_hidden_for=user
        ).order_by('-timestamp').first()

        # Get unread message count from this user
        unread_count = chat.messages.filter(
            sender=other_user
        ).exclude(
            read_by=user
        ).exclude(
            text_hidden_for=user
        ).count()
        
        chat_info.append({
            'chat': chat,
            'other_user': other_user,
            'last_message': last_message,
            'unread_count': unread_count,
        })

    return render(request, 'chat/inbox.html', {
        'chat_info': chat_info,
        'has_chats': chats.exists(),
    })

@login_required
def direct_msg(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    other_user = chat.get_other_participant(request.user)

    # Mark all messages in the chat as unread
    unread_texts = chat.messages.exclude(
        read_by=request.user
    ).exclude(
        sender=request.user
    )
    for text in unread_texts:
        text.mark_as_read(request.user)
    
    texts = chat.messages.exclude(
        text_hidden_for=request.user
    ).order_by('timestamp')
    
    return render(request, 'chat/direct_msg.html', {
        'chat': chat,
        'other_user': other_user,
        'texts': texts,
        'hide_notification': True,
    })

@login_required
@require_POST
def send_message(request):
    chat_id = request.POST.get('chat_id')
    content = request.POST.get('content')
    
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    other_user = chat.get_other_participant(request.user)
    
    text = Message.objects.create(
        chat=chat,
        sender=request.user,
        content=content
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'chat_{chat_id}',
        {
            'type': 'chat_message',
            'message': text.content,
            'sender': request.user.username,
            'timestamp': text.timestamp.strftime("%H:%M"),
            'user_id': str(request.user.id),
            'message_id': str(text.id),
            'is_sender': False,
            'chat_id': str(chat.id)
        }
    )

    # Notify recipients
    async_to_sync(channel_layer.group_send)(
        f'notifications_{other_user.id}',
        {
            'type': 'notify',
            'type': 'new_message',
            'sender': request.user.username,
            'sender_avatar': request.user.profile.profile_pic.url if hasattr(request.user, 'profile') and request.user.profile.profile_pic else '',
            'chat_id': chat_id,
            'content': content[:50] + '...' if len(content) > 50 else content
        }
    )
    
    return JsonResponse({
        'success': True,
        'message_id': text.id,
        'content': text.content,
        'timestamp': text.timestamp.strftime("%H:%M"),
        'sender': request.user.username,
    })

@login_required
@require_POST
def start_chat(request):
    data = json.loads(request.body)
    other_user_id = data.get('user_id')

    try:
        other_user = get_object_or_404(get_user_model(), id=other_user_id)

        # Check for any existing chat between these users
        existing_chat = Chat.objects.filter(
            participants=request.user
        ).filter(
            participants=other_user
        ).first()

        if existing_chat:
            # Remove chat from deleted_for to make it visible again
            existing_chat.chat_hidden_for.remove(request.user, other_user)

            # Mark all existing messages as deleted for the current user
            messages_to_delete = existing_chat.messages.exclude(
                text_hidden_for=request.user
            )
            for message in messages_to_delete:
                message.text_hidden_for.add(request.user)
            
            return JsonResponse({
                'success': True,
                'chat_id': existing_chat.id,
                'is_new': False,
                'has_messages': existing_chat.messages.exclude(text_hidden_for=request.user).exists()
            })

        # No existing chat found - create a new one
        chat = Chat.objects.create()
        chat.participants.add(request.user, other_user)

        return JsonResponse({
            'success': True,
            'chat_id': chat.id,
            'is_new': True,
            'has_messages': False
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
    
@login_required
def get_unread_count(request):
    unread_count = Message.objects.filter(
        chat__participants=request.user
    ).exclude(
        read_by=request.user
    ).exclude(
        sender=request.user
    ).exclude(
        text_hidden_for=request.user
    ).count()
    
    return JsonResponse({'unread_count': unread_count})

@login_required
@require_POST
def delete_text(request, text_id):
    try:
        text = get_object_or_404(Message, id=text_id)
        
        if not text.chat.participants.filter(id=request.user.id).exists():
            raise PermissionDenied("Not authorized")
        
        if text.sender == request.user:
            text.text_hidden_for.add(*text.chat.participants.all())
        else:
            text.text_hidden_for.add(request.user)
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def delete_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
    chat.chat_hidden_for.add(request.user)
    return JsonResponse({'success': True})

@login_required
def search_users(request):
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    User = get_user_model()
    users = User.objects.filter(
        username__icontains=query
    ).exclude(
        id=request.user.id
    ).select_related('profile')[:10]
    
    results = []
    for user in users:
        profile_pic_url = None
        if hasattr(user, 'profile') and user.profile.profile_pic:
            profile_pic_url = user.profile.profile_pic.url
        
        results.append({
            'id': user.id,
            'username': user.username,
            'profile_pic_url': profile_pic_url,
            'initials': user.username[0].upper() if user.username else '?'
        })
    
    return JsonResponse({'results': results})

@login_required
@require_POST
def edit_text(request, text_id):
    text = get_object_or_404(Message, id=text_id)
    
    if text.sender != request.user:
        return JsonResponse({'success': False, 'error': 'You can only edit your own messages'}, status=403)
    
    if text.text_hidden_for.count() > 0:
        return JsonResponse({'success': False, 'error': 'Cannot edit deleted texts'}, status=400)
    
    content = request.POST.get('content')
    if not content:
        return JsonResponse({'success': False, 'error': 'Message cannot be empty'}, status=400)
    
    # Update message
    text.content = content
    text.edited = True 
    text.save()
    
    return JsonResponse({
        'success': True,
        'content': text.content,
        'timestamp': text.timestamp.strftime("%H:%M"),
        'edited': True,
    })