from django.urls import path
from . import views

urlpatterns = [
    path("feed/", views.FeedListCreateView.as_view(), name="feed-list"),
    path("feed/<int:pk>/", views.FeedDetailView.as_view(), name="feed-detail"),
    path("feed/<int:pk>/like/", views.LikeToggle.as_view(), name="feed-like-toggle"),
    path("feed/<int:pk>/comments/", views.CommentListCreateView.as_view(), name="feed-comments"),
    path("comments/<int:pk>/", views.CommentDetailView.as_view(), name="comment-detail"),

    path("feed/<int:pk>/unlock/", views.UnlockFeed.as_view(), name="feed-unlock"),
    path("follow/<int:creator_id>/", views.FollowToggle.as_view(), name="follow-toggle"),
    path("top-fans/<int:creator_id>/", views.CreatorTopFansView.as_view(), name="creator-top-fans"),
    path("my-creators/", views.MyTopCreatorsView.as_view(), name="my-creators"),
    path("tip/<int:creator_id>/", views.TipCreatorView.as_view(), name="tip-creator"),

    path("stories/", views.StoryView.as_view(), name="stories"),

]
