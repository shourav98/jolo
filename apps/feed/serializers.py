from rest_framework import serializers
from .models import Feed, FeedFile, FeedVideo, Comment, Like, Unlike, Story, StoryItem,CustomUser

class FeedCreateSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(required=False, allow_null=True)
    video = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Feed
        fields = ['content', 'image', 'video', 'status']

    def create(self, validated_data):
        user_profile = self.context['request'].user.profile
        return Feed.objects.create(profile=CustomUser, **validated_data)

class FeedVideoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedVideo
        fields = '__all__'

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'

class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = '__all__'

class UnlikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unlike
        fields = '__all__'

class StorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Story
        fields = '__all__'

class StoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoryItem
        fields = '__all__'