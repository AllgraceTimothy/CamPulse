import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Chat, Message
from datetime import datetime
from channels.layers import get_channel_layer
from social.models import Post
from django.core.exceptions import ObjectDoesNotExist

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        if self.user.is_anonymous:
            await self.close()
        else:
            self.group_name = f'notifications_{self.user.id}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
    async def notify(self, event):
        notification_type = event.get('notification_type')
        
        if notification_type == 'new_message':
            await self.send(text_data=json.dumps({
                'type': 'new_message',
                'sender': event.get('sender'),
                'sender_avatar': event.get('sender_avatar') or '/static/default-avatar.png',
                'content': event.get('content'),
                'chat_id': event.get('chat_id')
            }))
        elif notification_type == 'post_like':
            await self.send(text_data=json.dumps({
                'type': 'post_like',
                'liker': event.get('liker'),
                'liker_avatar': event.get('liker_avatar') or '/static/default-avatar.png',
                'post_content': event.get('post_content'),
                'post_id': event.get('post_id')
            }))

@database_sync_to_async
def get_user_profile_pic(user):
    try:
        if hasattr(user, 'profile') and user.profile.profile_pic:
            return user.profile.profile_pic.url
    except ObjectDoesNotExist:
        pass
    return ''

@database_sync_to_async
def get_sender_profile_pic(sender_username):
    try:
        user = User.objects.get(username=sender_username)
        if hasattr(user, 'profile') and user.profile.profile_pic:
            return user.profile.profile_pic.url
    except (User.DoesNotExist, ObjectDoesNotExist):
        pass
    return ''

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.user = self.scope["user"]
        
        if self.user.is_anonymous:
            await self.close(code=4001)
            return

        try:
            self.chat = await self.get_chat()
            if not await self.is_participant():
                await self.close(code=4003)
                return
        except Exception as e:
            print(f"Connection error: {e}")
            await self.close(code=4002)
            return

        self.group_name = f'chat_{self.chat_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        print(f"WebSocket CONNECTED: {self.user.username} to chat {self.chat_id}")
        async def send_ping(self):
            while True:
                try:
                    await self.send(json.dumps({'type': 'ping'}))
                    await asyncio.sleep(20)  # Send ping every 20 seconds
                except:
                    break

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    @database_sync_to_async
    def get_chat(self):
        try:
            return Chat.objects.get(id=self.chat_id)
        except Chat.DoesNotExist:
            return None

    @database_sync_to_async
    def is_participant(self):
        return self.chat.participants.filter(id=self.user.id).exists()
    
    @database_sync_to_async
    def get_other_participant(self):
        return self.chat.participants.exclude(id=self.user.id).first()

    @database_sync_to_async
    def save_message(self, content):
        return Message.objects.create(
            chat=self.chat,
            sender=self.user,
            content=content,
            timestamp=datetime.now()
        )
    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.get(id=user_id)

    @database_sync_to_async
    def get_post(self, post_id):
        return Post.objects.get(id=post_id)

    @database_sync_to_async
    def get_post_author(self, post):
        return post.author

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                # Handle chat message
                message = data['message']
                db_message = await self.save_message(message)
                
                # Notify chat participants
                await self.channel_layer.group_send(
                    self.group_name,
                    {
                        'type': 'chat_message',
                        'message': db_message.content,
                        'sender': self.user.username,
                        'timestamp': db_message.timestamp.strftime("%H:%M"),
                        'user_id': str(self.user.id),
                        'message_id': str(db_message.id),
                        'chat_id': str(self.chat.id),
                        'is_sender': False
                    }
                )
                
                # Send notification to recipient
                other_user = await self.get_other_participant()
                await self.channel_layer.group_send(
                    f'notifications_{other_user.id}',
                    {
                        'type': 'notify',
                        'notification_type': 'new_message',
                        'sender': self.user.username,
                        'sender_avatar': self.user.profile.profile_pic.url if hasattr(self.user, 'profile') and self.user.profile.profile_pic else '',
                        'content': message[:50] + '...' if len(message) > 50 else message,
                        'chat_id': str(self.chat.id)
                    }
                )
                
            elif message_type == 'post_like':
                # Proper async handling of post like notification
                post_id = data['post_id']
                liker_id = data['liker_id']
                
                # Get liker and post in proper async way
                liker = await self.get_user(liker_id)
                post = await self.get_post(post_id)
                post_author = await self.get_post_author(post)
                
                await self.channel_layer.group_send(
                    f'notifications_{post_author.id}',
                    {
                        'type': 'notify',
                        'notification_type': 'post_like',
                        'liker': liker.username,
                        'liker_avatar': await get_user_profile_pic(liker),
                        'post_content': data.get('post_content', 'your post'),
                        'post_id': post_id
                    }
                )
                
        except Exception as e:
            print(f"Error processing message: {e}")

    async def chat_message(self, event):
        # Get the sender's profile picture, not the current user's
        sender_avatar = await get_sender_profile_pic(event['sender'])
        sender_initials = event['sender'][0].upper() if event['sender'] else 'U'
        
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'timestamp': event['timestamp'],
            'user_id': event['user_id'],
            'message_id': event['message_id'],
            'is_sender': str(self.user.id) == event['user_id'],
            'chat_id': str(self.chat.id),
            'sender_avatar': sender_avatar,
            'sender_initials': sender_initials
        }))

        # Notify the recipient's notification channel
        if not event['is_sender']:
            channel_layer = get_channel_layer()
            other_user = await self.get_other_participant()
            other_user_avatar = await get_sender_profile_pic(self.user.username)
            await channel_layer.group_send(
                f'notifications_{other_user.id}',
                {
                    'type': 'notify',
                    'notification_type': 'new_message',
                    'chat_id': str(self.chat.id),
                    'sender': self.user.username,
                    'sender_avatar': other_user_avatar,
                    'content': event['message'][:50] + '...' if len(event['message']) > 50 else event['message']
                }
            )