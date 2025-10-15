import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from datetime import timedelta
from .models import ChatSession, Message, MessageReaction
from apps.account.models import CustomUser, UserActivity
from .serializers import MessageSerializer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope['url_route']['kwargs']['session_id']
        self.room_group_name = f'chat_{self.session_id}'

        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        # mark user online
        await self.update_user_status(user, True)

    async def disconnect(self, close_code):
        user = self.scope["user"]
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        await self.update_user_status(user, False)

    async def receive(self, text_data):
        """Handle incoming messages"""
        data = json.loads(text_data)
        message = data.get("message")
        message_type = data.get("message_type", "normal")

        user = self.scope["user"]
        session = await self.get_session(self.session_id)

        if not session or user not in [session.creator, session.fan]:
            await self.send_json({"error": "Unauthorized"})
            return

        message_obj = await self.save_message(session, user, message, message_type)
        serialized = await self.serialize_message(message_obj)

        # broadcast message
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat_message",
                "message": serialized,
            }
        )

        # if creator replied, start 60s free window
        if user == session.creator:
            await self.activate_free_window(session)

    async def chat_message(self, event):
        await self.send_json(event["message"])

    async def send_json(self, content):
        await self.send(text_data=json.dumps(content))

    # ---------- database operations (sync -> async) ----------
    @database_sync_to_async
    def get_session(self, session_id):
        try:
            return ChatSession.objects.get(id=session_id, is_active=True)
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def save_message(self, session, sender, content, message_type):
        tokens_used = 0
        
        # Fan pays if outside free window and not first message
        if (sender == session.fan and 
            (not session.free_window_until or timezone.now() > session.free_window_until) and
            session.messages.filter(sender=sender).exists()):  # Not first message
            
            tokens_used = 0.5
            # Deduct from wallet
            wallet = sender.wallet
            if wallet.tokens >= tokens_used:
                wallet.tokens -= tokens_used
                wallet.save()
            else:
                raise Exception("Insufficient tokens")

        msg = Message.objects.create(
            session=session,
            sender=sender,
            content=content,
            message_type=message_type,
            tokens_used=tokens_used,
        )
        return msg

    @database_sync_to_async
    def serialize_message(self, message):
        serializer = MessageSerializer(message)
        return serializer.data

    @database_sync_to_async
    def activate_free_window(self, session):
        session.free_window_until = timezone.now() + timedelta(seconds=60)
        session.save(update_fields=["free_window_until"])

    @database_sync_to_async
    def update_user_status(self, user, is_online):
        UserActivity.objects.update_or_create(
            user=user,
            defaults={"is_online": is_online, "last_online": timezone.now()},
        )
