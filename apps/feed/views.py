from django.shortcuts import get_object_or_404
from django.db import transaction, models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser

from apps.feed.models import (
    Feed, FeedFile, Comment, Like, Follow, Unlock, FeedTip, TopFan, Story, StoryItem
)
from apps.feed.serializers import (
    FeedSerializer, CommentSerializer, TopFanSerializer
)
from apps.account.models import UserProfile
from apps.monetization.services import spend_coins



# FEED CRUD (Create, List, Update, Delete)

class FeedListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        
        user = request.user
        if not user.is_authenticated:
            feeds = Feed.objects.filter(status="public").order_by("-created_at")
        else:
            profile = user.profile
            following_profiles = profile.following.values("following")
            feeds = Feed.objects.filter(
                models.Q(status="public")
                | models.Q(profile=profile)
                | models.Q(status="friends", profile__in=following_profiles)
            ).distinct().order_by("-created_at")

        serializer = FeedSerializer(feeds, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request):
        
        serializer = FeedSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            feed = serializer.save(profile=request.user.profile)
            files = request.FILES.getlist("files")
            for f in files:
                FeedFile.objects.create(feed=feed, file=f)
            return Response(
                FeedSerializer(feed, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FeedDetailView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        serializer = FeedSerializer(feed, context={"request": request})
        return Response(serializer.data)

    def put(self, request, pk):
        feed = get_object_or_404(Feed, id=pk, profile=request.user.profile)
        serializer = FeedSerializer(feed, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        feed = get_object_or_404(Feed, id=pk, profile=request.user.profile)
        feed.delete()
        return Response({"message": "Feed deleted"}, status=status.HTTP_204_NO_CONTENT)



# LIKE / UNLIKE TOGGLE


class LikeToggle(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        profile = request.user.profile
        existing_like = Like.objects.filter(
            content_type__model="feed", object_id=feed.id, liked_by=profile
        )
        if existing_like.exists():
            existing_like.delete()
            feed.total_like = max(feed.total_like - 1, 0)
            feed.save(update_fields=["total_like"])
            return Response({"liked": False})
        Like.objects.create(content_object=feed, liked_by=profile)
        feed.total_like += 1
        feed.save(update_fields=["total_like"])
        return Response({"liked": True})



#  COMMENT CREATE + LIST


class CommentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        comments = Comment.objects.filter(object_id=feed.id).order_by("-created_at")
        serializer = CommentSerializer(comments, many=True, context={"request": request})
        return Response(serializer.data)

    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        serializer = CommentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(content_object=feed, comment_by=request.user.profile)
            feed.total_comment += 1
            feed.save(update_fields=["total_comment"])
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# COMMENT EDIT & DELETE (only by owner)

class CommentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        
        comment = get_object_or_404(Comment, id=pk, comment_by=request.user.profile)
        new_content = request.data.get("content", "").strip()
        if not new_content:
            return Response({"error": "Content cannot be empty."}, status=400)
        comment.content = new_content
        comment.save(update_fields=["content"])
        return Response({"message": "Comment updated successfully.", "content": comment.content})

    def delete(self, request, pk):
        
        comment = get_object_or_404(Comment, id=pk, comment_by=request.user.profile)
        feed = comment.content_object
        comment.delete()
        # safely reduce count
        if hasattr(feed, "total_comment") and feed.total_comment > 0:
            feed.total_comment -= 1
            feed.save(update_fields=["total_comment"])
        return Response({"message": "Comment deleted successfully."}, status=status.HTTP_204_NO_CONTENT)




#  UNLOCK LOCKED FEED (Spend Coins)


class UnlockFeed(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        fan = request.user
        if feed.status != "locked":
            return Response({"detail": "Feed is already public"}, status=400)

        if feed.is_unlocked_for(fan):
            return Response({"detail": "Already unlocked"}, status=400)

        try:
            spend_coins(fan, feed.profile.user, service="locked", coins=feed.unlock_price)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        Unlock.objects.create(feed=feed, fan=fan.profile)
        feed.total_view += 1
        feed.save(update_fields=["total_view"])
        return Response({"message": "Feed unlocked successfully"})



# FOLLOW / UNFOLLOW TOGGLE


class FollowToggle(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, creator_id):
        fan = request.user.profile
        creator = get_object_or_404(UserProfile, id=creator_id)
        if fan == creator:
            return Response({"error": "You cannot follow yourself."}, status=400)

        relation, created = Follow.objects.get_or_create(follower=fan, following=creator)
        if not created:
            relation.delete()
            return Response({"following": False})
        return Response({"following": True})



#  TIP CREATOR (Spend Coins)


class TipCreatorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, creator_id):
        fan = request.user
        creator = get_object_or_404(UserProfile, id=creator_id)
        coins = int(request.data.get("coins", 0))
        if coins <= 0:
            return Response({"error": "Invalid amount"}, status=400)

        try:
            spend_coins(fan, creator.user, service="tip", coins=coins)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

        FeedTip.objects.create(sender=fan.profile, receiver=creator, amount=coins)
        return Response({"message": f"Tipped {creator.user.name} with {coins} coins!"})



#  TOP FANS + MY CREATORS


class CreatorTopFansView(APIView):
   
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, creator_id):
        creator = get_object_or_404(UserProfile, id=creator_id)
        fans = TopFan.objects.filter(creator=creator, status="active").order_by("-score")[:20]
        serializer = TopFanSerializer(fans, many=True, context={"request": request})
        return Response(serializer.data)


class MyTopCreatorsView(APIView):
   
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        fan = request.user.profile
        creators = TopFan.objects.filter(fan=fan, status="active").order_by("-score")
        serializer = TopFanSerializer(creators, many=True, context={"request": request})
        return Response(serializer.data)




class StoryView(APIView):
    """Handle GET, POST, DELETE for stories"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """List active stories of self + following"""
        profile = request.user.profile
        following = profile.following.values_list("following_id", flat=True)
        now = timezone.now()

        stories = Story.objects.filter(
            models.Q(profile=profile) | models.Q(profile__in=following)
        ).order_by("-created_at")

        data = []
        for story in stories:
            items = story.items.filter(is_active=True, expired_at__gt=now)
            if not items.exists():
                continue
            data.append({
                "story_id": story.id,
                "creator": story.profile.user.name,
                "created_at": story.created_at,
                "items": [
                    {
                        "id": i.id,
                        "file": request.build_absolute_uri(i.file.url),
                        "expired_at": i.expired_at,
                        "is_active": not i.is_expired(),
                    }
                    for i in items
                ],
            })
        return Response(data)

    def post(self, request):
        """Upload new story (multiple files allowed)"""
        profile = request.user.profile
        story, _ = Story.objects.get_or_create(profile=profile)
        files = request.FILES.getlist("files")

        if not files:
            return Response({"detail": "No files uploaded."}, status=400)

        for f in files:
            StoryItem.objects.create(
                story=story,
                file=f,
                expired_at=timezone.now() + timedelta(hours=24),
            )
        return Response({"message": "Story uploaded successfully."}, status=201)

    def delete(self, request):
        """Delete your own story (and all items)"""
        profile = request.user.profile
        deleted, _ = Story.objects.filter(profile=profile).delete()
        if deleted:
            return Response({"message": "Story deleted successfully."}, status=204)
        return Response({"detail": "No story found."}, status=404)