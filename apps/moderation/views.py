import logging
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .services import moderate_text, moderate_visual
from .models import ContentViolationLog, UserModerationProfile
from .serializers import (
    TextModerationSerializer,
    VisualModerationSerializer,
    ContentViolationLogSerializer,
    AppealSerializer,
    UserModerationProfileSerializer,
    ManualRestrictionSerializer,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
#  Public / Authenticated endpoints
# ─────────────────────────────────────────────

class ModerateTextView(APIView):
    """
    POST /api/moderate/text/

    Standalone text moderation check.
    Any authenticated user can call this.
    Body: { "text": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TextModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = moderate_text(serializer.validated_data["text"])

        if result.get("status") == "error":
            return Response(
                {"detail": "Hive AI service error", "error": result.get("detail")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(result, status=status.HTTP_200_OK)


class ModerateVisualView(APIView):
    """
    POST /api/moderate/visual/

    Standalone visual (image/video) moderation check.
    Any authenticated user can call this.
    Body: { "media_url": "https://..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = VisualModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = moderate_visual(serializer.validated_data["media_url"])

        if result.get("status") == "error":
            return Response(
                {"detail": "Hive AI service error", "error": result.get("detail")},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(result, status=status.HTTP_200_OK)


# ─────────────────────────────────────────────
#  Admin-only moderation log endpoints
# ─────────────────────────────────────────────

class ViolationLogListView(APIView):
    """
    GET /api/moderate/logs/

    List all ContentViolationLog entries.
    Admin only.

    Query filters:
      ?action_taken=banned|restricted|warned|none
      ?user_id=<int>
      ?appeal_status=pending|approved|rejected|none
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = ContentViolationLog.objects.select_related("user", "reviewed_by", "feed").all()

        action_taken = request.query_params.get("action_taken")
        if action_taken:
            qs = qs.filter(action_taken=action_taken)

        user_id = request.query_params.get("user_id")
        if user_id:
            qs = qs.filter(user_id=user_id)

        appeal_status = request.query_params.get("appeal_status")
        if appeal_status:
            qs = qs.filter(appeal_status=appeal_status)

        serializer = ContentViolationLogSerializer(qs, many=True)
        return Response(serializer.data)


class ViolationLogDetailView(APIView):
    """
    GET /api/moderate/logs/<id>/

    Detail view for a single violation log.
    Admin only.
    """
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        try:
            log = ContentViolationLog.objects.select_related("user", "reviewed_by", "feed").get(pk=pk)
        except ContentViolationLog.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ContentViolationLogSerializer(log)
        return Response(serializer.data)


class AppealDecisionView(APIView):
    """
    PATCH /api/moderate/logs/<id>/appeal/

    Admin approves or rejects a user's appeal.
    - approved → restores action_taken to "none" (NOTE: post is already deleted, admin decision is symbolic)
    - rejected → confirms the original action stands
    Body: { "decision": "approved" | "rejected", "admin_notes": "..." }
    """
    permission_classes = [IsAdminUser]

    def patch(self, request, pk):
        try:
            log = ContentViolationLog.objects.select_related("user").get(pk=pk)
        except ContentViolationLog.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AppealSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]
        admin_notes = serializer.validated_data.get("admin_notes", "")

        log.appeal_status = decision
        log.reviewed_by = request.user
        log.reviewed_at = timezone.now()
        if admin_notes:
            log.admin_notes = admin_notes

        if decision == "approved":
            # If appeal approved, lift restriction for the user if this was their only violation
            mod_profile = getattr(log.user, "moderation_profile", None)
            if mod_profile and mod_profile.violation_count >= 1:
                mod_profile.violation_count = max(0, mod_profile.violation_count - 1)
                if mod_profile.violation_count == 0:
                    mod_profile.restriction_level = "none"
                    mod_profile.restricted_until = None
                elif mod_profile.violation_count == 1:
                    mod_profile.restriction_level = "warned"
                    mod_profile.restricted_until = None
                mod_profile.save()

            # If user was banned, reactivate them
            if log.action_taken == "banned":
                log.user.is_active = True
                log.user.save(update_fields=["is_active"])

        log.save()

        return Response(
            {"detail": f"Appeal {decision}.", "log": ContentViolationLogSerializer(log).data},
            status=status.HTTP_200_OK,
        )


# ─────────────────────────────────────────────
#  Admin user moderation profile endpoints
# ─────────────────────────────────────────────

class UserModerationProfileListView(APIView):
    """
    GET /api/moderate/users/

    List all user moderation profiles.
    Admin only.

    Query filters:
      ?restriction_level=none|warned|restricted|banned
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        qs = UserModerationProfile.objects.select_related("user").all()

        restriction_level = request.query_params.get("restriction_level")
        if restriction_level:
            qs = qs.filter(restriction_level=restriction_level)

        serializer = UserModerationProfileSerializer(qs, many=True)
        return Response(serializer.data)


class UserModerationProfileDetailView(APIView):
    """
    GET  /api/moderate/users/<id>/    — view user's moderation state
    PATCH /api/moderate/users/<id>/  — admin manually adjusts restriction level

    Body for PATCH:
    {
        "restriction_level": "none" | "warned" | "restricted" | "banned",
        "restricted_until": "2026-04-01T00:00:00Z",  // optional
        "admin_notes": "..."  // optional
    }
    """
    permission_classes = [IsAdminUser]

    def _get_object(self, pk):
        try:
            return UserModerationProfile.objects.select_related("user").get(pk=pk)
        except UserModerationProfile.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(UserModerationProfileSerializer(obj).data)

    def patch(self, request, pk):
        obj = self._get_object(pk)
        if not obj:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ManualRestrictionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_level = serializer.validated_data["restriction_level"]
        obj.restriction_level = new_level
        obj.restricted_until = serializer.validated_data.get("restricted_until")
        if serializer.validated_data.get("admin_notes"):
            obj.admin_notes = serializer.validated_data["admin_notes"]
        obj.save()

        # Sync account active state
        user = obj.user
        if new_level == "banned":
            user.is_active = False
        else:
            user.is_active = True
        user.save(update_fields=["is_active"])

        logger.info(
            f"[Moderation] Admin {request.user} manually set {user} restriction to '{new_level}'."
        )

        return Response(
            {"detail": f"User restriction updated to '{new_level}'.", "profile": UserModerationProfileSerializer(obj).data},
            status=status.HTTP_200_OK,
        )
