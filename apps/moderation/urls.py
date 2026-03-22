from django.urls import path
from .views import (
    ModerateTextView,
    ModerateVisualView,
    ViolationLogListView,
    ViolationLogDetailView,
    AppealDecisionView,
    UserModerationProfileListView,
    UserModerationProfileDetailView,
)

urlpatterns = [
    # ── Public / Authenticated ──
    path("text/",   ModerateTextView.as_view(),   name="moderate-text"),
    path("visual/", ModerateVisualView.as_view(), name="moderate-visual"),

    # ── Admin: Violation Logs ──
    path("logs/",                ViolationLogListView.as_view(),   name="moderation-log-list"),
    path("logs/<int:pk>/",       ViolationLogDetailView.as_view(), name="moderation-log-detail"),
    path("logs/<int:pk>/appeal/", AppealDecisionView.as_view(),    name="moderation-appeal"),

    # ── Admin: User Moderation Profiles ──
    path("users/",           UserModerationProfileListView.as_view(),   name="moderation-user-list"),
    path("users/<int:pk>/",  UserModerationProfileDetailView.as_view(), name="moderation-user-detail"),
]
