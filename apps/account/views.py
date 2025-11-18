from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

import jwt
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import CustomUser, OTPVerification
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.parsers import MultiPartParser, FormParser

from django.core.cache import cache
import uuid
from .serializers import (
    SignupSerializer,
    LoginSerializer,
    ProfileSerializer,
    ForgotPasswordOTPRequestSerializer,
    ForgotPasswordOTPVerifySerializer,
    ForgotPasswordResetSerializer,
)
import random





# Signup
class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "status": 201,
                "success": True,
                "user_id": user.id,
                "phone": user.phone,
                "message": "Signup completed successfully."
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": 400,
            "success": False,
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


# Login
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)

            user_data = {
                "id": user.id,
                "name": user.name,
                "phone": user.phone,
                "email": user.email,
                "role": user.role,
                "status": user.status,
                "gender": user.gender,
                "date_of_birth": user.date_of_birth,
                "street_address": user.street_address,
                "zip_code": user.zip_code,
                "city": user.city,
                "country": user.country,
                "avatar": user.avatar.url if user.avatar else None
            }

            return Response({
                "status": True,
                "message": "User logged in successfully.",
                "token": str(refresh.access_token),
                "userData": user_data,
                "code": 200
            }, status=200)

        return Response({
            "status": False,
            "message": "Invalid phone or password",
            "errors": serializer.errors,
            "code": 400
        }, status=400)



# Profile
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  

    def get(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, context={"request": request})
        return Response({
            "status": 200,
            "success": True,
            "data": serializer.data
        })

    def put(self, request):
        profile = request.user.profile

        # First, handle non-file fields
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            return Response({
                "status": 400,
                "success": False,
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Save the profile with non-file fields first
        profile = serializer.save()

        # Handle Cloudinary uploads for profile photos and documents
        profile_photo_file = request.FILES.get('profile_photo_file')
        cover_photo_file = request.FILES.get('cover_photo_file')
        id_proof_file = request.FILES.get('id_proof_file')
        intro_video_file = request.FILES.get('intro_video_file')

        import cloudinary.uploader
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Files received - profile_photo: {profile_photo_file}, cover_photo: {cover_photo_file}, id_proof: {id_proof_file}, intro_video: {intro_video_file}")

        try:
            if profile_photo_file:
                logger.info(f"Uploading profile photo: {profile_photo_file.name}")
                cloudinary_result = cloudinary.uploader.upload(
                    profile_photo_file,
                    resource_type="auto",
                    folder="profile_photos/"
                )
                profile.profile_photo = cloudinary_result['secure_url']
                profile.profile_photo_public_id = cloudinary_result['public_id']
                logger.info(f"Profile photo uploaded: {profile.profile_photo}")

            if cover_photo_file:
                logger.info(f"Uploading cover photo: {cover_photo_file.name}")
                cloudinary_result = cloudinary.uploader.upload(
                    cover_photo_file,
                    resource_type="auto",
                    folder="cover_photos/"
                )
                profile.cover_photo = cloudinary_result['secure_url']
                profile.cover_photo_public_id = cloudinary_result['public_id']
                logger.info(f"Cover photo uploaded: {profile.cover_photo}")

            if id_proof_file:
                logger.info(f"Uploading ID proof: {id_proof_file.name}")
                cloudinary_result = cloudinary.uploader.upload(
                    id_proof_file,
                    resource_type="auto",
                    folder="id_proofs/"
                )
                profile.id_proof = cloudinary_result['secure_url']
                profile.id_proof_public_id = cloudinary_result['public_id']
                logger.info(f"ID proof uploaded: {profile.id_proof}")

            if intro_video_file:
                logger.info(f"Uploading intro video: {intro_video_file.name}")
                cloudinary_result = cloudinary.uploader.upload(
                    intro_video_file,
                    resource_type="auto",
                    folder="intro_videos/"
                )
                profile.intro_video = cloudinary_result['secure_url']
                profile.intro_video_public_id = cloudinary_result['public_id']
                logger.info(f"Intro video uploaded: {profile.intro_video}")

        except Exception as e:
            logger.error(f"Cloudinary upload error: {str(e)}")
            return Response({
                "status": 500,
                "success": False,
                "message": f"File upload failed: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save profile with Cloudinary URLs
        profile.save()

        # Update user name if provided
        full_name = request.data.get('full_name')
        if full_name:
            request.user.name = full_name
            request.user.save()

        # Return updated data
        response_serializer = ProfileSerializer(profile, context={"request": request})
        return Response({
            "status": 200,
            "success": True,
            "message": "Profile updated successfully",
            "data": response_serializer.data
        })


# Forgot Password Flow
class ForgotPasswordOTPRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordOTPRequestSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            try:
                user = CustomUser.objects.get(phone=phone)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            otp_code = str(random.randint(10000, 99999))
            OTPVerification.objects.create(user=user, otp=otp_code, purpose="reset")

            return Response({"message": "OTP sent successfully", "otp": otp_code})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            otp = serializer.validated_data['otp']

            try:
                user = CustomUser.objects.get(phone=phone)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

            otp_obj = OTPVerification.objects.filter(
                user=user, purpose="reset", otp=otp, is_used=False
            ).order_by('-created_at').first()

            if not otp_obj:
                return Response({"error": "Invalid or already used OTP"}, status=status.HTTP_400_BAD_REQUEST)

            if otp_obj.is_expired():
                otp_obj.delete()
                return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

            otp_obj.is_used = True
            otp_obj.save()

            # Generate reset token
            reset_token = str(uuid.uuid4())

            # Store token in cache (key=token, value=user_id)
            cache.set(reset_token, user.id, timeout=300)  

            return Response({
                "status": 200,
                "success": True,
                "message": "OTP verified successfully.",
                "reset_token": reset_token
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class ForgotPasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        reset_token = request.data.get('reset_token')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')

        if not reset_token:
            return Response({"error": "Reset token is required"}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"error": "Passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        # Get user_id from cache
        user_id = cache.get(reset_token)
        if not user_id:
            return Response({"error": "Invalid or expired reset token"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        #  Reset password
        user.set_password(new_password)
        user.save()

        # Delete used token
        cache.delete(reset_token)

        return Response({
            "status": 200,
            "success": True,
            "message": "Password reset successful."
        }, status=status.HTTP_200_OK)

#change password

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        confirm_password = request.data.get("confirm_password")

        if not old_password or not new_password or not confirm_password:
            return Response({
                "status": 400,
                "success": False,
                "message": "All fields are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({
                "status": 400,
                "success": False,
                "message": "Passwords do not match."
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(old_password):
            return Response({
                "status": 400,
                "success": False,
                "message": "Old password is incorrect."
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({
            "status": 200,
            "success": True,
            "message": "Password changed successfully."
        }, status=status.HTTP_200_OK)

#logout
class LogoutView(APIView):
    
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            
            return Response({
                "status": 200,
                "success": True,
                "message": "Logout successful."
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({
                "status": 400,
                "success": False,
                "message": "Logout failed."
            }, status=status.HTTP_400_BAD_REQUEST)
        






class VerifyTokenAPIView(APIView):
    permission_classes = [AllowAny]  # Change this to AllowAny
    
    def get(self, request):
        # Get token from query params (same way WebSocket does)
        token = request.GET.get('token')
        
        if not token:
            return Response({'error': 'No token provided'}, status=400)
        
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=["HS256"],
                options={"verify_exp": True}
            )
            
            user_id = payload.get('user_id')
            
            # Try to get the user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            try:
                user = User.objects.get(id=user_id)
                return Response({
                    'valid': True,
                    'user_id': user_id,
                    'user_name': user.name,
                    'exp': payload.get('exp')
                })
            except User.DoesNotExist:
                return Response({'valid': False, 'error': 'User not found'})
                
        except jwt.ExpiredSignatureError:
            return Response({'valid': False, 'error': 'Token expired'})
        except jwt.InvalidTokenError as e:
            return Response({'valid': False, 'error': str(e)})