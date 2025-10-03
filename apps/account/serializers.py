from rest_framework import serializers
from .models import CustomUser, UserProfile, OTPVerification
from django.contrib.auth import authenticate

class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    # profile_photo = serializers.ImageField(required=False)
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
        profile_fields = ['profile_photo', 'gender', 'date_of_birth', 'street_address', 'zip_code', 'city', 'country']
        user_data = {k: validated_data[k] for k in ['phone', 'name', 'password']}
        validated_data.pop('confirm_password')
        user = CustomUser.objects.create_user(**user_data)
        user.is_active = True 
        user.save()
        profile_data = {k: validated_data.get(k) for k in profile_fields}
        UserProfile.objects.create(user=user, **profile_data)
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
    full_name = serializers.CharField(source='user.name')
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
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
            'is_active',
        ]

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