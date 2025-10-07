from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.db.models import F
from django.db import transaction as db_transaction
from .models import (
    UserProfile, Feed, FeedFile, FeedVideo,
    Comment, Like, Unlike, Story, StoryItem,
    CreatorProfile, TopFan, Transaction
)
from .serializers import (
    FeedSerializer, FeedCreateSerializer, FeedVideoSerializer,
    CommentSerializer, SimpleCommentCreateSerializer,
    LikeSerializer, UnlikeSerializer,
    StorySerializer, StoryItemSerializer,
    TopFanSerializer, TransactionSerializer, CreatorProfileSerializer, ProfileSerializer
)


# ---------------- Utilities ----------------
def get_profile_from_request(user):
    # tries to get related Profile; adapt if your relation differs
    profile = getattr(user, 'profile', None)
    if profile:
        return profile
    return UserProfile.objects.get(user=user)


# ---------------- Feeds ----------------
class FeedListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        feeds = Feed.objects.select_related('profile').prefetch_related('files').order_by('-created_at')
        serializer = FeedSerializer(feeds, many=True)
        return Response({'status': 200, 'data': serializer.data})

    def post(self, request):
        serializer = FeedCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            feed = serializer.save()
            return Response({'status': 201, 'data': FeedSerializer(feed).data}, status=status.HTTP_201_CREATED)
        return Response({'status': 400, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class FeedDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, feed_id):
        feed = get_object_or_404(Feed, pk=feed_id)
        serializer = FeedSerializer(feed)
        return Response({'status': 200, 'data': serializer.data})


# ---------------- Feed Comments ----------------
class CommentListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_object_and_ctype(self, content_type_name, object_id):
        model = Feed if content_type_name == 'feed' else FeedVideo
        obj = get_object_or_404(model, pk=object_id)
        ctype = ContentType.objects.get_for_model(model)
        return obj, ctype

    def get(self, request, content_type_name, object_id):
        obj, ctype = self.get_object_and_ctype(content_type_name, object_id)
        comments = Comment.objects.filter(content_type=ctype, object_id=obj.id).select_related('comment_by')
        serializer = CommentSerializer(comments, many=True)
        return Response({'status': 200, 'data': serializer.data})

    def post(self, request, content_type_name, object_id):
        obj, ctype = self.get_object_and_ctype(content_type_name, object_id)
        serializer = SimpleCommentCreateSerializer(data=request.data)
        if serializer.is_valid():
            profile = get_profile_from_request(request.user)
            Comment.objects.create(
                content_type=ctype,
                object_id=obj.id,
                comment_by=profile,
                content=serializer.validated_data['content']
            )
            # increment counter atomically
            model_cls = obj.__class__
            model_cls.objects.filter(pk=obj.pk).update(total_comment=F('total_comment') + 1)
            return Response({'status': 201, 'message': 'Comment added'}, status=status.HTTP_201_CREATED)
        return Response({'status': 400, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# ---------------- Like / Unlike ----------------
class ToggleLikeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, content_type_name, object_id):
        model = Feed if content_type_name == 'feed' else FeedVideo
        obj = get_object_or_404(model, pk=object_id)
        ctype = ContentType.objects.get_for_model(model)
        profile = get_profile_from_request(request.user)

        exists = Like.objects.filter(content_type=ctype, object_id=obj.id, liked_by=profile)
        if exists.exists():
            exists.delete()
            model.objects.filter(pk=obj.pk).update(total_like=F('total_like') - 1)
            return Response({'status': 200, 'liked': False})
        else:
            # remove unlike if present
            Unlike.objects.filter(content_type=ctype, object_id=obj.id, unliked_by=profile).delete()
            Like.objects.create(content_type=ctype, object_id=obj.id, liked_by=profile)
            model.objects.filter(pk=obj.pk).update(total_like=F('total_like') + 1)
            return Response({'status': 201, 'liked': True})


class ToggleUnlikeAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, content_type_name, object_id):
        model = Feed if content_type_name == 'feed' else FeedVideo
        obj = get_object_or_404(model, pk=object_id)
        ctype = ContentType.objects.get_for_model(model)
        profile = get_profile_from_request(request.user)

        exists = Unlike.objects.filter(content_type=ctype, object_id=obj.id, unliked_by=profile)
        if exists.exists():
            exists.delete()
            model.objects.filter(pk=obj.pk).update(total_unlike=F('total_unlike') - 1)
            return Response({'status': 200, 'unliked': False})
        else:
            # remove like if present
            Like.objects.filter(content_type=ctype, object_id=obj.id, liked_by=profile).delete()
            Unlike.objects.create(content_type=ctype, object_id=obj.id, unliked_by=profile)
            model.objects.filter(pk=obj.pk).update(total_unlike=F('total_unlike') + 1)
            return Response({'status': 201, 'unliked': True})


# ---------------- Videos ----------------
class FeedVideoListCreateAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        vids = FeedVideo.objects.select_related('profile').order_by('-created_at')
        serializer = FeedVideoSerializer(vids, many=True)
        return Response({'status': 200, 'data': serializer.data})

    def post(self, request):
        serializer = FeedVideoSerializer(data=request.data)
        if serializer.is_valid():
            profile = get_profile_from_request(request.user)
            serializer.save(profile=profile)
            return Response({'status': 201, 'data': serializer.data}, status=status.HTTP_201_CREATED)
        return Response({'status': 400, 'errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class FeedVideoDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, video_id):
        video = get_object_or_404(FeedVideo, pk=video_id)
        serializer = FeedVideoSerializer(video)
        return Response({'status': 200, 'data': serializer.data})


class IncrementVideoViewAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, video_id):
        video = get_object_or_404(FeedVideo, pk=video_id)
        FeedVideo.objects.filter(pk=video.pk).update(total_view=F('total_view') + 1)
        return Response({'status': 200, 'message': 'view incremented'})


# ---------------- Story APIs ----------------
class StoryListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        stories = Story.objects.select_related('profile').prefetch_related('items').order_by('-created_at')
        serializer = StorySerializer(stories, many=True)
        return Response({'status': 200, 'data': serializer.data})

    def post(self, request):
        profile = get_profile_from_request(request.user)
        story = Story.objects.create(profile=profile)
        # accept single file for story item via key 'file'
        if 'file' in request.FILES:
            expired_at = request.data.get('expired_at')  # expect ISO datetime string
            StoryItem.objects.create(story=story, file=request.FILES['file'], expired_at=expired_at or None)
        return Response({'status': 201, 'message': 'story created'})


# ---------------- TopFan / Transaction (Tip) ----------------
class TopFanListCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile = get_profile_from_request(request.user)
        # show fans of the user (those who are fans of me)
        fans = TopFan.objects.filter(iam=profile)
        serializer = TopFanSerializer(fans, many=True)
        return Response({'status': 200, 'data': serializer.data})

    def post(self, request):
        # to mark someone as top fan: provide 'fan_profile_id'
        profile = get_profile_from_request(request.user)
        fan_id = request.data.get('fan_profile_id')
        fan_profile = get_object_or_404(Profile, pk=fan_id)
        topfan, created = TopFan.objects.get_or_create(iam=profile, fan_profile=fan_profile)
        serializer = TopFanSerializer(topfan)
        return Response({'status': 201 if created else 200, 'data': serializer.data})


class TipTransactionAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        POST payload:
        {
            "to_profile_id": int,
            "amount": "12.50"
        }
        """
        to_profile_id = request.data.get('to_profile_id')
        amount = request.data.get('amount')
        if not to_profile_id or not amount:
            return Response({'status': 400, 'message': 'to_profile_id and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        from_profile = get_profile_from_request(request.user)
        to_profile = get_object_or_404(Profile, pk=to_profile_id)

        # In production: integrate payment gateway here; here we just record tip transaction
        with db_transaction.atomic():
            txn = Transaction.objects.create(profile=to_profile, type='tip', amount=amount)
            # Optionally: increase total_earn on FeedVideo/CreatorProfile etc if needed.

        return Response({'status': 201, 'message': 'Tip recorded', 'data': TransactionSerializer(txn).data}, status=status.HTTP_201_CREATED)


# ---------------- Creator Profile ----------------
class CreatorProfileDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, profile_id):
        profile = get_object_or_404(Profile, pk=profile_id)
        creator = getattr(profile, 'creatorprofile', None)
        if not creator:
            return Response({'status': 404, 'message': 'Not a creator'}, status=status.HTTP_404_NOT_FOUND)
        serializer = CreatorProfileSerializer(creator)
        return Response({'status': 200, 'data': serializer.data})
