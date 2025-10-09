from rest_framework import serializers
from django.contrib.contenttypes.models import ContentType
from .models import (
    UserProfile, Feed, FeedFile, FeedVideo,
    Comment, Like, Unlike, Story, StoryItem,
    CreatorProfile, TopFan, Transaction
)


# Profile / Creator 
class ProfileSerializer(serializers.ModelSerializer):
   
    full_name = serializers.CharField(source='user.name', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'id',
            'full_name',
            'profile_photo',
            'gender',
            'date_of_birth',
            'street_address',
            'zip_code',
            'city',
            'country',
            'bio',
            'first_line',
            'is_creator',
        ]


class CreatorProfileSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    class Meta:
        model = CreatorProfile
        fields = ['id', 'profile', 'start_date', 'status']


#  Feed / Files 
class FeedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedFile
        fields = ['id', 'file', 'created_at']


class FeedSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    files = FeedFileSerializer(many=True, read_only=True)

    class Meta:
        model = Feed
        fields = [
            'id', 'profile', 'content', 'status',
            'total_like', 'total_unlike', 'total_comment',
            'files', 'created_at', 'updated_at'
        ]


class FeedCreateSerializer(serializers.ModelSerializer):
    # Accept multiple files via multipart form-data key 'files'
    files = serializers.ListField(
        child=serializers.FileField(), write_only=True, required=False
    )
    # Accept optional video file to create FeedVideo
    video = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = Feed
        fields = ['content', 'status', 'files', 'video']

    def create(self, validated_data):
        request = self.context.get('request')
        files = validated_data.pop('files', [])
        video = validated_data.pop('video', None)

        # Profile model connected to request.user (assumes OneToOne user->Profile exists)
        profile = getattr(request.user, 'profile', None) or Profile.objects.get(user=request.user)
        feed = Feed.objects.create(profile=profile, **validated_data)

        for f in files:
            FeedFile.objects.create(feed=feed, file=f)

        if video:
            # create a FeedVideo for the same user
            FeedVideo.objects.create(profile=profile, file=video, title='', description='')

        return feed


#  FeedVideo 
class FeedVideoSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = FeedVideo
        fields = [
            'id', 'profile', 'file', 'title', 'description',
            'total_like', 'total_unlike', 'total_comment', 'total_view', 'total_earn', 'created_at'
        ]
        read_only_fields = ['total_like', 'total_unlike', 'total_comment', 'total_view', 'total_earn', 'created_at']


#  Comment / Like / Unlike 
class CommentSerializer(serializers.ModelSerializer):
    comment_by = ProfileSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'comment_by', 'content', 'created_at']
        read_only_fields = ['comment_by', 'created_at']


class SimpleCommentCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=2000)


class LikeSerializer(serializers.ModelSerializer):
    liked_by = ProfileSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'liked_by', 'created_at']


class UnlikeSerializer(serializers.ModelSerializer):
    unliked_by = ProfileSerializer(read_only=True)

    class Meta:
        model = Unlike
        fields = ['id', 'unliked_by', 'created_at']


# Story
class StoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryItem
        fields = ['id', 'file', 'created_at', 'expired_at', 'is_active', 'total_view']


class StorySerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)
    items = StoryItemSerializer(many=True, read_only=True)

    class Meta:
        model = Story
        fields = ['id', 'profile', 'created_at', 'items']


# TopFan / Transaction 
class TopFanSerializer(serializers.ModelSerializer):
    iam = ProfileSerializer(read_only=True)
    fan_profile = ProfileSerializer(read_only=True)
    class Meta:
        model = TopFan
        fields = ['id', 'iam', 'fan_profile', 'status']


class TransactionSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer(read_only=True)

    class Meta:
        model = Transaction
        fields = ['id', 'profile', 'type', 'amount', 'created_at']
        read_only_fields = ['created_at', 'profile']
