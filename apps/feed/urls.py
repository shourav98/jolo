from django.urls import path
from .views import (
    FeedListCreateAPIView, FeedDetailAPIView,
    CommentListCreateAPIView, ToggleLikeAPIView, ToggleUnlikeAPIView,
    FeedVideoListCreateAPIView, FeedVideoDetailAPIView, IncrementVideoViewAPIView,
    StoryListCreateAPIView,
    TopFanListCreateAPIView, TipTransactionAPIView,
    CreatorProfileDetailAPIView
)

urlpatterns = [
    # Feeds
    path('feeds/', FeedListCreateAPIView.as_view(), name='feed-list-create'),
    path('feeds/<int:feed_id>/', FeedDetailAPIView.as_view(), name='feed-detail'),

    # Comments (generic for feed/video)
    path('comments/<str:content_type_name>/<int:object_id>/', CommentListCreateAPIView.as_view(), name='comments'),

    # Like / Unlike
    path('like/<str:content_type_name>/<int:object_id>/', ToggleLikeAPIView.as_view(), name='like'),
    path('unlike/<str:content_type_name>/<int:object_id>/', ToggleUnlikeAPIView.as_view(), name='unlike'),

    # Videos
    path('videos/', FeedVideoListCreateAPIView.as_view(), name='video-list-create'),
    path('videos/<int:video_id>/', FeedVideoDetailAPIView.as_view(), name='video-detail'),
    path('videos/<int:video_id>/view/', IncrementVideoViewAPIView.as_view(), name='video-view'),

    # Stories
    path('stories/', StoryListCreateAPIView.as_view(), name='story-list-create'),

    # TopFan & Tip
    path('topfans/', TopFanListCreateAPIView.as_view(), name='topfan-list-create'),
    path('transactions/tip/', TipTransactionAPIView.as_view(), name='tip'),

    # Creator
    path('creator/<int:profile_id>/', CreatorProfileDetailAPIView.as_view(), name='creator-detail'),
]
