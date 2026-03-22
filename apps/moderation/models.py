from django.db import models
from django.conf import settings


# ─────────────────────────────────────────────
#  Choices
# ─────────────────────────────────────────────

CONTENT_TYPE_CHOICES = (
    ("text",   "Text"),
    ("visual", "Visual (Image/Video)"),
    ("both",   "Text + Visual"),
    ("none",   "None (clean)"),
)

ACTION_TAKEN_CHOICES = (
    ("none",       "No Action (clean)"),
    ("warned",     "Warned — post removed"),
    ("restricted", "Restricted — post removed, posting blocked"),
    ("banned",     "Banned — account deactivated"),
)

RESTRICTION_LEVEL_CHOICES = (
    ("none",       "No Restrictions"),
    ("warned",     "Warned (1 violation)"),
    ("restricted", "Restricted (2 violations, posting blocked)"),
    ("banned",     "Permanently Banned"),
)

APPEAL_STATUS_CHOICES = (
    ("none",     "No Appeal"),
    ("pending",  "Appeal Pending"),
    ("approved", "Appeal Approved — content restored"),
    ("rejected", "Appeal Rejected"),
)


# ─────────────────────────────────────────────
#  ContentViolationLog
# ─────────────────────────────────────────────

class ContentViolationLog(models.Model):
    """
    Records every AI moderation decision.
    Facebook-style audit trail for admins to review.
    """
    # The offending post (nullable: may be deleted)
    feed = models.ForeignKey(
        "feed.Feed",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="violation_logs",
    )
    # The user who created the post
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="violation_logs",
    )

    # What type of content triggered the flag
    content_type = models.CharField(max_length=10, choices=CONTENT_TYPE_CHOICES, default="none")

    # Snapshot of flagged categories from Hive AI
    violation_categories = models.JSONField(default=list)

    # What penalty was applied automatically
    action_taken = models.CharField(max_length=16, choices=ACTION_TAKEN_CHOICES, default="none")

    # Full raw Hive AI response (for transparency/debugging)
    ai_raw_response = models.JSONField(default=dict)

    # Admin review fields
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="moderation_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, default="")

    # Appeal system
    appeal_status = models.CharField(max_length=16, choices=APPEAL_STATUS_CHOICES, default="none")
    appeal_note = models.TextField(blank=True, default="", help_text="User's appeal message or admin note")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Content Violation Log"
        verbose_name_plural = "Content Violation Logs"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["action_taken", "-created_at"]),
            models.Index(fields=["appeal_status"]),
        ]

    def __str__(self):
        return f"[{self.action_taken.upper()}] {self.user} — {self.created_at.strftime('%Y-%m-%d %H:%M')}"


# ─────────────────────────────────────────────
#  UserModerationProfile
# ─────────────────────────────────────────────

class UserModerationProfile(models.Model):
    """
    Strike counter and restriction state for each user.
    Created lazily the first time a user receives a violation.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="moderation_profile",
    )

    violation_count = models.PositiveIntegerField(default=0)
    restriction_level = models.CharField(
        max_length=16,
        choices=RESTRICTION_LEVEL_CHOICES,
        default="none",
    )
    # Temporary restriction end time (None = permanent ban or no restriction)
    restricted_until = models.DateTimeField(null=True, blank=True)

    last_violation_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, default="", help_text="Internal admin notes about this user")

    class Meta:
        verbose_name = "User Moderation Profile"
        verbose_name_plural = "User Moderation Profiles"

    def __str__(self):
        return f"{self.user} — {self.restriction_level} ({self.violation_count} violations)"

    def is_currently_restricted(self):
        """Returns True if the user is in a posting restriction window."""
        from django.utils import timezone
        if self.restriction_level == "banned":
            return True
        if self.restriction_level == "restricted" and self.restricted_until:
            return timezone.now() < self.restricted_until
        return False
