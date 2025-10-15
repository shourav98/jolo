# serializers.py
from rest_framework import serializers
from .models import ChatSession, Message, MessageReaction
from apps.account.models import CustomUser, UserProfile 
from django.utils import timezone
from datetime import timedelta

class UserSerializer(serializers.ModelSerializer):
    profile_photo = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'phone', 'profile_photo', 'is_online']
    
    def get_profile_photo(self, obj):
        if hasattr(obj, 'profile') and obj.profile.profile_photo:
            return obj.profile.profile_photo.url
        return None
    
    def get_is_online(self, obj):
        if hasattr(obj, 'activity'):
            return obj.activity.is_online
        return False


class MessageReactionSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.name', read_only=True)
    
    class Meta:
        model = MessageReaction
        fields = ['id', 'user', 'user_name', 'reaction', 'created_at']


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.name', read_only=True)
    sender_profile_photo = serializers.SerializerMethodField()
    reactions = MessageReactionSerializer(many=True, read_only=True)
    can_react = serializers.SerializerMethodField()
    
    class Meta:
        model = Message
        fields = [
            'id', 'session', 'sender', 'sender_name', 'sender_profile_photo',
            'content', 'translated_content', 'message_type', 'tokens_used',
            'created_at', 'is_read', 'reactions', 'can_react'
        ]
    
    def get_sender_profile_photo(self, obj):
        if hasattr(obj.sender, 'profile') and obj.sender.profile.profile_photo:
            return obj.sender.profile.profile_photo.url
        return None
    
    def get_can_react(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user != obj.sender
        return False


class ChatSessionSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    fan = UserSerializer(read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    free_window_active = serializers.SerializerMethodField()
    free_window_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'creator', 'fan', 'is_active', 'created_at',
            'free_window_until', 'last_message', 'unread_count',
            'free_window_active', 'free_window_remaining'
        ]
    
    def get_last_message(self, obj):
        last_msg = obj.messages.last()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None
    
    def get_unread_count(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
        return 0
    
    def get_free_window_active(self, obj):
        if obj.free_window_until:
            return timezone.now() < obj.free_window_until
        return False
    
    def get_free_window_remaining(self, obj):
        if obj.free_window_until and timezone.now() < obj.free_window_until:
            remaining = obj.free_window_until - timezone.now()
            return int(remaining.total_seconds())
        return 0


class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content', 'message_type']
    
    def validate(self, data):
        session = self.context['session']
        user = self.context['request'].user
        
        # Check if user is part of this chat session
        if user not in [session.creator, session.fan]:
            raise serializers.ValidationError("You are not part of this chat session")
        if user == session.fan and not session.messages.exists():
            data['tokens_used'] = 0
        # Check free window for fans
        if user == session.fan and session.free_window_until:
            if timezone.now() > session.free_window_until:
                data['tokens_used'] = self.calculate_tokens(data['content'])
        
        return data
    
    def calculate_tokens(self, content):
        return 0.5
        # 0.5 tokens per message model
        # words = len(content.split())
        # return max(1, int(words * 0.5))


class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = ['reaction']


class WelcomeMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['welcome_message', 'auto_translate']