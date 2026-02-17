from rest_framework import serializers
from apps.feed.models import Feed, FeedFile, Comment, TopFan, BlockedUser, MutedPost, ReportedPost


def build_url(request, value):
    """Safely build full URL — works for Cloudinary or relative paths."""
    if not value:
        return None
    url = str(value)
    if request and not url.startswith("http"):
        return request.build_absolute_uri(url)
    return url


class FeedFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FeedFile
        fields = ["id", "file_url", "file_type"]

    def get_file_url(self, obj):
        return build_url(self.context.get("request"), obj.file)


class FeedSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="profile.user.name", read_only=True)
    author_id = serializers.IntegerField(source="profile.user.id", read_only=True)
    author_photo = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    videos = serializers.SerializerMethodField()
    is_unlocked = serializers.SerializerMethodField()
    is_muted = serializers.SerializerMethodField()
    is_author_blocked = serializers.SerializerMethodField()
    is_creator = serializers.BooleanField(source="profile.is_creator", read_only=True)
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = Feed
        fields = [
            "id",
            "author_id",
            "author_name",
            "author_photo",
            "is_owner",
            "is_creator",
            "content",
            "status",
            "unlock_price",
            "comments_enabled",
            "is_unlocked",
            "is_muted",
            "is_author_blocked",
            "total_like",
            "total_unlike",
            "total_comment",
            "total_view",
            "created_at",
            "images",
            "videos",
        ]

    def get_author_photo(self, obj):
        return getattr(obj.profile, "profile_photo", None)

    def get_images(self, obj):
        request = self.context.get("request")
        images = []
        for f in obj.files.filter(file_type="image"):
            if f.file:
                from cloudinary.utils import cloudinary_url
                url, _ = cloudinary_url(f.file)
                images.append(url)
        return images

    def get_videos(self, obj):
        request = self.context.get("request")
        videos = []
        for f in obj.files.filter(file_type="video"):
            if f.file:
                from cloudinary.utils import cloudinary_url
                url, _ = cloudinary_url(f.file, resource_type="video")
                videos.append(url)
        return videos

    def get_is_unlocked(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return obj.status != "locked"
        if hasattr(user, "profile") and user.profile.id == obj.profile_id:
            return True
        if obj.status == "locked":
            return obj.is_unlocked_for(user)
        return True

    def get_is_muted(self, obj):
        """Check if current user has muted this post"""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        from apps.feed.models import MutedPost
        return MutedPost.objects.filter(user=user.profile, post=obj).exists()

    def get_is_author_blocked(self, obj):
        """Check if current user has blocked the post author"""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        from apps.feed.models import BlockedUser
        from apps.feed.models import BlockedUser
        return BlockedUser.objects.filter(blocker=user.profile, blocked=obj.profile).exists()

    def get_is_owner(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.profile.user == request.user
        return False




class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="comment_by.user.name", read_only=True)
    user_photo = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "user_name", "user_photo", "content", "created_at"]

    def get_user_photo(self, obj):
        photo = getattr(obj.comment_by, "profile_photo", None)
        if photo:
            from cloudinary.utils import cloudinary_url
            url, _ = cloudinary_url(photo)
            return url
        return None


class TopFanSerializer(serializers.ModelSerializer):
    fan_id = serializers.IntegerField(source="fan.id", read_only=True)
    fan_name = serializers.CharField(source="fan.user.name", read_only=True)
    fan_photo = serializers.SerializerMethodField()

    class Meta:
        model = TopFan
        fields = ["fan_id", "fan_name", "fan_photo", "score", "last_interacted"]

    def get_fan_photo(self, obj):
        photo = getattr(obj.fan, "profile_photo", None)
        if photo:
            from cloudinary.utils import cloudinary_url
            url, _ = cloudinary_url(photo)
            return url
        return None
    

# New Serializers for Post Menu Actions

class BlockedUserSerializer(serializers.ModelSerializer):
    """Serializer for user blocking"""
    blocked_user_id = serializers.IntegerField(source="blocked.id", read_only=True)
    blocked_user_name = serializers.CharField(source="blocked.user.name", read_only=True)
    blocked_user_photo = serializers.SerializerMethodField()
    blocked_user_bio = serializers.CharField(source="blocked.bio", read_only=True)

    is_blocked = serializers.SerializerMethodField()

    class Meta:
        model = BlockedUser
        fields = ["id", "blocked_user_id", "blocked_user_name", "blocked_user_photo", "blocked_user_bio", "created_at", "is_blocked"]
        read_only_fields = ["id", "created_at"]
    
    def get_blocked_user_photo(self, obj):
        """Get blocked user's profile photo URL"""
        photo = getattr(obj.blocked, "profile_photo", None)
        if photo:
            from cloudinary.utils import cloudinary_url
            url, _ = cloudinary_url(photo)
            return url
        return None

    def get_is_blocked(self, obj):
        return True


class MutedPostSerializer(serializers.ModelSerializer):
    """Serializer for muted posts"""
    post_id = serializers.IntegerField(source="post.id", read_only=True)

    class Meta:
        model = MutedPost
        fields = ["id", "post_id", "created_at"]
        read_only_fields = ["id", "created_at"]


class ReportedPostSerializer(serializers.ModelSerializer):
    """Serializer for reporting posts"""
    post_id = serializers.IntegerField(source="post.id", read_only=True)
    reason_display = serializers.SerializerMethodField()

    class Meta:
        model = ReportedPost
        fields = ["id", "post_id", "reason", "reason_display", "description", "status", "created_at"]
        read_only_fields = ["id", "status", "created_at"]

    def get_reason_display(self, obj):
        from apps.feed.models import REPORT_REASONS
        reason_dict = dict(REPORT_REASONS)
        
        # If reason is a list, map each one
        if isinstance(obj.reason, list):
            labels = [reason_dict.get(r, r) for r in obj.reason]
            return ", ".join(labels)
        
        # If reason is a string (legacy data or single value stored as string)
        return reason_dict.get(obj.reason, obj.reason)




# Friend Suggestion Serializers

class SuggestedFriendSerializer(serializers.Serializer):
    """Serializer for suggested friends"""
    user_id = serializers.IntegerField(source="suggested_user.id")
    name = serializers.CharField(source="suggested_user.user.name")
    bio = serializers.CharField(source="suggested_user.bio")
    profile_photo = serializers.SerializerMethodField()
    total_score = serializers.FloatField()
    reason = serializers.CharField()
    mutual_followers = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    
    def get_profile_photo(self, obj):
        """Get profile photo URL"""
        photo = getattr(obj.suggested_user, "profile_photo", None)
        if photo:
            from cloudinary.utils import cloudinary_url
            url, _ = cloudinary_url(photo)
            return url
        return None
    
    def get_mutual_followers(self, obj):
        """Count mutual followers"""
        from apps.feed.models import Follow
        user = self.context.get('request').user.profile
        
        # Get user's followers
        user_followers = set(Follow.objects.filter(following=user).values_list('follower_id', flat=True))
        
        # Get suggested user's followers
        suggested_followers = set(Follow.objects.filter(following=obj.suggested_user).values_list('follower_id', flat=True))
        
        # Count mutual
        mutual_count = len(user_followers & suggested_followers)
        return mutual_count
    
    def get_is_following(self, obj):
        """Check if current user is following suggested user"""
        from apps.feed.models import Follow
        user = self.context.get('request').user.profile
        return Follow.objects.filter(follower=user, following=obj.suggested_user).exists()
