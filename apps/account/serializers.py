from rest_framework import serializers
from .models import CustomUser, UserProfile, OTPVerification
from django.contrib.auth import authenticate
from apps.feed.models import Feed
from apps.feed.serializers import FeedSerializer


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    gender = serializers.CharField(required=False)
    date_of_birth = serializers.DateField(required=False)
    street_address = serializers.CharField(required=False)
    zip_code = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    country = serializers.CharField(required=False)

    class Meta:
        model = CustomUser
        fields = [
            'name', 'phone', 'password', 'confirm_password',
            'gender', 'date_of_birth',
            'street_address', 'zip_code', 'city', 'country'
        ]

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        profile_fields = ['gender', 'date_of_birth', 'street_address', 'zip_code', 'city', 'country']
        user_data = {k: validated_data[k] for k in ['phone', 'name', 'password'] if k in validated_data}
        validated_data.pop('confirm_password', None)

        user = CustomUser.objects.create_user(**user_data)
        user.is_active = True
        user.save()

        profile_data = {k: validated_data.get(k) for k in profile_fields}
        if profile_data:
            profile = getattr(user, "profile", None)
            if profile:
                for key, value in profile_data.items():
                    setattr(profile, key, value)
                profile.save()

        return user
    


class LoginSerializer(serializers.Serializer):
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(phone=attrs['phone'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError("Invalid phone or password")
        if not user.is_active:
            raise serializers.ValidationError("Account not active")
        attrs['user'] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.name', required=False)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)

    # Upload fields (input)
    profile_photo_file = serializers.FileField(required=False, write_only=True)
    cover_photo_file = serializers.FileField(required=False, write_only=True)
    id_proof_file = serializers.FileField(required=False, write_only=True)
    intro_video_file = serializers.FileField(required=False, write_only=True)

    # Display URLs (output)
    profile_photo_url = serializers.SerializerMethodField()
    cover_photo_url = serializers.SerializerMethodField()
    id_proof_url = serializers.SerializerMethodField()
    intro_video_url = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id", "full_name",
            "gender", "date_of_birth", "street_address", "zip_code",
            "city", "country", "bio", "flirt_line",
            "is_creator", "is_active",
            # Upload fields
            "profile_photo_file", "cover_photo_file",
            "id_proof_file", "intro_video_file",
            # Display fields
            "profile_photo_url", "cover_photo_url",
            "id_proof_url", "intro_video_url",
            # Stats
            "total_followers", "total_following", "total_videos", "total_feeds",
        ]

    # For displaying profile photo URL
    def get_profile_photo_url(self, obj):
        if getattr(obj, "profile_photo", None):
            return obj.profile_photo
        return None

    # For displaying cover photo URL
    def get_cover_photo_url(self, obj):
        if getattr(obj, "cover_photo", None):
            return obj.cover_photo
        return None

    def get_id_proof_url(self, obj):
        if getattr(obj, "id_proof", None):
            return obj.id_proof
        return None

    def get_intro_video_url(self, obj):
        if getattr(obj, "intro_video", None):
            return obj.intro_video
        return None

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        if user_data and "name" in user_data:
            instance.user.name = user_data["name"]
            instance.user.save()

        # normal update
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance

class ProfileDetailSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="user.name")

    feeds = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "name",
            "profile_photo",
            "cover_photo",
            "bio",
            "flirt_line",
            "is_creator",
            "total_followers",
            "total_following",
            "total_videos",
            "total_feeds",
            "is_following",
            "feeds",
        ]

    def get_is_following(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False

        from apps.feed.models import Follow
        return Follow.objects.filter(
            follower=request.user.profile,
            following=obj
        ).exists()

    def get_feeds(self, obj):
        request = self.context.get("request")

        qs = (
            Feed.objects
            .filter(profile=obj, status="public")
            .order_by("-created_at")[:10]   # ✅ LIMIT HERE
        )

        return FeedSerializer(qs, many=True, context={"request": request}).data

    


class ForgotPasswordOTPRequestSerializer(serializers.Serializer):
    phone = serializers.CharField()


class ForgotPasswordOTPVerifySerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField(max_length=5)


class ForgotPasswordResetSerializer(serializers.Serializer):
    phone = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match")
        return data
