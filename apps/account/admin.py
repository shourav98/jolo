from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django import forms

from unfold.admin import ModelAdmin

from unfold.admin import ModelAdmin  # ✅ Unfold base admin
from .models import CustomUser, UserProfile



# 🔹 Remove Groups from sidebar
admin.site.unregister(Group)


# 🔹 Custom User Creation & Change Forms
class CustomUserCreationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('phone', 'name', 'password')


class CustomUserChangeForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('phone', 'name', 'is_active', 'is_staff', 'is_superuser')


@admin.register(CustomUser)
class CustomUserAdmin(ModelAdmin):
    model = CustomUser


# 🔹 Inline Profile Admin (editable inside user page)
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    extra = 0


# 🔹 Custom User Admin — clean & Unfold-styled
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin, ModelAdmin):

    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    inlines = [UserProfileInline]

    # Displayed columns
    list_display = ("phone", "name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "is_superuser")
    search_fields = ("phone", "name")
    ordering = ("phone",)

    # Remove “groups” and “permissions”
    fieldsets = (
        (None, {"fields": ("phone", "name", "password")}),
        ("Permissions", {"fields": ("is_staff", "is_active", "is_superuser")}),
    )

    # Add form field layout
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "name", "password1", "password2", "is_staff", "is_active"),
        }),
    )


admin.site.register(UserProfile)


# 🔹 Separate UserProfile registration (optional)
@admin.register(UserProfile)
class UserProfileAdmin(ModelAdmin):
    list_display = ("user", "gender", "city", "country", "is_creator")
    list_filter = ("gender", "is_creator")
    search_fields = ("user__name", "user__phone", "city", "country")

