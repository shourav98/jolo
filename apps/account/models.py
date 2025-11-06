from django.db import models
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from datetime import timedelta
from .managers import CustomUserManager



class CustomUser(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = ["name"]

    username = None
    objects = CustomUserManager()

    def __str__(self):
        return f"{self.name} ({self.phone})"


class OTPVerification(models.Model):
    PURPOSE_CHOICES = (
        ("signup", "Signup"),
        ("reset", "Password Reset"),
    )

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="otps")
    otp = models.CharField(max_length=4)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.phone} - {self.purpose} - {self.otp}"

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)


class UserProfile(models.Model):
    GENDER_CHOICES = (
        ("male", "Male"),
        ("female", "Female"),
        ("other", "Other"),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    # profile_photo = models.ImageField(
    #     upload_to="profile_photos/%Y/%m/%d/", blank=True, null=True
    # )
    profile_photo = models.URLField(null=True, blank=True)  # Store Cloudinary URL
    profile_photo_public_id = models.CharField(max_length=255, null=True, blank=True)  # Store Cloudinary public ID
    cover_photo = models.URLField(null=True, blank=True)  # Store Cloudinary URL
    cover_photo_public_id = models.CharField(max_length=255, null=True, blank=True)  # Store Cloudinary public ID
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    street_address = models.CharField(max_length=255, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)

    bio = models.TextField(blank=True, null=True)
    flirt_line = models.CharField(max_length=255, blank=True, null=True)
    is_creator = models.BooleanField(default=False)

    # New fields for chat functionality
    welcome_message = models.TextField(blank=True, null=True, help_text="Auto-reply welcome message for creators")
    auto_translate = models.BooleanField(default=True, help_text="Auto-translate messages")
    is_online = models.BooleanField(default=False)
    last_online = models.DateTimeField(default=timezone.now)
    # Monetization Application
    id_proof = models.URLField(null=True, blank=True)  # Store Cloudinary URL
    id_proof_public_id = models.CharField(max_length=255, null=True, blank=True)  # Store Cloudinary public ID
    intro_video = models.URLField(null=True, blank=True)  # Store Cloudinary URL
    intro_video_public_id = models.CharField(max_length=255, null=True, blank=True)  # Store Cloudinary public ID

    def __str__(self):
        return f"{self.user.name}'s Profile"
