import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Chat, Message
from datetime import datetime

User = get_user_model()

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
            # Leave room group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        print(f"WebSocket DISCONNECTED: {getattr(self, 'user', 'Anonymous')} from chat {getattr(self, 'chat_id', 'unknown')} with code {close_code}")

    # Database operations
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
    def save_message(self, content):
        return Message.objects.create(
            chat=self.chat,
            sender=self.user,
            content=content,
            timestamp=datetime.now()
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data['message']
            
            # Save message to database
            db_message = await self.save_message(message)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.group_name,
                {
                    'type': 'chat_message',
                    'message': db_message.content,
                    'sender': self.user.username,
                    'timestamp': db_message.timestamp.strftime("%H:%M"),
                    'user_id': str(self.user.id)
                }
            )
        except Exception as e:
            print(f"Error processing message: {e}")

async def chat_message(self, event):
    sender_username = self.user.username
    
    await self.send(text_data=json.dumps({
        'type': 'chat_message',
        'message': event['message'],
        'sender': sender_username,
        'timestamp': event['timestamp'],
        'user_id': str(self.user.id)
    }))