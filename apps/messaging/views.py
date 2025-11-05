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
        return Response(serializer.data)

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
        return Response(serializer.data)




class StartChatAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, user_id):
        target_user = get_object_or_404(User, id=user_id)
        
        if request.user.id == user_id:
            return Response({'error': 'Cannot start chat with yourself'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Prioritize request.user as creator if possible
        if hasattr(request.user, 'profile') and request.user.profile.is_creator:
            creator = request.user
            fan = target_user
        elif hasattr(target_user, 'profile') and target_user.profile.is_creator:
            creator = target_user
            fan = request.user
        else:
            return Response(
                {'error': 'Chat requires at least one creator'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if creator is monetized
        if (hasattr(creator, 'monetization') and 
            creator.monetization.status != 'active'):
            return Response(
                {'error': 'Creator is not monetized and cannot receive paid messages'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        chat_session, created = ChatSession.objects.get_or_create(
            creator=creator,
            fan=fan,
            defaults={'is_active': True}
        )
        
        serializer = ChatSessionSerializer(chat_session, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)





class MessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        chat_session = get_object_or_404(ChatSession, id=session_id, is_active=True)
        
        # Check if user is part of this chat
        if request.user not in [chat_session.creator, chat_session.fan]:
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateMessageSerializer(
            data=request.data,
            context={'request': request, 'session': chat_session}
        )
        
        if serializer.is_valid():
            try:
                # Determine service type based on uploaded files
                has_document = serializer.validated_data.get('document_file') is not None

                if has_document:
                    # Check file extension to determine if it's photo or video
                    file_name = serializer.validated_data['document_file'].name.lower()
                    if file_name.endswith(('.mp4', 'video')):
                        service_type = "video"
                    else:
                        service_type = "photo"
                else:
                    service_type = "chat"

                message_data = {
                    'session': chat_session,
                    'sender': request.user,
                    'content': serializer.validated_data.get('content', ''),
                    'document_file': serializer.validated_data.get('document_file')
                }

                # Check if this is the first message in the chat
                is_first_message_in_chat = not chat_session.messages.exists()

                coins_used = 0

                # FIRST MESSAGE LOGIC: Anyone can send first message for free
                if is_first_message_in_chat:
                    # First message is always free, regardless of who sends it
                    coins_used = 0

                    # If creator sends first message, activate free window for fan's response
                    if request.user == chat_session.creator:
                        chat_session.activate_free_window()

                # SUBSEQUENT MESSAGES LOGIC
                else:
                    is_first_message_from_this_user = not chat_session.messages.filter(sender=request.user).exists()

                    # Media messages (photo/video) always cost coins, even during free window
                    if has_document:
                        # Get creator tier and coin cost for the service type
                        creator_profile = chat_session.creator.creator_profile
                        coins_used = self.get_chat_cost(creator_profile.tier, service_type)

                        # Deduct coins
                        from apps.messaging.services import spend_coins
                        spend_coins(
                            fan=request.user,
                            creator=chat_session.creator,
                            service=service_type,
                            coins=coins_used
                        )

                    # Text messages follow free window logic
                    elif (request.user == chat_session.fan and
                          not chat_session.is_free_window_active() and
                          not is_first_message_from_this_user):

                        # Get creator tier and coin cost
                        creator_profile = chat_session.creator.creator_profile
                        coins_used = self.get_chat_cost(creator_profile.tier, service_type)

                        # Deduct coins
                        from apps.messaging.services import spend_coins
                        spend_coins(
                            fan=request.user,
                            creator=chat_session.creator,
                            service=service_type,
                            coins=coins_used
                        )

                    # If creator replies, activate free window for fan
                    if request.user == chat_session.creator:
                        chat_session.activate_free_window()

                message_data['coins_used'] = coins_used
                message = Message.objects.create(**message_data)
                
                # Auto-translation (with safe attribute check)
                self.handle_auto_translation(request.user, message)
                
                # Update user activity
                UserActivity.objects.update_or_create(
                    user=request.user,
                    defaults={'is_online': True, 'last_online': timezone.now()}
                )
                
                response_serializer = MessageSerializer(message, context={'request': request})
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_chat_cost(self, tier, service_type="chat"):
        from apps.messaging.services import get_message_cost
        return get_message_cost(tier, service_type)
    
    def handle_auto_translation(self, user, message):
        """Handle auto-translation safely"""
        try:
            # Check if user has profile and auto_translate is enabled
            if (hasattr(user, 'profile') and 
                hasattr(user.profile, 'auto_translate') and 
                user.profile.auto_translate):
                
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='auto', target='en')
                translated_text = translator.translate(message.content)
                message.translated_content = translated_text
                message.save()
                
        except Exception as e:
            # Log the error but don't break the message sending
            print(f"Translation failed: {e}")
            # You might want to use Django's logging here
            # import logging
            # logger = logging.getLogger(__name__)
            # logger.error(f"Translation failed for message {message.id}: {e}")
    
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
            return Response({'error': 'Only fans can send priority messages'}, status=403)
        
        wallet = request.user.wallet
        priority_cost = 5
        
        if wallet.balance < priority_cost:
            return Response({'error': 'Insufficient coins', 'suggested_pack': 'Chat Pack (10 coins for $0.99)'}, status=400)
        
        recent_priority_count = Message.objects.filter(
            session=chat_session, 
            sender=request.user, 
            created_at__gte=timezone.now()-timedelta(minutes=1)
        ).count()
        
        if recent_priority_count >= 3:
            return Response({'error': 'Too many priority messages recently'}, status=429)
        
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content is required'}, status=400)
        
        wallet.spend(priority_cost)
        
        message = Message.objects.create(
            session=chat_session,
            sender=request.user,
            content=content,
            coins_used=priority_cost
        )
        
        serializer = MessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=201)




class AddReactionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        if message.sender == request.user:
            return Response({'error': 'Cannot react to your own message'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = ReactionSerializer(data=request.data)
        if serializer.is_valid():
            reaction, created = MessageReaction.objects.update_or_create(
                message=message,
                user=request.user,
                defaults=serializer.validated_data
            )
            
            return Response({'status': 'success', 'reaction': reaction.reaction})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class OnlineCreatorsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all online creator activities
        online_activities = UserActivity.objects.filter(
            is_online=True,
            user__profile__is_creator=True
        ).select_related('user')

        # Extract the creator users from those activities
        creators = [activity.user for activity in online_activities]

        # Serialize and return
        serializer = UserSerializer(creators, many=True)
        return Response(serializer.data)




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
        
        return Response({
            'status': 'success', 
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
        
        return Response({
            'free_window_active': free_window_active,
            'time_remaining': int(time_remaining),
            'free_window_until': chat_session.free_window_until
        })

class DeleteMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def delete(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        if message.sender != request.user:
            return Response({'error': 'Can only delete own messages'}, status=status.HTTP_403_FORBIDDEN)
        
        message.delete()
        return Response({'status': 'deleted'}, status=status.HTTP_200_OK)
    





class TranslateMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        target_language = request.data.get('target_language', 'en')
        
        try:
            translator = GoogleTranslator(source='auto', target=target_language)
            translated_text = translator.translate(message.content)
            
            return Response({
                'original': message.content,
                'translated': translated_text,
                'target_language': target_language
            })
        except Exception as e:
            return Response({'error': f'Translation failed: {str(e)}'}, status=400)
        



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
    

class OnlineCreatorsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all online creator activities
        online_activities = UserActivity.objects.filter(
            is_online=True,
            user__profile__is_creator=True
        ).select_related('user')

        # Extract the creator users from those activities
        creators = [activity.user for activity in online_activities]

        # Serialize and return
        serializer = UserSerializer(creators, many=True)
        return Response(serializer.data)
    




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
                return Response(
                    {'error': 'Access denied to this chat session'}, 
                    status=status.HTTP_403_FORBIDDEN
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
            return Response(
                {'error': f'Error retrieving messages: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )