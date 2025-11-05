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
    expertise = serializers.CharField(source='profile.expertise', read_only=True)

    last_online = serializers.DateTimeField(source='activity.last_online', read_only=True)
    last_seen_display = serializers.SerializerMethodField()

    def get_last_seen_display(self, obj):
        if hasattr(obj, 'activity'):
            return obj.activity.get_last_seen_display()
        return "Offline"
    
    class Meta:
        model = CustomUser
        fields = ['id', 'name', 'phone', 'profile_photo', 'is_online', 'last_online', 'last_seen_display', 'expertise']
    
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
    coins_used = serializers.IntegerField(read_only=True) 
    document_file = serializers.FileField(read_only=True)  # Returns URL for Flutter download
    
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

        # For media messages, always check balance since they always cost
        if has_document:
            fan_wallet = user.wallet
            creator_tier = session.creator.creator_profile.tier
            coin_cost = self.get_chat_cost(creator_tier, service_type)

            if fan_wallet.balance < coin_cost:
                raise serializers.ValidationError("Insufficient coins")

        # For text messages, check balance only if not first message and outside free window
        elif session.messages.exists():  # Not first message
            is_first_message_from_this_user = not session.messages.filter(sender=user).exists()

            if (user == session.fan and
                session.free_window_until and
                timezone.now() > session.free_window_until and
                not is_first_message_from_this_user):  # Not their first message

                # Check fan's wallet balance
                fan_wallet = user.wallet
                creator_tier = session.creator.creator_profile.tier
                coin_cost = self.get_chat_cost(creator_tier, service_type)

                if fan_wallet.balance < coin_cost:
                    raise serializers.ValidationError("Insufficient coins")

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