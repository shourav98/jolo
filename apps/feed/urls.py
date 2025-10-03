from django.urls import path
from .views import FeedCreateView, CommentListView

urlpatterns = [
   path('feed/', FeedCreateView.as_view(), name='feed-list'),
    path('feed/<int:feed_id>/comments/', CommentListView.as_view(), name='feed-comments'),
]