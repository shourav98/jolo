from django.urls import path
from .views import (
    SignupView,
    LoginView,
    ProfileView,
    ChangePasswordView,
    ForgotPasswordOTPRequestView,
    ForgotPasswordOTPVerifyView,
    ForgotPasswordResetView,
    LogoutView,
    DeleteAccountView,
    VerifyTokenAPIView,
    PublicProfileView,
)

urlpatterns = [
    path('signup/', SignupView.as_view(), name='signup'),
    path('login/', LoginView.as_view(), name='login'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/request/', ForgotPasswordOTPRequestView.as_view(), name='forgot-password-request'),
    path('forgot-password/verify/', ForgotPasswordOTPVerifyView.as_view(), name='forgot-password-verify'),
    path('forgot-password/reset/', ForgotPasswordResetView.as_view(), name='forgot-password-reset'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),

    path('verify-token/', VerifyTokenAPIView.as_view(), name='verify-token'),
    path("profile/<int:profile_id>/", PublicProfileView.as_view()),
]