from rest_framework import serializers
from .models import ChatSession, Message, MessageReaction
from apps.account.models import CustomUser, UserProfile 
from django.utils import timezone
from datetime import timedelta

from rest_framework.pagination import PageNumberPagination

class MessagePagination(PageNumberPagination):
    page_size = 50  # For long chat histories


class UserSerializer(serializers.ModelSerializer):
    profile_photo = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()
    online_status = serializers.SerializerMethodField()
    last_seen = serializers.SerializerMethodField()
    expertise = serializers.CharField(source='profile.expertise', read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'name', 'phone', 'profile_photo', 
            'is_online', 'online_status', 'last_seen', 'expertise'
        ]
    
    def get_profile_photo(self, obj):
        if hasattr(obj, 'profile') and obj.profile.profile_photo:
            return obj.profile.profile_photo.url
        return None
    
    def get_is_online(self, obj):
        """Check if user is currently online"""
        if hasattr(obj, 'activity'):
            # Consider user online if active in last 5 minutes
            from django.utils import timezone
            from datetime import timedelta
            
            if obj.activity.is_online:
                recent_threshold = timezone.now() - timedelta(minutes=5)
                return obj.activity.last_seen >= recent_threshold
        return False
    
    def get_online_status(self, obj):
        """Get formatted online status"""
        if hasattr(obj, 'activity'):
            return obj.activity.get_status_display()
        return "Offline"
    
    def get_last_seen(self, obj):
        """Get last seen timestamp"""
        if hasattr(obj, 'activity'):
            return obj.activity.last_seen
        return None

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
    coins_used = serializers.IntegerField(read_only=True) 
    document_file = serializers.URLField(read_only=True)  # Cloudinary URL
    
    class Meta:
        model = Message
        fields = [
            'id', 'session', 'sender', 'sender_name', 'sender_profile_photo',
            'content', 'translated_content', 'coins_used',
            'created_at', 'is_read', 'reactions', 'can_react', 'document_file',
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
    document_file = serializers.FileField(required=False)  # Accept file upload

    class Meta:
        model = Message
        fields = ['content', 'document_file']
    
    def validate(self, data):
        session = self.context['session']
        user = self.context['request'].user

        # Check if user is part of this chat session
        if user not in [session.creator, session.fan]:
            raise serializers.ValidationError("You are not part of this chat session")

        # Check if creator has monetization active (required for paid messages)
        if not hasattr(session.creator, 'monetization') or session.creator.monetization.status != 'active':
            raise serializers.ValidationError("Creator is not monetized")

        # Determine service type for validation
        has_document = data.get('document_file') is not None

        if has_document:
            file_name = data['document_file'].name.lower()
            if file_name.endswith(('.mp4', 'video')):
                service_type = "video"
            else:
                service_type = "photo"
        else:
            service_type = "chat"

        # Skip balance validation here - we'll do it in the view after Cloudinary upload
        # to avoid wasting upload resources on failed validations

        return data
    
    def get_chat_cost(self, tier, service_type="chat"):
        from apps.messaging.services import get_message_cost
        return get_message_cost(tier, service_type)

class ReactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageReaction
        fields = ['reaction']

class WelcomeMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['welcome_message', 'auto_translate']