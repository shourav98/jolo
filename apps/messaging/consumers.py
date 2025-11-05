import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from django.utils import timezone
from django.db.models import Q
from django.conf import settings
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

def _resolve_redis_url_from_settings():
    """
    Robustly extract a Redis URL from settings.CHANNEL_LAYERS.
    Supports:
      - CONFIG: {"hosts": ["redis://host:6379"] }
      - CONFIG: {"hosts": [("127.0.0.1", 6379)] }
      - direct string host entries
    Falls back to "redis://127.0.0.1:6379".
    """
    default = "redis://127.0.0.1:6379"
    cl = getattr(settings, "CHANNEL_LAYERS", {}).get("default", {}).get("CONFIG", {})
    hosts = cl.get("hosts") if cl else None

    if not hosts:
        return default

    first = hosts[0]

    # If tuple like ("127.0.0.1", 6379)
    if isinstance(first, (list, tuple)) and len(first) >= 2:
        host = first[0]
        port = first[1]
        return f"redis://{host}:{port}"

    # If already a full URL string
    if isinstance(first, str):
        return first

    # Fallback
    return default


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
    
    @property
    def user_presence_key(self):
        # Protect against unauthenticated scopes lacking user/id
        uid = getattr(self.scope.get("user"), "id", None)
        return f"user_presence_{uid}" if uid is not None else "user_presence_anonymous"

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            logger.warning("WebSocket connection rejected - user not authenticated")
            await self.close(code=4001)
            return

        # Connect to Redis using resolved URL (do NOT access channel_layer.config)
        redis_url = _resolve_redis_url_from_settings()
        try:
            redis_client = await aioredis.from_url(redis_url)
        except Exception as e:
            logger.exception("Failed to connect to Redis in connect(): %s", e)
            await self.close(code=1011)
            return

        # Add this channel to user's presence set in Redis
        try:
            await redis_client.sadd(self.user_presence_key, self.channel_name)

            # Check if this is the first connection (set online if so)
            connection_count = await redis_client.scard(self.user_presence_key)
            if connection_count == 1:
                await self.update_user_activity(user, True)
                await self.broadcast_status(user, True)

            # Add to chat group
            await self.channel_layer.group_add(self.session_group_name, self.channel_name)
            await self.accept()

            await self.send(json.dumps({
                "type": "connection_established",
                "message": "You are connected to the chat session.",
                "user": getattr(user, "name", str(user)),
                "user_id": user.id
            }))

        except Exception as e:
            logger.exception("Error during WebSocket connect flow: %s", e)
            # Ensure we try to close the redis client
            try:
                await redis_client.close()
            except Exception:
                pass
            await self.close(code=1011)
            return

        # Clean up Redis connection
        try:
            await redis_client.close()
        except Exception:
            pass

    async def disconnect(self, close_code):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            return

        redis_url = _resolve_redis_url_from_settings()
        try:
            redis_client = await aioredis.from_url(redis_url)
        except Exception as e:
            logger.exception("Failed to connect to Redis in disconnect(): %s", e)
            return

        try:
            await redis_client.srem(self.user_presence_key, self.channel_name)

            # If no more connections, set offline
            connection_count = await redis_client.scard(self.user_presence_key)
            if connection_count == 0:
                await self.update_user_activity(user, False)
                await self.broadcast_status(user, False)

            # Remove from chat group
            await self.channel_layer.group_discard(self.session_group_name, self.channel_name)
        except Exception as e:
            logger.exception("Error during disconnect cleanup: %s", e)
        finally:
            try:
                await redis_client.close()
            except Exception:
                pass

    @database_sync_to_async
    def get_user_sessions(self, user):
        from apps.messaging.models import ChatSession
        # Return session IDs where user is creator or fan
        return list(ChatSession.objects.filter(Q(creator=user) | Q(fan=user)).values_list('id', flat=True))

    async def broadcast_status(self, user, is_online):
        # Get all chat sessions this user is in
        session_ids = await self.get_user_sessions(user)

        # Broadcast to each chat group
        for session_id in session_ids:
            group_name = f"chat_{session_id}"
            await self.channel_layer.group_send(
                group_name,
                {
                    "type": "user_status",
                    "user_id": user.id,
                    "is_online": is_online,
                    "last_online": timezone.now().isoformat() if not is_online else None
                }
            )

    async def user_status(self, event):
        # Handler for status broadcasts
        await self.send(json.dumps({
            "type": "user_status",
            "user_id": event["user_id"],
            "is_online": event["is_online"],
            "last_online": event.get("last_online")
        }))

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

            logger.info(f"Message received from {getattr(user,'name',str(user))}: {content[:50]}...")

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
                    "sender": getattr(user, "name", str(user)),
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
            logger.exception(f"Error processing message: {e}")
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
