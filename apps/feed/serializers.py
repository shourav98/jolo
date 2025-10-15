from rest_framework import serializers
from django.conf import settings
from apps.feed.models import (
    Feed, FeedFile, FeedVideo, Comment,
    Like, Unlike, Story, StoryItem,
    Follow, TopFan, Transaction, VideoTip,
    CreatorProfile, Announcement
)
from apps.account.models import UserProfile
from apps.monetization.models import Wallet


# -----------------------------
# 👤 SIMPLE USER PROFILE
# -----------------------------
class SimpleUserProfileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['id', 'name', 'profile_photo']


# -----------------------------
# 📰 FEED SERIALIZERS
# -----------------------------
class FeedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedFile
        fields = ['id', 'file']


class FeedVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedVideo
        fields = [
            'id', 'file', 'title', 'description',
            'total_like', 'total_comment', 'total_view',
            'total_earn', 'created_at'
        ]


class FeedSerializer(serializers.ModelSerializer):
    files = FeedFileSerializer(many=True, read_only=True)

    class Meta:
        model = Feed
        fields = [
            'id', 'content', 'status', 'files',
            'total_like', 'total_comment', 'created_at'
        ]


# 🪙 FEED CREATE + WALLET DEDUCTION
class FeedCreateSerializer(serializers.Serializer):
    content = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=[("public", "Public"), ("private", "Private"), ("friends", "Friends")],
        required=True
    )
    image = serializers.ImageField(required=False)
    video = serializers.FileField(required=False)

    def create(self, validated_data):
        user = self.context["request"].user
        profile = user.profile
        content = validated_data.get("content", "")
        status = validated_data.get("status")
        image = validated_data.get("image", None)
        video = validated_data.get("video", None)

        # 🪙 Deduct coin on post create
        wallet, _ = Wallet.objects.get_or_create(user=user)
        post_cost = getattr(settings, "POST_COST_COINS", 10)
        if wallet.balance < post_cost:
            raise serializers.ValidationError({"detail": "Insufficient coin balance to post."})
        wallet.spend(post_cost)

        # 📰 Create Feed
        feed = Feed.objects.create(profile=profile, content=content, status=status)
        if image:
            FeedFile.objects.create(feed=feed, file=image)

        feed_video = None
        if video:
            feed_video = FeedVideo.objects.create(
                profile=profile,
                file=video,
                title=content[:100],
                description=content
            )

        return {"feed": feed, "video": feed_video if video else None}


# -----------------------------
# 💬 COMMENT SERIALIZER
# -----------------------------
class CommentSerializer(serializers.ModelSerializer):
    comment_by = SimpleUserProfileSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'content', 'comment_by', 'created_at']


# -----------------------------
# 👍 LIKE / 👎 UNLIKE SERIALIZERS
# -----------------------------
class LikeSerializer(serializers.ModelSerializer):
    liked_by = SimpleUserProfileSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'liked_by', 'created_at']


class UnlikeSerializer(serializers.ModelSerializer):
    unliked_by = SimpleUserProfileSerializer(read_only=True)

    class Meta:
        model = Unlike
        fields = ['id', 'unliked_by', 'created_at']



# STORY SERIALIZERS

class StoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryItem
        fields = ['id', 'file', 'is_active', 'total_view', 'created_at']


class StorySerializer(serializers.ModelSerializer):
    profile = SimpleUserProfileSerializer(read_only=True)
    items = StoryItemSerializer(many=True, read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'profile', 'items', 'created_at']



# FOLLOW / TOP FAN SERIALIZERS

class FollowSerializer(serializers.ModelSerializer):
    follower = SimpleUserProfileSerializer(read_only=True)
    following = SimpleUserProfileSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']


class TopFanSerializer(serializers.ModelSerializer):
    iam = SimpleUserProfileSerializer(read_only=True)
    fan_profile = SimpleUserProfileSerializer(read_only=True)

    class Meta:
        model = TopFan
        fields = ['id', 'iam', 'fan_profile', 'score', 'status', 'last_interacted']



# TRANSACTION / VIDEO TIP SERIALIZERS

class TransactionSerializer(serializers.ModelSerializer):
    sender = SimpleUserProfileSerializer(read_only=True)
    receiver = SimpleUserProfileSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'sender', 'receiver', 'type', 'amount', 'created_at']


class VideoTipSerializer(serializers.ModelSerializer):
    sender = SimpleUserProfileSerializer(read_only=True)

    class Meta:
        model = VideoTip
        fields = ['id', 'video', 'sender', 'amount', 'created_at']



#  CREATOR / ANNOUNCEMENT SERIALIZERS

class CreatorProfileSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = CreatorProfile
        fields = ['id', 'user', 'start_date', 'status']


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ['id', 'title', 'content', 'image', 'video', 'is_featured', 'created_at']
