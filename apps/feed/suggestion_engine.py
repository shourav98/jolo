"""
Friend Suggestion Scoring Engine
Calculates dynamic scores for friend suggestions based on user behavior
"""

from django.db.models import Count, Q, F
from django.utils import timezone
from datetime import timedelta
from apps.feed.models import (
    ProfileView, UserInteractionScore, Like, Comment, Follow, Feed
)
from apps.account.models import UserProfile
from django.contrib.contenttypes.models import ContentType


# Score weights (configurable)
SCORE_WEIGHTS = {
    'profile_views': 10.0,      # Highest priority
    'likes': 5.0,               # High priority
    'comments': 7.0,            # Very high (more engaged)
    'mutual_follows': 3.0,      # Medium priority
    'session_frequency': 4.0,   # Medium-high priority
    'trending': 1.0,            # Lowest (fallback)
}


def calculate_profile_view_score(viewer, viewed):
    """Calculate score based on profile views"""
    try:
        profile_view = ProfileView.objects.get(viewer=viewer, viewed=viewed)
        view_count = profile_view.view_count
        
        # Base score
        score = view_count * SCORE_WEIGHTS['profile_views']
        
        # Bonus for recent views (within 24 hours)
        if profile_view.last_viewed_at >= timezone.now() - timedelta(hours=24):
            score *= 1.5
        
        return score
    except ProfileView.DoesNotExist:
        return 0.0


def calculate_like_score(user, suggested_user):
    """Calculate score based on likes on suggested user's content"""
    feed_content_type = ContentType.objects.get_for_model(Feed)
    
    # Count likes by user on suggested_user's posts
    like_count = Like.objects.filter(
        liked_by=user,
        content_type=feed_content_type,
        object_id__in=Feed.objects.filter(profile=suggested_user).values_list('id', flat=True)
    ).count()
    
    return like_count * SCORE_WEIGHTS['likes']


def calculate_comment_score(user, suggested_user):
    """Calculate score based on comments on suggested user's content"""
    feed_content_type = ContentType.objects.get_for_model(Feed)
    
    # Count comments by user on suggested_user's posts
    comment_count = Comment.objects.filter(
        comment_by=user,
        content_type=feed_content_type,
        object_id__in=Feed.objects.filter(profile=suggested_user).values_list('id', flat=True)
    ).count()
    
    return comment_count * SCORE_WEIGHTS['comments']


def calculate_mutual_follow_score(user, suggested_user):
    """Calculate score based on mutual followers"""
    # Get user's followers
    user_followers = Follow.objects.filter(following=user).values_list('follower', flat=True)
    
    # Get suggested_user's followers
    suggested_followers = Follow.objects.filter(following=suggested_user).values_list('follower', flat=True)
    
    # Count mutual followers
    mutual_count = len(set(user_followers) & set(suggested_followers))
    
    return mutual_count * SCORE_WEIGHTS['mutual_follows']


def calculate_session_score(viewer, viewed):
    """Calculate score based on browsing session patterns"""
    # Get recent profile views by viewer in same sessions
    recent_views = ProfileView.objects.filter(
        viewer=viewer,
        last_viewed_at__gte=timezone.now() - timedelta(days=7)
    ).exclude(viewed=viewed)
    
    # Count how many times viewed user appeared in same sessions
    session_frequency = 0
    viewer_sessions = recent_views.values_list('session_id', flat=True).distinct()
    
    for session_id in viewer_sessions:
        if session_id and ProfileView.objects.filter(
            viewer=viewer,
            viewed=viewed,
            session_id=session_id
        ).exists():
            session_frequency += 1
    
    return session_frequency * SCORE_WEIGHTS['session_frequency']


def calculate_trending_score(suggested_user):
    """Calculate trending score (fallback)"""
    # Count followers
    follower_count = Follow.objects.filter(following=suggested_user).count()
    
    # Count recent engagement (last 7 days)
    feed_content_type = ContentType.objects.get_for_model(Feed)
    recent_posts = Feed.objects.filter(
        profile=suggested_user,
        created_at__gte=timezone.now() - timedelta(days=7)
    )
    
    recent_engagement = Like.objects.filter(
        content_type=feed_content_type,
        object_id__in=recent_posts.values_list('id', flat=True)
    ).count()
    
    # Calculate trending score
    score = (follower_count * 0.1) + (recent_engagement * 0.5)
    
    return score * SCORE_WEIGHTS['trending']


def generate_suggestion_reason(score_components):
    """Generate human-readable reason for suggestion"""
    # Find the highest scoring component
    max_component = max(score_components.items(), key=lambda x: x[1])
    component_name, component_score = max_component
    
    if component_score == 0:
        return "New user you might like"
    
    reasons = {
        'profile_view_score': "You viewed their profile multiple times",
        'like_score': "You liked their content",
        'comment_score': "You commented on their posts",
        'mutual_follow_score': "You have mutual connections",
        'session_score': "You browse similar content",
        'trending_score': "Popular in your network",
    }
    
    return reasons.get(component_name, "Suggested for you")


def calculate_user_suggestion_score(user, suggested_user):
    """Calculate complete suggestion score for a user pair"""
    
    # Calculate all score components
    profile_view_score = calculate_profile_view_score(user, suggested_user)
    like_score = calculate_like_score(user, suggested_user)
    comment_score = calculate_comment_score(user, suggested_user)
    mutual_follow_score = calculate_mutual_follow_score(user, suggested_user)
    session_score = calculate_session_score(user, suggested_user)
    trending_score = calculate_trending_score(suggested_user)
    
    # Calculate total score
    total_score = (
        profile_view_score +
        like_score +
        comment_score +
        mutual_follow_score +
        session_score +
        trending_score
    )
    
    # Generate reason
    score_components = {
        'profile_view_score': profile_view_score,
        'like_score': like_score,
        'comment_score': comment_score,
        'mutual_follow_score': mutual_follow_score,
        'session_score': session_score,
        'trending_score': trending_score,
    }
    reason = generate_suggestion_reason(score_components)
    
    # Update or create score record
    score_obj, created = UserInteractionScore.objects.update_or_create(
        user=user,
        suggested_user=suggested_user,
        defaults={
            'profile_view_score': profile_view_score,
            'like_score': like_score,
            'comment_score': comment_score,
            'mutual_follow_score': mutual_follow_score,
            'session_score': session_score,
            'trending_score': trending_score,
            'total_score': total_score,
            'reason': reason,
        }
    )
    
    return score_obj


def get_suggested_friends(user, limit=20, exclude_following=True):
    """Get ranked list of suggested friends for a user"""
    from apps.feed.models import BlockedUser
    
    # Get users to exclude
    exclude_ids = [user.id]
    
    # Exclude users already following
    if exclude_following:
        following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
        exclude_ids.extend(following_ids)
    
    # Exclude blocked users (both ways)
    blocked_ids = BlockedUser.objects.filter(
        Q(blocker=user) | Q(blocked=user)
    ).values_list('blocked_id', 'blocker_id')
    
    for blocker_id, blocked_id in blocked_ids:
        exclude_ids.extend([blocker_id, blocked_id])
    
    # Get existing scores
    suggestions = UserInteractionScore.objects.filter(
        user=user
    ).exclude(
        suggested_user_id__in=exclude_ids
    ).select_related(
        'suggested_user',
        'suggested_user__user'
    ).order_by('-total_score')[:limit]
    
    return suggestions


def recalculate_all_scores_for_user(user):
    """Recalculate scores for all potential suggestions for a user"""
    from apps.feed.models import BlockedUser
    
    # Get all potential suggestions (exclude self, following, blocked)
    exclude_ids = [user.id]
    
    following_ids = Follow.objects.filter(follower=user).values_list('following_id', flat=True)
    exclude_ids.extend(following_ids)
    
    blocked_ids = BlockedUser.objects.filter(
        Q(blocker=user) | Q(blocked=user)
    ).values_list('blocked_id', 'blocker_id')
    
    for blocker_id, blocked_id in blocked_ids:
        exclude_ids.extend([blocker_id, blocked_id])
    
    # Get users who have interacted with or been viewed by current user
    potential_suggestions = set()
    
    # Users whose profiles were viewed
    viewed_users = ProfileView.objects.filter(viewer=user).values_list('viewed_id', flat=True)
    potential_suggestions.update(viewed_users)
    
    # Users whose content was liked
    feed_content_type = ContentType.objects.get_for_model(Feed)
    liked_user_posts = Like.objects.filter(
        liked_by=user,
        content_type=feed_content_type
    ).values_list('object_id', flat=True)
    liked_users = Feed.objects.filter(id__in=liked_user_posts).values_list('profile_id', flat=True)
    potential_suggestions.update(liked_users)
    
    # Users whose content was commented on
    commented_user_posts = Comment.objects.filter(
        comment_by=user,
        content_type=feed_content_type
    ).values_list('object_id', flat=True)
    commented_users = Feed.objects.filter(id__in=commented_user_posts).values_list('profile_id', flat=True)
    potential_suggestions.update(commented_users)
    
    # Add trending users if not enough suggestions
    if len(potential_suggestions) < 50:
        trending_users = UserProfile.objects.annotate(
            follower_count=Count('followers')
        ).order_by('-follower_count')[:50].values_list('id', flat=True)
        potential_suggestions.update(trending_users)
    
    # Remove excluded IDs
    potential_suggestions = potential_suggestions - set(exclude_ids)
    
    # Calculate scores for each potential suggestion
    for suggested_user_id in potential_suggestions:
        try:
            suggested_user = UserProfile.objects.get(id=suggested_user_id)
            calculate_user_suggestion_score(user, suggested_user)
        except UserProfile.DoesNotExist:
            continue
    
    return len(potential_suggestions)
