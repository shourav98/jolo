from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

import jwt
from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import CustomUser, OTPVerification
from rest_framework_simplejwt.tokens import RefreshToken
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
            return Response({
                "status": 200,
                "success": True,
                "access": str(refresh.access_token),
                # "refresh": str(refresh),
                "message": "Login successful"
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Profile
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile)
        return Response({
            "status": 200,
            "success": True,
            "data": serializer.data
        })

    def put(self, request):
        profile = request.user.profile
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            full_name = request.data.get('full_name')
            if full_name:
                request.user.name = full_name
                request.user.save()
            return Response({
                "status": 200,
                "success": True,
                "message": "Profile updated successfully",
                "data": serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({"message": "OTP verified successfully"})
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