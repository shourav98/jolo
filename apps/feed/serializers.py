from rest_framework import serializers
from apps.feed.models import Feed, FeedFile, Comment, TopFan


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
            "images",
            "videos",
        ]

    def get_author_photo(self, obj):
        return build_url(self.context.get("request"), getattr(obj.profile, "profile_photo", None))

    def get_images(self, obj):
        request = self.context.get("request")
        return [build_url(request, f.file) for f in obj.files.filter(file_type="image")]

    def get_videos(self, obj):
        request = self.context.get("request")
        return [build_url(request, f.file) for f in obj.files.filter(file_type="video")]

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




class CommentSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="comment_by.user.name", read_only=True)
    user_photo = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ["id", "user_name", "user_photo", "content", "created_at"]

    def get_user_photo(self, obj):
        return build_url(self.context.get("request"), getattr(obj.comment_by, "profile_photo", None))


class TopFanSerializer(serializers.ModelSerializer):
    fan_id = serializers.IntegerField(source="fan.id", read_only=True)
    fan_name = serializers.CharField(source="fan.user.name", read_only=True)
    fan_photo = serializers.SerializerMethodField()

    class Meta:
        model = TopFan
        fields = ["fan_id", "fan_name", "fan_photo", "score", "last_interacted"]

    def get_fan_photo(self, obj):
        return build_url(self.context.get("request"), getattr(obj.fan, "profile_photo", None))
    




    

# from rest_framework import serializers
# from django.utils import timezone
# from apps.feed.models import Feed, FeedFile, Comment, Unlock, TopFan
# from apps.account.models import UserProfile


# # FILE SERIALIZER 
# class FeedFileSerializer(serializers.ModelSerializer):
#     file_url = serializers.SerializerMethodField()

#     class Meta:
#         model = FeedFile
#         fields = ["id", "file_url"]

#     def get_file_url(self, obj):
#         request = self.context.get("request")
#         return request.build_absolute_uri(obj.file.url) if request else obj.file.url


# #  FEED SERIALIZER 
# class FeedSerializer(serializers.ModelSerializer):
#     author_name = serializers.CharField(source="profile.user.name", read_only=True)
#     author_id = serializers.IntegerField(source="profile.user.id", read_only=True)
#     author_photo = serializers.SerializerMethodField()
#     images = serializers.SerializerMethodField()
#     videos = serializers.SerializerMethodField()
#     is_unlocked = serializers.SerializerMethodField()

#     class Meta:
#         model = Feed
#         fields = [
#             "id",
#             "author_id",
#             "author_name",
#             "author_photo",
#             "content",
#             "status",
#             "unlock_price",
#             "is_unlocked",
#             "total_like",
#             "total_comment",
#             "total_view",
#             "created_at",
#             "images",
#             "videos",
#         ]
#         read_only_fields = ("id", "unlock_price", "total_like", "total_comment", "total_view", "created_at")

#     # Author photo
#     def get_author_photo(self, obj):
#         prof = getattr(obj.profile, "profile_photo", None)
#         if not prof:
#             return None

#         request = self.context.get("request")

#         # If the photo is a FileField (has .url)
#         if hasattr(prof, "url"):
#             url = prof.url
#         else:
#             # Already a string — could be Cloudinary or any absolute URL
#             url = str(prof)

#         # If URL is relative, build full absolute URI
#         if request and not url.startswith("http"):
#             return request.build_absolute_uri(url)
#         return url

#     # Images
#     def get_images(self, obj):
#         request = self.context.get("request")
#         images = obj.files.filter(file_type="image")

#         urls = []
#         for f in images:
#             file_obj = f.file
#             # Handle both FileField and string URL
#             url = file_obj.url if hasattr(file_obj, "url") else str(file_obj)

#             # Build absolute URI only if it’s a relative path
#             if request and not url.startswith("http"):
#                 url = request.build_absolute_uri(url)
#             urls.append(url)

#         return urls

#     # Videos
#     def get_videos(self, obj):
#         request = self.context.get("request")
#         videos = obj.files.filter(file_type="video")

#         urls = []
#         for f in videos:
#             file_obj = f.file
#             url = file_obj.url if hasattr(file_obj, "url") else str(file_obj)

#             if request and not url.startswith("http"):
#                 url = request.build_absolute_uri(url)
#             urls.append(url)

#         return urls

#     # Unlocked Logic (clear & tier-safe)
#     def get_is_unlocked(self, obj):
#         request = self.context.get("request")
#         user = getattr(request, "user", None)

#         # Not logged in → only public feeds are visible
#         if not user or not user.is_authenticated:
#             return obj.status != "locked"

#         # Creator always sees their own locked content
#         if hasattr(user, "profile") and user.profile.id == obj.profile_id:
#             return True

#         # For locked feeds, check if this fan has unlocked it
#         if obj.status == "locked":
#             return obj.is_unlocked_for(user)

#         # For public or follower-only feeds, always visible
#         return True




# #  COMMENT SERIALIZER 
# class CommentSerializer(serializers.ModelSerializer):
#     user_name = serializers.CharField(source="comment_by.user.name", read_only=True)
#     user_photo = serializers.SerializerMethodField()

#     class Meta:
#         model = Comment
#         fields = ["id", "user_name", "user_photo", "content", "created_at"]

#     def get_user_photo(self, obj):
#         prof = getattr(obj.comment_by, "profile_photo", None)
#         if prof:
#             request = self.context.get("request")
#             if request:
#                 return request.build_absolute_uri(prof.url)
#             return prof.url
#         return None


# #  TOP FAN SERIALIZER 
# class TopFanSerializer(serializers.ModelSerializer):
#     fan_id = serializers.IntegerField(source="fan.id", read_only=True)
#     fan_name = serializers.CharField(source="fan.user.name", read_only=True)
#     fan_photo = serializers.SerializerMethodField()

#     class Meta:
#         model = TopFan
#         fields = ["fan_id", "fan_name", "fan_photo", "score", "last_interacted"]

#     def get_fan_photo(self, obj):
#         prof = getattr(obj.fan, "profile_photo", None)
#         if prof:
#             request = self.context.get("request")
#             if request:
#                 return request.build_absolute_uri(prof.url)
#             return prof.url
#         return None
