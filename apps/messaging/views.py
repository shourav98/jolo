from django.shortcuts import render, get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import ChatSession, Message, MessageReaction, UserActivity
from .serializers import (
    ChatSessionSerializer, MessageSerializer, CreateMessageSerializer,
    ReactionSerializer, UserSerializer
)
from django.db import models
from apps.account.models import UserProfile, CustomUser as User
from deep_translator import GoogleTranslator
from rest_framework import serializers
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from apps.monetization.services import spend_coins
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import cloudinary.uploader

import logging
logger = logging.getLogger(__name__)

from apps.monetization.models import MonetizationStatus





# Unified API Response
def api_response(success=True, message="Success", data=None, status_code=200):
    return Response(
        {
            "success": success,
            "message": message,
            "status_code": status_code,
            "data": data,
        },
        status=status_code,
    )

from apps.messaging.services import spend_coins, can_send_free_message, get_message_cost

class MessagePagination(PageNumberPagination):
    page_size = 50

class ChatSearchAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        query = request.query_params.get('query', '')
        users = User.objects.filter(
            Q(name__icontains=query) | Q(phone__icontains=query),
            profile__is_creator=True
        ).exclude(id=request.user.id)
        serializer = UserSerializer(users, many=True)
        return api_response(data=serializer.data)

class ChatSessionsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        active_only = request.query_params.get('active_only', 'false').lower() == 'true'
        sessions = ChatSession.objects.filter(
            Q(creator=request.user) | Q(fan=request.user),
            is_active=True,
            is_archived=False
        ).select_related('creator', 'fan').prefetch_related('messages')
        
        if active_only:
            sessions = sessions.filter(
                Q(creator__activity__is_online=True) if request.user.profile.is_creator else Q(fan__activity__is_online=True)
            )
        
        serializer = ChatSessionSerializer(sessions, many=True, context={'request': request})
        return api_response(data=serializer.data)




class StartChatAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        
        if request.user.id == user_id:
            return api_response(success=False, message='Cannot start chat with yourself', status_code=status.HTTP_400_BAD_REQUEST)
        
        # Prioritize request.user as creator if possible
        if hasattr(request.user, 'profile') and request.user.profile.is_creator:
            creator = request.user
            fan = target_user
        elif hasattr(target_user, 'profile') and target_user.profile.is_creator:
            creator = target_user
            fan = request.user
        else:
            return api_response(
                success=False,
                message='Chat requires at least one creator',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if creator is monetized
        if (hasattr(creator, 'monetization') and
            creator.monetization.status != 'active'):
            return api_response(
                success=False,
                message='Creator is not monetized and cannot receive paid messages',
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        chat_session, created = ChatSession.objects.get_or_create(
            creator=creator,
            fan=fan,
            defaults={'is_active': True}
        )
        
        serializer = ChatSessionSerializer(chat_session, context={'request': request})
        return api_response(data=serializer.data, status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        logger.info(f"=== MESSAGE API CALLED ===")
        logger.info(f"User: {request.user.name}")
        logger.info(f"Session: {session_id}")
        logger.info(f"Data: {request.data}")
        logger.info(f"Files: {request.FILES}")
        
        chat_session = get_object_or_404(ChatSession, id=session_id, is_active=True)
        
        # Check if user is part of this chat
        if request.user not in [chat_session.creator, chat_session.fan]:
            logger.error("User not part of chat session")
            return api_response(success=False, message='Access denied', status_code=status.HTTP_403_FORBIDDEN)

        serializer = CreateMessageSerializer(
            data=request.data,
            context={'request': request, 'session': chat_session}
        )
        
        if not serializer.is_valid():
            logger.error(f"SERIALIZER ERRORS: {serializer.errors}")
            return api_response(success=False, message="Validation error", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)

        try:
            # Determine service type based on uploaded files
            has_document = serializer.validated_data.get('document_file') is not None
            content = serializer.validated_data.get('content', '').strip()

            if not content and not has_document:
                return api_response(success=False, message="Message content or document is required", status_code=400)

            logger.info(f"Message processing - Has document: {has_document}, Content length: {len(content) if content else 0}")

            if has_document:
                # Check file extension to determine if it's photo or video
                file_name = serializer.validated_data['document_file'].name.lower()
                if file_name.endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                    service_type = "video"
                else:
                    service_type = "photo"

                logger.info(f"Document type: {service_type}, File: {file_name}")

                # Upload to Cloudinary
                uploaded_file = serializer.validated_data['document_file']
                cloudinary_result = cloudinary.uploader.upload(
                    uploaded_file,
                    resource_type="auto",
                    folder="messaging_documents/"
                )

                document_url = cloudinary_result['secure_url']
                document_public_id = cloudinary_result['public_id']
                logger.info(f"File uploaded to Cloudinary: {document_url}")
            else:
                service_type = "chat"
                document_url = None
                document_public_id = None

            # Check wallet balance and calculate coins needed
            coins_used = 0
            is_first_message_in_chat = not chat_session.messages.exists()
            is_first_message_from_this_user = not chat_session.messages.filter(sender=request.user).exists()

            logger.info(f"Chat status - First message in chat: {is_first_message_in_chat}, First message from user: {is_first_message_from_this_user}")
            logger.info(f"Free window active: {chat_session.is_free_window_active()}")
            logger.info(f"User role: {'creator' if request.user == chat_session.creator else 'fan'}")

            if is_first_message_in_chat:
                # First message is always free
                coins_used = 0
                logger.info("First message in chat - free")
                if request.user == chat_session.creator:
                    chat_session.activate_free_window()
                    logger.info("Creator first message - activated free window")
            else:
                if has_document:
                    # Media messages always cost coins
                    creator_profile = chat_session.creator.creator_profile
                    coins_used = self.get_chat_cost(creator_profile.tier, service_type)
                    logger.info(f"Media message cost: {coins_used} coins for {service_type}")

                    fan_wallet = request.user.wallet
                    logger.info(f"Fan wallet balance: {fan_wallet.balance}")
                    if fan_wallet.balance < coins_used:
                        return api_response(
                            success=False, 
                            message=f"Insufficient coins for {service_type}. Required: {coins_used}, Available: {fan_wallet.balance}", 
                            status_code=400
                        )

                elif (request.user == chat_session.fan and
                      not chat_session.is_free_window_active() and
                      not is_first_message_from_this_user):
                    # Text messages cost coins outside free window
                    creator_profile = chat_session.creator.creator_profile
                    coins_used = self.get_chat_cost(creator_profile.tier, service_type)
                    logger.info(f"Paid text message cost: {coins_used} coins")

                    fan_wallet = request.user.wallet
                    logger.info(f"Fan wallet balance: {fan_wallet.balance}")
                    if fan_wallet.balance < coins_used:
                        return api_response(
                            success=False, 
                            message=f"Insufficient coins. Required: {coins_used}, Available: {fan_wallet.balance}", 
                            status_code=400
                        )
                else:
                    logger.info("Free message conditions met")

                # If creator replies, activate free window for fan
                if request.user == chat_session.creator:
                    chat_session.activate_free_window()
                    logger.info("Creator reply - activated free window")

            # Create message first
            message_data = {
                'session': chat_session,
                'sender': request.user,
                'content': content,
                'document_file': document_url,
                'document_public_id': document_public_id,
                'coins_used': coins_used
            }
            message = Message.objects.create(**message_data)
            logger.info(f"Message created with ID: {message.id}, Coins used: {coins_used}")

            # Process coin spending after message creation
            if coins_used > 0:
                try:
                    from apps.messaging.services import spend_coins
                    logger.info(f"Processing coin spending: {coins_used} coins")
                    spend_coins(
                        fan=request.user,
                        creator=chat_session.creator,
                        service=service_type,
                        coins=coins_used
                    )
                    logger.info("Coin spending completed successfully")
                except Exception as e:
                    # If payment fails, delete the message and return error
                    message.delete()
                    logger.error(f"Payment failed: {e}")
                    return api_response(success=False, message=str(e), status_code=400)
            
            # Auto-translation
            self.handle_auto_translation(request.user, message)
            
            # Update user activity
            UserActivity.objects.update_or_create(
                user=request.user,
                defaults={'is_online': True, 'last_online': timezone.now()}
            )
            
            response_serializer = MessageSerializer(message, context={'request': request})
            logger.info("Message sent successfully")
            return api_response(data=response_serializer.data, status_code=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error sending message: {str(e)}", exc_info=True)
            return api_response(success=False, message="Internal server error", status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def get_chat_cost(self, tier, service_type="chat"):
        from apps.messaging.services import get_message_cost
        return get_message_cost(tier, service_type)
    
    def handle_auto_translation(self, user, message):
        """Handle auto-translation safely"""
        try:
            if (hasattr(user, 'profile') and 
                hasattr(user.profile, 'auto_translate') and 
                user.profile.auto_translate):
                
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='auto', target='en')
                translated_text = translator.translate(message.content)
                message.translated_content = translated_text
                message.save()
                
        except Exception as e:
            logger.error(f"Translation failed for message {message.id}: {e}")


    
    def translate_message(self, message):
        """Auto-translate message content"""
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='auto', target='en')
            translated_text = translator.translate(message.content)
            message.translated_content = translated_text
            message.save()
        except Exception as e:
            print(f"Translation failed: {e}")

class SendPriorityMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        chat_session = get_object_or_404(ChatSession, id=session_id, is_active=True)
        
        if request.user != chat_session.fan:
            return api_response(success=False, message='Only fans can send priority messages', status_code=403)
        
        wallet = request.user.wallet
        priority_cost = 5
        
        if wallet.balance < priority_cost:
            return api_response(success=False, message='Insufficient coins', data={'suggested_pack': 'Chat Pack (10 coins for $0.99)'}, status_code=400)
        
        recent_priority_count = Message.objects.filter(
            session=chat_session, 
            sender=request.user, 
            created_at__gte=timezone.now()-timedelta(minutes=1)
        ).count()
        
        if recent_priority_count >= 3:
            return api_response(success=False, message='Too many priority messages recently', status_code=429)
        
        content = request.data.get('content')
        if not content:
            return api_response(success=False, message='Content is required', status_code=400)
        
        wallet.spend(priority_cost)
        
        message = Message.objects.create(
            session=chat_session,
            sender=request.user,
            content=content,
            coins_used=priority_cost
        )
        
        serializer = MessageSerializer(message, context={'request': request})
        return api_response(data=serializer.data, status_code=201)




class AddReactionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        if message.sender == request.user:
            return api_response(success=False, message='Cannot react to your own message', status_code=status.HTTP_400_BAD_REQUEST)
        
        serializer = ReactionSerializer(data=request.data)
        if serializer.is_valid():
            reaction, created = MessageReaction.objects.update_or_create(
                message=message,
                user=request.user,
                defaults=serializer.validated_data
            )
            
            return api_response(message='Reaction added successfully', data={'reaction': reaction.reaction})
        
        return api_response(success=False, message="Validation error", data=serializer.errors, status_code=status.HTTP_400_BAD_REQUEST)



# class OnlineCreatorsAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         # Get all online creator activities
#         online_activities = UserActivity.objects.filter(
#             is_online=True,
#             user__profile__is_creator=True
#         ).select_related('user')

#         # Extract the creator users from those activities
#         creators = [activity.user for activity in online_activities]

#         # Serialize and return
#         serializer = UserSerializer(creators, many=True)
#         return api_response(data=serializer.data)




class UpdateUserStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        is_online = request.data.get('is_online', True)
        
        # Update UserActivity
        activity, created = UserActivity.objects.update_or_create(
            user=request.user,
            defaults={
                'is_online': is_online,
                'last_online': timezone.now()
            }
        )
        
        # Also update UserProfile if it exists
        if hasattr(request.user, 'profile'):
            request.user.profile.is_online = is_online
            request.user.profile.last_online = timezone.now()
            request.user.profile.save()
        
        return api_response(message='User status updated successfully', data={
            'is_online': is_online,
            'user_id': request.user.id
        })



class CheckFreeWindowAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        chat_session = get_object_or_404(ChatSession, id=session_id)
        
        free_window_active = False
        time_remaining = 0
        
        if chat_session.free_window_until:
            free_window_active = timezone.now() < chat_session.free_window_until
            if free_window_active:
                time_remaining = (chat_session.free_window_until - timezone.now()).total_seconds()
        
        return api_response(data={
            'free_window_active': free_window_active,
            'time_remaining': int(time_remaining),
            'free_window_until': chat_session.free_window_until
        })

class DeleteMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        if message.sender != request.user:
            return api_response(success=False, message='Can only delete own messages', status_code=status.HTTP_403_FORBIDDEN)
        
        message.delete()
        return api_response(message='Message deleted successfully')
    





class TranslateMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        target_language = request.data.get('target_language', 'en')
        
        try:
            translator = GoogleTranslator(source='auto', target=target_language)
            translated_text = translator.translate(message.content)
            
            return api_response(data={
                'original': message.content,
                'translated': translated_text,
                'target_language': target_language
            })
        except Exception as e:
            return api_response(success=False, message=f'Translation failed: {str(e)}', status_code=400)
        



class AllwisperMessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        messages = Message.objects.filter(
            session__creator=request.user,
        ).select_related('session', 'sender').order_by('-created_at')
        
        paginator = MessagePagination()
        paginated_messages = paginator.paginate_queryset(messages, request)
        serializer = MessageSerializer(paginated_messages, many=True, context={'request': request})
        
        return paginator.get_paginated_response(serializer.data)
    

# class OnlineCreatorsAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         # Get all online creator activities
#         online_activities = UserActivity.objects.filter(
#             is_online=True,
#             user__profile__is_creator=True
#         ).select_related('user')

#         # Extract the creator users from those activities
#         creators = [activity.user for activity in online_activities]

#         # Serialize and return
#         serializer = UserSerializer(creators, many=True)
#         return api_response(data=serializer.data)
    




class ChatSessionMessagesAPIView(APIView):
    """
    API to get all messages from a specific chat session/conversation
    """
    permission_classes = [IsAuthenticated]
    pagination_class = MessagePagination
    
    def get(self, request, session_id):
        try:
            # Get the chat session
            chat_session = get_object_or_404(
                ChatSession, 
                id=session_id,
                is_active=True
            )
            
            # Check if user is part of this chat session
            if request.user not in [chat_session.creator, chat_session.fan]:
                return api_response(
                    success=False,
                    message='Access denied to this chat session',
                    status_code=status.HTTP_403_FORBIDDEN
                )
            
            # Get all messages for this session, ordered by creation time
            messages = Message.objects.filter(
                session=chat_session
            ).select_related(
                'sender', 
                'sender__profile'
            ).prefetch_related(
                'reactions',
                'reactions__user'
            ).order_by('created_at')  # Order by oldest first for chronological order
            
            # Apply pagination
            paginator = self.pagination_class()
            paginated_messages = paginator.paginate_queryset(messages, request)
            
            # Serialize the messages
            serializer = MessageSerializer(
                paginated_messages, 
                many=True, 
                context={'request': request}
            )
            
            # Prepare response data
            response_data = {
                'session_id': str(chat_session.id),
                'creator': UserSerializer(chat_session.creator, context={'request': request}).data,
                'fan': UserSerializer(chat_session.fan, context={'request': request}).data,
                'total_messages': messages.count(),
                'free_window_active': chat_session.is_free_window_active(),
                'free_window_until': chat_session.free_window_until,
                'messages': serializer.data
            }
            
            return paginator.get_paginated_response(response_data)
            
        except Exception as e:
            return api_response(
                success=False,
                message=f'Error retrieving messages: {str(e)}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class OnlineUsersAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get list of online users (creators only or all users)"""
        user_type = request.query_params.get('type', 'creators')  # 'creators' or 'all'
        
        # Get recently active users (within last 5 minutes)
        recent_threshold = timezone.now() - timedelta(minutes=5)
        
        if user_type == 'creators':
            # Get online creators
            online_activities = UserActivity.objects.filter(
                last_seen__gte=recent_threshold,
                user__profile__is_creator=True
            ).select_related('user', 'user__profile')
        else:
            # Get all online users
            online_activities = UserActivity.objects.filter(
                last_seen__gte=recent_threshold
            ).select_related('user', 'user__profile')
        
        online_users = [activity.user for activity in online_activities]
        
        serializer = UserSerializer(online_users, many=True, context={'request': request})
        
        return api_response(
            success=True,
            message=f"Found {len(online_users)} online users",
            data={
                'online_users': serializer.data,
                'total_online': len(online_users)
            }
        )

class OnlineCreatorsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get online creators with ACTIVE monetization - Optimized with logging"""
        recent_threshold = timezone.now() - timedelta(minutes=5)
        
        logger.info("=== ONLINE CREATORS API (OPTIMIZED) ===")
        logger.info(f"Recent threshold: {recent_threshold}")
        
        try:
            # Direct database query for efficiency
            online_creators_activities = UserActivity.objects.filter(
                last_seen__gte=recent_threshold,
                user__monetization__status=MonetizationStatus.ACTIVE
            ).select_related(
                'user', 
                'user__profile', 
                'user__monetization'
            ).order_by('-last_seen')
            
            logger.info(f"Direct query result count: {online_creators_activities.count()}")
            
            # Debug each result
            for activity in online_creators_activities:
                user = activity.user
                logger.info(f"Found active creator: {user.name} (ID: {user.id})")
                logger.info(f"  - Last seen: {activity.last_seen}")
                logger.info(f"  - Monetization status: {user.monetization.status}")
            
            online_creators = [activity.user for activity in online_creators_activities]
            
            serializer = UserSerializer(online_creators, many=True, context={'request': request})
            
            return api_response(
                success=True,
                message=f"Found {len(online_creators)} active creators",
                data={
                    'active_creators': serializer.data,
                    'total_active': len(online_creators)
                }
            )
            
        except Exception as e:
            logger.error(f"Error in OnlineCreatorsAPIView: {e}", exc_info=True)
            return api_response(
                success=False,
                message="Error fetching online creators",
                status_code=500
            )