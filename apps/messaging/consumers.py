# apps/messaging/consumers.py
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)

class ChatConsumer(AsyncWebsocketConsumer):

    async def get_user_model(self):
        from django.contrib.auth import get_user_model
        return get_user_model()

    @property
    def session_id(self):
        return self.scope["url_route"]["kwargs"]["session_id"]

    @property
    def session_group_name(self):
        return f"chat_{self.session_id}"

    async def connect(self):
        User = await self.get_user_model()
        
        # Check if user is authenticated
        user = self.scope.get("user")
        
        if user is None or not user.is_authenticated:
            logger.warning(f"WebSocket connection rejected - user not authenticated")
            await self.close(code=4001)
            return

        logger.info(f"WebSocket connection accepted for user: {user.name} (ID: {user.id})")

        # Add this channel to the group
        await self.channel_layer.group_add(
            self.session_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(json.dumps({
            "type": "connection_established",
            "message": "You are connected to the chat session.",
            "user": user.name,
            "user_id": user.id
        }))

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if user and user.is_authenticated:
            try:
                await self.update_user_activity(user, False)
            except Exception as e:
                logger.error(f"Error updating user activity: {e}")

        # Remove channel from the group
        await self.channel_layer.group_discard(
            self.session_group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket disconnected with code: {close_code}")

    @database_sync_to_async
    def update_user_activity(self, user, is_online):
        from apps.messaging.models import UserActivity
        activity, _ = UserActivity.objects.get_or_create(user=user)
        activity.is_online = is_online
        activity.last_online = timezone.now()
        activity.save(update_fields=['is_online', 'last_online'])

    @database_sync_to_async
    def get_chat_session(self, session_id):
        from apps.messaging.models import ChatSession
        try:
            return ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return None

    @database_sync_to_async
    def check_user_in_session(self, session, user):
        return user in [session.creator, session.fan]

    @database_sync_to_async
    def is_first_message_from_user(self, session, user):
        return not session.messages.filter(sender=user).exists()

    @database_sync_to_async
    def spend_coins_and_create_message(self, session, user, content, coins_to_spend):
        from apps.messaging.models import Message
        from apps.monetization.services import spend_coins as monetization_spend_coins
        from apps.monetization.models import CreatorMonetization, MonetizationStatus
        
        # Create the message first (we'll update coins_used later if payment succeeds)
        message = Message.objects.create(
            session=session,
            sender=user,
            content=content,
            coins_used=0  # Initialize as 0, update after payment
        )
        
        # Process payment if coins need to be spent
        if coins_to_spend > 0:
            try:
                # Check if creator is monetized
                creator = session.creator
                if not hasattr(creator, 'monetization') or creator.monetization.status != MonetizationStatus.ACTIVE:
                    raise ValueError("Creator is not monetized")
                
                # Use the proper monetization service to spend coins
                spend_event = monetization_spend_coins(
                    fan=user,
                    creator=creator,
                    service="chat",
                    coins=coins_to_spend
                )
                
                # Update message with actual coins used
                message.coins_used = coins_to_spend
                message.save(update_fields=['coins_used'])
                
                logger.info(f"Successfully spent {coins_to_spend} coins from {user.name} to {creator.name}")
                logger.info(f"Revenue split: Creator earned ${spend_event.usd_creator}, Platform earned ${spend_event.usd_platform}")
                
            except Exception as e:
                # If payment fails, delete the message and raise error
                message.delete()
                logger.error(f"Payment failed: {e}")
                raise ValueError(f"Payment failed: {str(e)}")
        
        # Activate free window if creator sent message
        if user == session.creator:
            session.activate_free_window()
            logger.info("Free window activated by creator response")
        
        return message

    @database_sync_to_async
    def create_free_message(self, session, user, content):
        from apps.messaging.models import Message
        
        # Create the message (free)
        message = Message.objects.create(
            session=session,
            sender=user,
            content=content,
            coins_used=0
        )
        
        # Activate free window if creator sent first message
        if user == session.creator and not session.messages.exists():
            session.activate_free_window()
            logger.info("Free window activated by creator first message")
        
        return message

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("Message received from unauthenticated user")
            await self.send(json.dumps({"error": "User not authenticated."}))
            return

        try:
            data = json.loads(text_data)
            logger.info(f"Raw received data: {data}")
            
            content = data.get("content", "").strip()
            
            if not content:
                await self.send(json.dumps({"error": "Message content cannot be empty"}))
                return

            logger.info(f"Message received from {user.name}: {content[:50]}...")

            # Get chat session
            session = await self.get_chat_session(self.session_id)
            if not session:
                await self.send(json.dumps({"error": "Chat session not found"}))
                return

            # Check if user is part of this chat session
            if not await self.check_user_in_session(session, user):
                await self.send(json.dumps({"error": "Not authorized for this chat session"}))
                return

            role = 'creator' if user == session.creator else 'fan'
            free_window_active = session.is_free_window_active()

            logger.info(f"User role: {role}, Free window active: {free_window_active}")

            coins_to_spend = 0
            
            # FIRST MESSAGE LOGIC: Anyone can send first message for free
            is_first_message_in_chat = not await database_sync_to_async(lambda: session.messages.exists())()
            
            if is_first_message_in_chat:
                # First message is always free
                message = await self.create_free_message(session, user, content)
                logger.info(f"First message saved to database with ID: {message.id}")
                
            else:
                # SUBSEQUENT MESSAGES LOGIC
                is_first_message_from_this_user = await self.is_first_message_from_user(session, user)
                
                # Fan pays if:
                # 1. Outside free window AND
                # 2. Not their first message in this chat AND  
                # 3. Not a creator (creators always message free)
                if (role == 'fan' and 
                    not free_window_active and
                    not is_first_message_from_this_user):
                    
                    # Get creator tier and coin cost
                    creator_tier = await database_sync_to_async(
                        lambda: session.creator.creator_profile.tier
                    )()
                    coins_to_spend = self.get_chat_cost(creator_tier)
                    
                    # Create message with coin spending
                    message = await self.spend_coins_and_create_message(
                        session, user, content, coins_to_spend
                    )
                    
                else:
                    # Free message (creator or fan in free window or first message)
                    message = await self.create_free_message(session, user, content)
                
                logger.info(f"Message saved to database with ID: {message.id}")

            # Update user activity
            await self.update_user_activity(user, True)

            # Broadcast to group
            await self.channel_layer.group_send(
                self.session_group_name,
                {
                    "type": "chat_message",
                    "message_id": str(message.id),
                    "message": content,
                    "sender": user.name,
                    "sender_id": user.id,
                    "role": role,
                    "timestamp": message.created_at.isoformat(),
                    "coins_used": coins_to_spend
                }
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            await self.send(json.dumps({"error": "Invalid JSON format"}))
        except ValueError as e:
            logger.error(f"Value error: {e}")
            await self.send(json.dumps({"error": str(e)}))
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await self.send(json.dumps({"error": f"Internal server error: {str(e)}"}))

    def get_chat_cost(self, tier):
        tier_costs = {
            "silver": 10,
            "gold": 10,
            "platinum": 15,
            "diamond": 20
        }
        return tier_costs.get(tier, 10)

    async def chat_message(self, event):
        await self.send(json.dumps({
            "type": "chat_message",
            "message_id": event["message_id"],
            "message": event["message"],
            "sender": event["sender"],
            "sender_id": event["sender_id"],
            "role": event["role"],
            "timestamp": event["timestamp"],
            "coins_used": event["coins_used"]
        }))