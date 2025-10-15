from django.urls import path
from apps.feed import views


urlpatterns = [
    #  POST CRUD
    path('posts/', views.FeedListCreateView.as_view(), name='feed-list-create'),
    path('posts/<int:pk>/', views.FeedListCreateView.as_view(), name='feed-detail'),

    # COMMENTS CRUD
    path('comments/', views.CommentListCreateView.as_view(), name='comment-list-create'),
    path('comments/<int:pk>/', views.CommentListCreateView.as_view(), name='comment-detail'),

    # 👍 LIKE / 👎 UNLIKE
    path('likes/', views.LikeListCreateView.as_view(), name='like-list-create'),
    path('unlikes/', views.UnlikeListCreateView.as_view(), name='unlike-list-create'),

    # STORIES
    path('stories/', views.StoryListCreateView.as_view(), name='story-list-create'),
    path('stories/<int:pk>/', views.StoryListCreateView.as_view(), name='story-detail'),

    # 👥 FOLLOW / UNFOLLOW
    path('follow/<int:user_id>/', views.FollowListCreateView.as_view(), name='follow-toggle'),

    # TIP / TRANSACTION
    path('transactions/', views.TipTransactionView.as_view(), name='tip-transaction'),

    # TOPFANS (Leaderboard)
    path('topfans/<int:creator_id>/', views.TopFanListView.as_view(), name='topfans-list'),
]
