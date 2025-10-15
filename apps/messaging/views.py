from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import ChatSession, Message, MessageReaction, UserActivity
from .serializers import (
    ChatSessionSerializer, MessageSerializer, CreateMessageSerializer,
    ReactionSerializer, WelcomeMessageSerializer, UserSerializer
)
from django.shortcuts import get_object_or_404
import json
from django.db import models
from apps.account.models import UserProfile,CustomUser as User
from deep_translator import GoogleTranslator
from rest_framework import serializers



class ChatSessionsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Get all chat sessions for the current user
        sessions = ChatSession.objects.filter(
            models.Q(creator=request.user) | models.Q(fan=request.user),
            is_active=True
        ).select_related('creator', 'fan').prefetch_related('messages')
        
        serializer = ChatSessionSerializer(sessions, many=True, context={'request': request})
        return Response(serializer.data)


class StartChatAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, creator_id):
        creator = get_object_or_404(User, id=creator_id)
        
        # Check if creator has creator profile
        if not hasattr(creator, 'profile') or not creator.profile.is_creator:
            return Response(
                {'error': 'User is not a creator'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if chat session already exists
        chat_session, created = ChatSession.objects.get_or_create(
            creator=creator,
            fan=request.user,
            defaults={'is_active': True}
        )
        
        # Send welcome message if this is a new session and creator has welcome message
        if created and creator.profile.welcome_message:
            Message.objects.create(
                session=chat_session,
                sender=creator,
                content=creator.profile.welcome_message,
                message_type='auto_reply'
            )
        
        serializer = ChatSessionSerializer(chat_session, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessagesAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, session_id):
        chat_session = get_object_or_404(
            ChatSession, 
            id=session_id,
            is_active=True
        )
        
        # Check if user is part of this chat
        if request.user not in [chat_session.creator, chat_session.fan]:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        messages = chat_session.messages.all().select_related('sender')
        serializer = MessageSerializer(messages, many=True, context={'request': request})
        
        # Mark messages as read
        if request.user == chat_session.fan:
            # Mark creator's messages as read
            chat_session.messages.filter(sender=chat_session.creator, is_read=False).update(is_read=True)
        else:
            # Mark fan's messages as read
            chat_session.messages.filter(sender=chat_session.fan, is_read=False).update(is_read=True)
        
        return Response(serializer.data)
    
    
    def post(self, request, session_id):
        chat_session = get_object_or_404(
            ChatSession, 
            id=session_id,
            is_active=True
        )

        # Check if this is the first message from fan
        is_first_fan_message = not chat_session.messages.filter(sender=request.user).exists()
        if (request.user == chat_session.fan and 
            is_first_fan_message and 
            not chat_session.messages.filter(sender=chat_session.creator).exists()):
            return Response(
                {'error': 'Creator must send first message'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if user is part of this chat
        if request.user not in [chat_session.creator, chat_session.fan]:
            return Response(
                {'error': 'Access denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreateMessageSerializer(
            data=request.data,
            context={'request': request, 'session': chat_session}
        )
        
        if serializer.is_valid():
            message = serializer.save(
                session=chat_session,
                sender=request.user
            )
            
            # Auto-translation if enabled
            if hasattr(request.user, 'profile') and request.user.profile.auto_translate:
                try:
                    translator = GoogleTranslator(source='auto', target='en')
                    translated_text = translator.translate(message.content)
                    message.translated_content = translated_text
                    message.save()
                except Exception as e:
                    # Log the error or handle it appropriately
                    pass
            
            # If creator replied, activate free window for fan
            if request.user == chat_session.creator:
                chat_session.free_window_until = timezone.now() + timedelta(seconds=60)
                chat_session.save()
            
            # Update user activity
            UserActivity.objects.update_or_create(
                user=request.user,
                defaults={'is_online': True, 'last_online': timezone.now()}
            )
            
            response_serializer = MessageSerializer(message, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# In SendPriorityMessageAPIView
class SendPriorityMessageAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, session_id):
        chat_session = get_object_or_404(ChatSession, id=session_id, is_active=True)
        
        if request.user != chat_session.fan:
            return Response({'error': 'Only fans can send priority messages'}, status=403)
        
        # Check token balance
        wallet = request.user.wallet
        priority_cost = 5  # tokens
        
        if wallet.tokens < priority_cost:
            return Response({'error': 'Insufficient tokens for priority message'}, status=400)
        
        # Check rate limiting
        recent_priority_count = Message.objects.filter(
            session=chat_session, 
            sender=request.user, 
            message_type='priority',
            created_at__gte=timezone.now()-timedelta(minutes=1)
        ).count()
        
        if recent_priority_count >= 3:
            return Response({'error': 'Too many priority messages recently'}, status=429)
        
        content = request.data.get('content')
        if not content:
            return Response({'error': 'Content is required'}, status=400)
        
        # Deduct tokens
        wallet.tokens -= priority_cost
        wallet.save()
        
        message = Message.objects.create(
            session=chat_session,
            sender=request.user,
            content=content,
            message_type='priority',
            tokens_used=priority_cost
        )
        
        serializer = MessageSerializer(message, context={'request': request})
        return Response(serializer.data, status=201)
    
    


class AddReactionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, message_id):
        message = get_object_or_404(Message, id=message_id)
        
        # User cannot react to their own messages
        if message.sender == request.user:
            return Response(
                {'error': 'Cannot react to your own message'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
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
        # Get creators who are online
        online_activities = UserActivity.objects.filter(
            is_online=True,
            user__profile__is_creator=True
        ).select_related('user')
        
        creators = [activity.user for activity in online_activities]
        serializer = UserSerializer(creators, many=True)
        return Response(serializer.data)


class UpdateUserStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        is_online = request.data.get('is_online', True)
        
        UserActivity.objects.update_or_create(
            user=request.user,
            defaults={
                'is_online': is_online,
                'last_online': timezone.now()
            }
        )
        
        # Update profile if user is creator
        if hasattr(request.user, 'profile') and request.user.profile.is_creator:
            request.user.profile.is_online = is_online
            request.user.profile.last_online = timezone.now()
            request.user.profile.save()
        
        return Response({'status': 'success', 'is_online': is_online})


class WelcomeMessageSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        serializer = WelcomeMessageSerializer(profile)
        return Response(serializer.data)
    
    def put(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        serializer = WelcomeMessageSerializer(profile, data=request.data)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
