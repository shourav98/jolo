from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from apps.feed.models import (
    Feed, FeedVideo, Comment, Like, Unlike,
    Story, StoryItem, Follow, TopFan, Transaction, VideoTip
)
from apps.feed.serializers import (
    FeedSerializer, FeedVideoSerializer, FeedCreateSerializer,
    CommentSerializer, LikeSerializer, UnlikeSerializer,
    StorySerializer, FollowSerializer, TopFanSerializer,
    TransactionSerializer, VideoTipSerializer
)
from apps.account.models import UserProfile
from apps.monetization.models import Wallet
from decimal import Decimal


#  FEED CRUD
class FeedListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        feeds = Feed.objects.all().order_by("-created_at")
        serializer = FeedSerializer(feeds, many=True)
        return Response(serializer.data, status=200)

    def post(self, request):
        serializer = FeedCreateSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            result = serializer.save()
            feed = result["feed"]
            video = result["video"]

            data = {"feed": FeedSerializer(feed).data}
            if video:
                data["video"] = FeedVideoSerializer(video).data

            return Response(data, status=201)
        return Response(serializer.errors, status=400)

    def put(self, request, pk):
        feed = get_object_or_404(Feed, pk=pk)
        if feed.profile.user != request.user:
            return Response({"detail": "Permission denied."}, status=403)

        serializer = FeedSerializer(feed, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        feed = get_object_or_404(Feed, pk=pk)
        if feed.profile.user != request.user:
            return Response({"detail": "Permission denied."}, status=403)
        feed.delete()
        return Response({"detail": "Deleted successfully."}, status=204)


#  COMMENT CRUD
class CommentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        comments = Comment.objects.all().select_related("comment_by__user").order_by("-created_at")
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        target_type = request.data.get("type") or request.query_params.get("type", "feed")
        target_id = request.data.get("id") or request.query_params.get("id")
        content = request.data.get("content")

        if not target_id or not content:
            return Response({"detail": "id and content required."}, status=400)

        model = Feed if target_type == "feed" else FeedVideo
        content_type = ContentType.objects.get_for_model(model)
        target = get_object_or_404(model, pk=target_id)

        comment = Comment.objects.create(
            content_type=content_type,
            object_id=target.id,
            comment_by=profile,
            content=content
        )

        return Response(CommentSerializer(comment).data, status=201)

    def put(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if comment.comment_by.user != request.user:
            return Response({"detail": "Permission denied."}, status=403)
        serializer = CommentSerializer(comment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if comment.comment_by.user != request.user:
            return Response({"detail": "Permission denied."}, status=403)
        comment.delete()
        return Response({"detail": "Comment deleted."}, status=204)


# 👍 LIKE / 👎 UNLIKE
class LikeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        target_type = request.data.get("type") or request.query_params.get("type", "feed")
        target_id = request.data.get("id") or request.query_params.get("id")

        if not target_id:
            return Response({"detail": "Missing id."}, status=400)

        model = Feed if target_type == "feed" else FeedVideo
        content_type = ContentType.objects.get_for_model(model)
        target = get_object_or_404(model, pk=target_id)

        like, created = Like.objects.get_or_create(
            content_type=content_type,
            object_id=target.id,
            liked_by=profile
        )

        if not created:
            like.delete()
            return Response({"detail": "Like removed."}, status=204)

        return Response({"detail": "Liked successfully."}, status=201)


class UnlikeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        target_type = request.data.get("type") or request.query_params.get("type", "feed")
        target_id = request.data.get("id") or request.query_params.get("id")

        if not target_id:
            return Response({"detail": "Missing id."}, status=400)

        model = Feed if target_type == "feed" else FeedVideo
        content_type = ContentType.objects.get_for_model(model)
        target = get_object_or_404(model, pk=target_id)

        unlike, created = Unlike.objects.get_or_create(
            content_type=content_type,
            object_id=target.id,
            unliked_by=profile
        )

        if not created:
            unlike.delete()
            return Response({"detail": "Unlike removed."}, status=204)

        return Response({"detail": "Unliked successfully."}, status=201)


# STORIES
class StoryListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        stories = Story.objects.select_related("profile__user").prefetch_related("items").order_by("-created_at")
        serializer = StorySerializer(stories, many=True)
        return Response(serializer.data)

    def post(self, request):
        profile = get_object_or_404(UserProfile, user=request.user)
        files = request.FILES.getlist('files')  

        if not files:
            return Response({"detail": "No file uploaded."}, status=400)

        story = Story.objects.create(profile=profile)

        for f in files:
            StoryItem.objects.create(story=story, file=f)

        
        story.refresh_from_db()
        serializer = StorySerializer(story)
        return Response(serializer.data, status=201)


    def delete(self, request, pk):
        story = get_object_or_404(Story, pk=pk)
        if story.profile.user != request.user:
            return Response({"detail": "Permission denied."}, status=403)
        story.delete()
        return Response({"detail": "Story deleted."}, status=204)


#  FOLLOW / UNFOLLOW
class FollowListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, user_id):
        follower = get_object_or_404(UserProfile, user=request.user)
        following = get_object_or_404(UserProfile, pk=user_id)

        if follower == following:
            return Response({"detail": "You cannot follow yourself."}, status=400)

        obj, created = Follow.objects.get_or_create(follower=follower, following=following)
        if not created:
            obj.delete()
            return Response({"detail": "Unfollowed successfully."})
        return Response({"detail": "Followed successfully."})


#  TIP / TRANSACTION
class TipTransactionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        sender = get_object_or_404(UserProfile, user=request.user)
        receiver_id = request.data.get("receiver_id")
        amount = Decimal(request.data.get("amount", "0"))

        if amount <= 0:
            return Response({"detail": "Invalid amount."}, status=400)

        receiver = get_object_or_404(UserProfile, pk=receiver_id)
        sender_wallet, _ = Wallet.objects.get_or_create(user=request.user)
        receiver_wallet, _ = Wallet.objects.get_or_create(user=receiver.user)

        if sender_wallet.balance < amount:
            return Response({"detail": "Insufficient balance."}, status=400)

        # Deduct & Add
        sender_wallet.spend(int(amount))
        receiver_wallet.add(int(amount))

        txn = Transaction.objects.create(
            sender=sender,
            receiver=receiver,
            type="tip",
            amount=amount
        )

        return Response(TransactionSerializer(txn).data, status=201)

    def get(self, request):
        txns = Transaction.objects.all().order_by("-created_at")
        serializer = TransactionSerializer(txns, many=True)
        return Response(serializer.data, status=200)


# TOP FANS
class TopFanListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, creator_id):
        creator_profile = get_object_or_404(UserProfile, pk=creator_id)
        fans = TopFan.objects.filter(
            iam=creator_profile, status='active'
        ).select_related('fan_profile__user').order_by('-score', '-last_interacted')[:10]

        serializer = TopFanSerializer(fans, many=True)
        return Response(serializer.data, status=200)
