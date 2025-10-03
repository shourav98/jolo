from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .models import Feed, FeedVideo, Comment, Story, StoryItem
from .serializers import FeedCreateSerializer, FeedVideoSerializer, CommentSerializer, StorySerializer, StoryItemSerializer

class FeedCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = FeedCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            feed = serializer.save()
            return Response({
                "status": 201,
                "success": True,
                "message": "Feed post created successfully",
                "data": FeedCreateSerializer(feed).data
            }, status=status.HTTP_201_CREATED)
        return Response({
            "status": 400,
            "success": False,
            "errors": serializer.errors,
            "message": "Feed post creation failed"
        }, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        feeds = Feed.objects.all().order_by('-created_at')
        serializer = FeedCreateSerializer(feeds, many=True)
        return Response({
            "status": 200,
            "success": True,
            "message": "Feed posts retrieved successfully",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

class CommentListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, feed_id):
        comments = Comment.objects.filter(content_type_id=feed_id)
        serializer = CommentSerializer(comments, many=True)
        return Response({"status": 200, "success": True, "data": serializer.data})

    def post(self, request, feed_id):
        data = request.data.copy()
        data['content_type_id'] = feed_id
        serializer = CommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"status": 201, "success": True, "data": serializer.data})
        return Response({"status": 400, "success": False, "errors": serializer.errors})