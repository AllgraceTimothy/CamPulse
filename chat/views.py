from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.models import User

from .models import Chat, Message, MessageVisibility, HiddenChat
from accounts.models import Profile

@login_required
def inbox(request):
    user = request.user
    search_query = request.GET.get('q', '')

    hidden_chat_ids = HiddenChat.objects.filter(user=user).values_list('chat_id', flat=True)
    chats = Chat.objects.filter(participants=user).exclude(deleted_for=request.user).order_by('-created_at')

    chat_info = []
    for chat in chats:
        other_users = chat.participants.exclude(id=user.id)
        last_message = chat.messages.filter(deleted_for_all=False).select_related('sender').order_by('-timestamp').first()

        chat_info.append({
            'chat': chat,
            'others': other_users,
            'last_message': last_message,
        })

    results = []
    if search_query:
        results = User.objects.filter(username__icontains=search_query).exclude(id=user.id)

    return render(request, 'chat/inbox.html', {
        'chat_info': chat_info,
        'search_query': search_query,
        'results': results,
    })


@login_required
def direct_msg(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)

    visible_messages = (
        Message.objects.filter(
            chat=chat,
            deleted_for_all=False
        )
        .exclude(
            visibility__user=request.user,
            visibility__visible=False
        )
        .select_related('sender')
        .prefetch_related('visibility')
        .order_by('timestamp')
    )

    return render(request, 'chat/direct_msg.html', {
        'chat': chat,
        'texts': visible_messages,
    })


@login_required
@require_POST
def send_message(request):
    chat_id = request.POST.get('chat_id')
    content = request.POST.get('content')

    chat = get_object_or_404(Chat, id=chat_id, participants=request.user)

    message = Message.objects.create(
        chat=chat,
        sender=request.user,
        content=content,
        timestamp=timezone.now()
    )

    # Set visibility for all participants
    for participant in chat.participants.all():
        MessageVisibility.objects.create(text=message, user=participant)

    return JsonResponse({
        'success': True,
        'text_id': message.id,
        'content': message.content,
        'timestamp': message.timestamp.strftime("%H:%M"),
        'sender': request.user.username,
    })


@login_required
@require_POST
def start_chat(request):
    other_user_id = request.POST.get('user_id')
    other_user = get_object_or_404(User, id=other_user_id)

    existing_chat = Chat.objects.filter(participants=request.user).filter(participants=other_user).first()
    if existing_chat:
        return redirect('direct_msg', chat_id=existing_chat.id)

    chat = Chat.objects.create()
    chat.participants.add(request.user, other_user)

    return redirect('direct_msg', chat_id=chat.id)


@login_required
@require_POST
def delete_message(request, text_id):
    message = get_object_or_404(Message, id=text_id)

    if message.sender == request.user:
        message.content = "[This message was deleted]"
        message.deleted_for_all = True
        message.save()
    else:
        # Soft delete: only hide from this user
        visibility, created = MessageVisibility.objects.get_or_create(
            text=message,
            user=request.user
        )
        visibility.visible = False
        visibility.save()

    return JsonResponse({'success': True})

@login_required
def delete_chat(request, chat_id):
    chat = get_object_or_404(Chat, id=chat_id)

    if request.user in chat.participants.all():
        chat.deleted_for.add(request.user)

    return redirect('inbox')

@login_required
@require_POST
def edit_text(request, text_id):
    text = get_object_or_404(Message, id=text_id)

    if text.sender != request.user:
        return JsonResponse({'success': False, 'error': 'You are not authorized to edit this text'})
    new_content = request.POST.get('content')

    if new_content:
        text.content = new_content
        text.edited = True
        text.save()

        for participant in text.chat.participants.all():
            visibility, created = MessageVisibility.objects.get_or_create(text=text, user=participant)
            visibility.visible = True
            visibility.save()

        return JsonResponse({'success': True, 'content': new_content, 'timestamp': text.timestamp.strftime("%H:%M")})
    
    return JsonResponse({'success': False, 'error': 'Content cannot be empty.'})

@login_required
@require_POST
def forward_text(request, text_id, target_chat_id):
    text = get_object_or_404(Message, id=text_id)
    target_chat = get_object_or_404(Chat, id=target_chat_id)

    if request.user not in target_chat.participants.all():
        return JsonResponse({'success': False, 'error': 'You must be part of the target chat.'})

    # Create a new forwarded message in the target chat
    forwarded_text = Message.objects.create(
        chat=target_chat,
        sender=request.user,
        content=text.content,
        timestamp=timezone.now()
    )

    # Set visibility for all participants in the target chat
    for participant in target_chat.participants.all():
        MessageVisibility.objects.create(text=forwarded_text, user=participant)

    return JsonResponse({
        'success': True,
        'content': forwarded_text.content,
        'sender': request.user.username,
        'timestamp': forwarded_text.timestamp.strftime("%H:%M"),
    })

@login_required
def available_chats(request):
    # Get all chats the user is part of, excluding the current chat if needed
    user_chats = Chat.objects.filter(participants=request.user).exclude(id=request.GET.get('exclude', 0))
    
    chats_data = []
    for chat in user_chats:
        # Customize this based on your chat model structure
        chats_data.append({
            'id': chat.id,
            'participants': [
                {'id': p.id, 'username': p.username} 
                for p in chat.participants.exclude(id=request.user.id)
            ]
        })
    
    return JsonResponse({'chats': chats_data})
