from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny
from .models import CustomUser, UserProfile, OTPVerification
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    SignupSerializer,
    LoginSerializer,
    ProfileSerializer,
    ForgotPasswordOTPRequestSerializer,
    ForgotPasswordOTPVerifySerializer,
    ForgotPasswordResetSerializer,
    
)
import random


#  Signup
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
                "message": "Signup completed"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": 400,
            "success": False,
            "errors": serializer.errors,
            "message": "Signup failed"
        }, status=status.HTTP_400_BAD_REQUEST)



# Login
class LoginView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            return Response({
                "status": 200,
                "success": True,
                "user_id": user.id,
                "phone": user.phone,
                "access": access_token,
                "message": "Login successful"
            }, status=status.HTTP_200_OK)
        return Response({
            "status": 400,
            "success": False,
            "errors": serializer.errors,
            "message": "Login failed"
        }, status=status.HTTP_400_BAD_REQUEST)


# Profile 
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return Response({
            "status": 200,
            "success": True,
            "message": "User profile retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def put(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if 'user' in serializer.validated_data:
                request.user.name = serializer.validated_data['user'].get('name', request.user.name)
                request.user.save()
            return Response({
                "status": 200,
                "success": True,
                "message": "Profile updated successfully",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response({
            "status": 400,
            "success": False,
            "errors": serializer.errors,
            "message": "Profile update failed"
        }, status=status.HTTP_400_BAD_REQUEST)
    


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
            otp_code = str(random.randint(1000, 9999))
            OTPVerification.objects.create(user=user, otp=otp_code, purpose="reset")
            # For demo/testing, show OTP in response
            return Response({"message": "OTP sent to your phone", "otp": otp_code})
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
            try:
                otp_obj = OTPVerification.objects.filter(user=user, purpose="reset", otp=otp).latest('created_at')
            except OTPVerification.DoesNotExist:
                return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            otp_obj.delete()
            return Response({"message": "OTP verified. You can now reset your password."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordResetView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            phone = serializer.validated_data['phone']
            new_password = serializer.validated_data['new_password']
            try:
                user = CustomUser.objects.get(phone=phone)
            except CustomUser.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password reset successful"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
                "errors": {"detail": "All fields are required."},
                "message": "Change password failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({
                "status": 400,
                "success": False,
                "errors": {"detail": "Passwords do not match."},
                "message": "Change password failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(old_password):
            return Response({
                "status": 400,
                "success": False,
                "errors": {"detail": "Old password is incorrect."},
                "message": "Change password failed"
            }, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({
            "status": 200,
            "success": True,
            "message": "Password changed successfully"
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # refresh_token = request.data["refresh"]
            # token = RefreshToken(refresh_token)
            # token.blacklist()
            return Response({
                "status": 200,
                "success": True,
                "message": "Logout successful"
            }, status=status.HTTP_200_OK)
        except Exception:
            return Response({
                "status": 400,
                "success": False,
                "message": "Logout failed"
            }, status=status.HTTP_400_BAD_REQUEST)
