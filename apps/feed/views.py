from django.shortcuts import get_object_or_404
from django.db import transaction, models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import timedelta
from django.utils import timezone
from apps.monetization.models import CreatorTier


from apps.feed.models import (
    Feed, FeedFile, Comment, Like, Follow, Unlock, FeedTip, TopFan, Story, StoryItem
)
from apps.feed.serializers import (
    FeedSerializer, CommentSerializer, TopFanSerializer
)
from apps.account.models import UserProfile
from apps.monetization.services import spend_coins
import cloudinary



#  Unified Response Helper


def api_response(success=True, message="Success", data=None, status_code=200):
    return Response(
        {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": data if data is not None else []
        },
        status=status_code
    )



# FEED CRUD (Create, List, Update, Delete)


class FeedListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        """List feeds visible to current user."""
        user = request.user
        if not user.is_authenticated:
            feeds = Feed.objects.filter(status="public").order_by("-created_at")
        else:
            profile = user.profile
            following_profiles = profile.following.values("following")
            feeds = Feed.objects.filter(
                models.Q(status="public")
                | models.Q(profile=profile)
                | models.Q(status="followers", profile__in=following_profiles)
            ).distinct().order_by("-created_at")

        serializer = FeedSerializer(feeds, many=True, context={"request": request})
        return api_response(data=serializer.data)

    def post(self, request):
        """Create a new feed post."""
        serializer = FeedSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return api_response(success=False, message="Validation error", data=serializer.errors, status_code=400)

        # Create feed
        feed = serializer.save(profile=request.user.profile)

        # Automatically set unlock_price if it's a locked post
        if feed.status == "locked":
            tier = getattr(request.user.creator_profile, "tier", CreatorTier.SILVER)
            tier_prices = {
                CreatorTier.SILVER: 500,
                CreatorTier.GOLD: 500,
                CreatorTier.PLATINUM: 750,
                CreatorTier.DIAMOND: 1000,
            }
            feed.unlock_price = tier_prices.get(tier, 500)
            feed.save(update_fields=["unlock_price"])

        # ✅ Handle image/video uploads to Cloudinary
        image_files = request.FILES.getlist("image")
        video_files = request.FILES.getlist("video")

        for img in image_files:
            cloudinary_result = cloudinary.uploader.upload_large(
                img,
                resource_type="auto",
                folder="feed/images/",
                chunk_size=6000000  # 6MB chunks for large files
            )
            FeedFile.objects.create(
                feed=feed,
                file=cloudinary_result['public_id'],
                file_public_id=cloudinary_result['public_id'],
                file_type="image"
            )

        for vid in video_files:
            cloudinary_result = cloudinary.uploader.upload_large(
                vid,
                resource_type="auto",
                folder="feed/videos/",
                chunk_size=6000000  # 6MB chunks for large files
            )
            FeedFile.objects.create(
                feed=feed,
                file=cloudinary_result['public_id'],
                file_public_id=cloudinary_result['public_id'],
                file_type="video"
            )

        return api_response(
            message="Feed created successfully.",
            data=FeedSerializer(feed, context={"request": request}).data,
            status_code=201
        )


class FeedDetailView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        serializer = FeedSerializer(feed, context={"request": request})
        return api_response(data=serializer.data)

    def put(self, request, pk):
        feed = get_object_or_404(Feed, id=pk, profile=request.user.profile)
        serializer = FeedSerializer(feed, data=request.data, partial=True, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return api_response(message="Feed updated successfully.", data=serializer.data)
        return api_response(success=False, message="Validation error", data=serializer.errors, status_code=400)

    def delete(self, request, pk):
        feed = get_object_or_404(Feed, id=pk, profile=request.user.profile)
        feed_id = feed.id
        feed.delete()
        return api_response(
            success=True,
            message="Feed deleted successfully.",
            data={"feed_id": feed_id},
            status_code=200  
        )




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
            return api_response(message="Unliked successfully.", data={"liked": False})
        Like.objects.create(content_object=feed, liked_by=profile)
        feed.total_like += 1
        feed.save(update_fields=["total_like"])
        return api_response(message="Liked successfully.", data={"liked": True})



# COMMENT CREATE + LIST

class CommentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        comments = Comment.objects.filter(object_id=feed.id).order_by("-created_at")
        serializer = CommentSerializer(comments, many=True, context={"request": request})
        return api_response(data=serializer.data)

    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        serializer = CommentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(content_object=feed, comment_by=request.user.profile)
            feed.total_comment += 1
            feed.save(update_fields=["total_comment"])
            return api_response(message="Comment added successfully.", data=serializer.data, status_code=201)
        return api_response(success=False, message="Validation error", data=serializer.errors, status_code=400)



# COMMENT EDIT & DELETE


class CommentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, pk):
        comment = get_object_or_404(Comment, id=pk, comment_by=request.user.profile)
        new_content = request.data.get("content", "").strip()
        if not new_content:
            return api_response(success=False, message="Content cannot be empty.", status_code=400)
        comment.content = new_content
        comment.save(update_fields=["content"])
        return api_response(message="Comment updated successfully.", data={"content": comment.content})

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, id=pk, comment_by=request.user.profile)
        feed = comment.content_object
        comment_id = comment.id
        feed_id = feed.id if hasattr(feed, "id") else None

        # Delete comment and update feed stats safely
        comment.delete()
        if hasattr(feed, "total_comment") and feed.total_comment > 0:
            feed.total_comment -= 1
            feed.save(update_fields=["total_comment"])

        return api_response(
            success=True,
            message="Comment deleted successfully.",
            data={"comment_id": comment_id, "feed_id": feed_id},
            status_code=200  
        )



# UNLOCK LOCKED FEED (Spend Coins)


class UnlockFeed(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        fan = request.user
        if feed.status != "locked":
            return api_response(success=False, message="Feed is already public.", status_code=400)
        if feed.is_unlocked_for(fan):
            return api_response(success=False, message="Feed already unlocked.", status_code=400)

        try:
            spend_coins(fan, feed.profile.user, service="locked", coins=feed.unlock_price)
        except Exception as e:
            return api_response(success=False, message=str(e), status_code=400)

        Unlock.objects.create(feed=feed, fan=fan.profile)
        feed.total_view += 1
        feed.save(update_fields=["total_view"])
        return api_response(message="Feed unlocked successfully.")



# FOLLOW / UNFOLLOW TOGGLE


class FollowToggle(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, creator_id):
        fan = request.user.profile
        creator = get_object_or_404(UserProfile, id=creator_id)
        if fan == creator:
            return api_response(success=False, message="You cannot follow yourself.", status_code=400)

        relation, created = Follow.objects.get_or_create(follower=fan, following=creator)
        if not created:
            relation.delete()
            return api_response(message="Unfollowed successfully.", data={"following": False})
        return api_response(message="Followed successfully.", data={"following": True})



# TIP CREATOR (Spend Coins)


class TipCreatorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, creator_id):
        fan = request.user
        creator = get_object_or_404(UserProfile, id=creator_id)
        coins = int(request.data.get("coins", 0))
        if coins <= 0:
            return api_response(success=False, message="Invalid coin amount.", status_code=400)

        try:
            spend_coins(fan, creator.user, service="tip", coins=coins)
        except Exception as e:
            return api_response(success=False, message=str(e), status_code=400)

        FeedTip.objects.create(sender=fan.profile, receiver=creator, amount=coins)
        return api_response(message=f"Tipped {creator.user.name} with {coins} coins!")



# TOP FANS + MY CREATORS


class CreatorTopFansView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, creator_id):
        creator = get_object_or_404(UserProfile, id=creator_id)
        fans = TopFan.objects.filter(creator=creator, status="active").order_by("-score")[:20]
        serializer = TopFanSerializer(fans, many=True, context={"request": request})
        return api_response(data=serializer.data)


class MyTopCreatorsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        fan = request.user.profile
        creators = TopFan.objects.filter(fan=fan, status="active").order_by("-score")
        serializer = TopFanSerializer(creators, many=True, context={"request": request})
        return api_response(data=serializer.data)




class MyTopFanListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        creator = request.user.profile
        fans = TopFan.objects.filter(creator=creator, status="active").order_by("-score")
        serializer = TopFanSerializer(fans, many=True, context={"request": request})
        
        data = {
            "total_fans": fans.count(),
            "fans": serializer.data
        }
        return api_response(
            success=True,
            message="TopFan list fetched successfully.",
            data=data,
            status_code=200
        )



class TopFanDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, fan_id):
        creator = request.user.profile
        try:
            topfan = TopFan.objects.get(creator=creator, fan__id=fan_id)
        except TopFan.DoesNotExist:
            return api_response(success=False, message="Fan not found in your top list.", status_code=404)

        serializer = TopFanSerializer(topfan, context={"request": request})
        return api_response(
            success=True,
            message="TopFan details fetched successfully.",
            data=serializer.data,
            status_code=200
        )


# STORY CRUD (24h Story)

class StoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
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
                        "file": cloudinary.utils.cloudinary_url(i.file, resource_type="image")[0] if i.file else None,
                        "expired_at": i.expired_at,
                        "is_active": not i.is_expired(),
                    }
                    for i in items
                ],
            })
        return api_response(data=data)

    def post(self, request):
        profile = request.user.profile
        story, _ = Story.objects.get_or_create(profile=profile)
        files = request.FILES.getlist("files")

        if not files:
            return api_response(success=False, message="No files uploaded.", status_code=400)

        uploaded_items = []
        for f in files:
            cloudinary_result = cloudinary.uploader.upload_large(
                f,
                resource_type="auto",
                folder="stories/",
                chunk_size=6000000  # 6MB chunks for large files
            )
            story_item = StoryItem.objects.create(
                story=story,
                file=cloudinary_result['public_id'],
                file_public_id=cloudinary_result['public_id'],
                expired_at=timezone.now() + timedelta(hours=24),
            )
            uploaded_items.append({
                "id": story_item.id,
                "file": cloudinary.utils.cloudinary_url(story_item.file, resource_type="image")[0],
                "expired_at": story_item.expired_at,
                "is_active": not story_item.is_expired(),
            })

        return api_response(
            message="Story uploaded successfully.",
            data={
                "story_id": story.id,
                "creator": story.profile.user.name,
                "created_at": story.created_at,
                "items": uploaded_items
            },
            status_code=201
        )

    def delete(self, request):
        profile = request.user.profile
        story = Story.objects.filter(profile=profile).first()

        if not story:
            return api_response(
                success=False,
                message="No story found for this user.",
                status_code=404
            )

        story_id = story.id
        story.delete()

        return api_response(
            success=True,
            message="Story deleted successfully.",
            data={"story_id": story_id},
            status_code=200  
        )






class StoryItemDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, story_id):
        profile = request.user.profile

        try:
            # Only delete if the logged-in user owns this story item
            story_item = StoryItem.objects.get(id=story_id, story__profile=profile)
        except StoryItem.DoesNotExist:
            return api_response(
                success=False,
                message="Story item not found or not owned by you.",
                status_code=404,
            )

        deleted_story_id = story_item.story.id
        story_item_id = story_item.id

        story_item.delete()

        # If story has no more items, delete the story itself
        story_deleted = False
        if not StoryItem.objects.filter(story_id=deleted_story_id).exists():
            Story.objects.filter(id=deleted_story_id).delete()
            story_deleted = True

        return api_response(
            success=True,
            message="Story item deleted successfully.",
            data={
                "story_item_id": story_item_id,
                "story_deleted": story_deleted,
                "story_id": deleted_story_id,
            },
            status_code=200,  
        )


