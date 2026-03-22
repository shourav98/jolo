from rest_framework import serializers
from .models import ContentViolationLog, UserModerationProfile


# ──────────────────────────────────
#  Standalone moderation request
# ──────────────────────────────────

class TextModerationSerializer(serializers.Serializer):
    text = serializers.CharField(
        help_text="The text content to scan for policy violations."
    )


class VisualModerationSerializer(serializers.Serializer):
    media_url = serializers.URLField(
        help_text="Public URL of an image or video to scan."
    )


# ──────────────────────────────────
#  Admin read serializers
# ──────────────────────────────────

class ContentViolationLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.name", read_only=True, default=None)

    class Meta:
        model = ContentViolationLog
        fields = [
            "id",
            "feed",
            "user",
            "user_name",
            "user_phone",
            "content_type",
            "violation_categories",
            "action_taken",
            "ai_raw_response",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "admin_notes",
            "appeal_status",
            "appeal_note",
            "created_at",
        ]
        read_only_fields = [
            "id", "feed", "user", "user_name", "user_phone",
            "content_type", "violation_categories", "action_taken",
            "ai_raw_response", "reviewed_by", "reviewed_by_name",
            "reviewed_at", "created_at",
        ]


class AppealSerializer(serializers.Serializer):
    """Used by admin to approve or reject an appeal."""
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")


class UserModerationProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)
    user_phone = serializers.CharField(source="user.phone", read_only=True)
    is_currently_restricted = serializers.SerializerMethodField()

    class Meta:
        model = UserModerationProfile
        fields = [
            "id",
            "user",
            "user_name",
            "user_phone",
            "violation_count",
            "restriction_level",
            "restricted_until",
            "last_violation_at",
            "admin_notes",
            "is_currently_restricted",
        ]
        read_only_fields = [
            "id", "user", "user_name", "user_phone",
            "violation_count", "last_violation_at",
        ]

    def get_is_currently_restricted(self, obj):
        return obj.is_currently_restricted()


class ManualRestrictionSerializer(serializers.Serializer):
    """Used by admin to manually adjust a user's restriction level."""
    restriction_level = serializers.ChoiceField(choices=["none", "warned", "restricted", "banned"])
    restricted_until = serializers.DateTimeField(required=False, allow_null=True)
    admin_notes = serializers.CharField(required=False, allow_blank=True, default="")
