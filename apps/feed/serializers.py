from rest_framework import serializers
from django.utils import timezone
from apps.feed.models import Feed, FeedFile, Comment, Unlock, TopFan
from apps.account.models import UserProfile


# FILE SERIALIZER 
class FeedFileSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = FeedFile
        fields = ["id", "file_url"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.file.url) if request else obj.file.url


#  FEED SERIALIZER 
class FeedSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="profile.user.name", read_only=True)
    author_id = serializers.IntegerField(source="profile.user.id", read_only=True)
    author_photo = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()  # ✅
    videos = serializers.SerializerMethodField()  # ✅
    is_unlocked = serializers.SerializerMethodField()

    class Meta:
        model = Feed
        fields = [
            "id",
            "author_id",
            "author_name",
            "author_photo",
            "content",
            "status",
            "unlock_price",
            "is_unlocked",
            "total_like",
            "total_comment",
            "total_view",
            "created_at",
            "images",   # ✅
            "videos",   # ✅
        ]
        read_only_fields = ("id", "total_like", "total_comment", "total_view", "created_at")

    def get_author_photo(self, obj):
        prof = getattr(obj.profile, "profile_photo", None)
        if prof:
            request = self.context.get("request")
            return request.build_absolute_uri(prof.url) if request else prof.url
        return None

    def get_images(self, obj):
        request = self.context.get("request")
        images = obj.files.filter(file_type="image")
        return [request.build_absolute_uri(f.file.url) for f in images] if request else [f.file.url for f in images]

    def get_videos(self, obj):
        request = self.context.get("request")
        videos = obj.files.filter(file_type="video")
        return [request.build_absolute_uri(f.file.url) for f in videos] if request else [f.file.url for f in videos]

    def get_is_unlocked(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return obj.status != "locked"
        return obj.is_unlocked_for(user)



#  COMMENT SERIALIZER 
class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="comment_by.user.name", read_only=True)
    user_photo = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "user_name", "user_photo", "content", "created_at"]

    def get_user_photo(self, obj):
        prof = getattr(obj.comment_by, "profile_photo", None)
        if prof:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(prof.url)
            return prof.url
        return None


#  TOP FAN SERIALIZER 
class TopFanSerializer(serializers.ModelSerializer):
    fan_id = serializers.IntegerField(source="fan.id", read_only=True)
    fan_name = serializers.CharField(source="fan.user.name", read_only=True)
    fan_photo = serializers.SerializerMethodField()

    class Meta:
        model = TopFan
        fields = ["fan_id", "fan_name", "fan_photo", "score", "last_interacted"]

    def get_fan_photo(self, obj):
        prof = getattr(obj.fan, "profile_photo", None)
        if prof:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(prof.url)
            return prof.url
        return None
