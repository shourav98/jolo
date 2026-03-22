from django.shortcuts import get_object_or_404
from django.db import transaction, models
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from datetime import timedelta
from django.utils import timezone
from apps.monetization.models import CreatorTier
from django.contrib.contenttypes.models import ContentType
import threading



from apps.feed.models import (
    Feed, FeedFile, Comment, Like, Follow, Unlock, FeedTip, TopFan, Story, StoryItem, ReportedPost, BlockedUser
)
from apps.feed.serializers import (
    FeedSerializer, CommentSerializer, TopFanSerializer
)
from apps.account.models import UserProfile
from apps.monetization.services import spend_coins
import cloudinary
from django.db.models import Q
# from apps.account.serializers import UserSerializer


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
            # Exclude blocked users (both ways)
            blocked_users = BlockedUser.objects.filter(blocker=profile).values_list('blocked', flat=True)
            blocked_by_users = BlockedUser.objects.filter(blocked=profile).values_list('blocker', flat=True)

            feeds = Feed.objects.filter(
                models.Q(status="public")
                | models.Q(status="locked")
                | models.Q(profile=profile)
                | models.Q(status="followers", profile__in=following_profiles)
            ).exclude(
                profile__in=blocked_users
            ).exclude(
                profile__in=blocked_by_users
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

        # ─── 🛡️ AI Content Moderation (Facebook-style) ───
        # Run AFTER all file uploads so visual scan sees the actual media.
        # We run it in a thread to avoid slowing down the API response.
        def run_moderation(feed_id):
            import time
            from apps.feed.models import Feed as FeedModel, FeedFile
            import logging
            
            logger = logging.getLogger(__name__)
            
            # Wait a moment to ensure SQLite has fully committed the FeedFiles from the main thread
            time.sleep(2)
            
            try:
                from apps.moderation.services import moderate_feed_after_upload
                # Re-fetch feed fresh
                feed_obj = FeedModel.objects.filter(id=feed_id).first()
                if feed_obj:
                    # Log to verify we can see the files
                    file_count = FeedFile.objects.filter(feed=feed_obj).count()
                    logger.info(f"[Moderation] Thread starting for Feed #{feed_id}. Found {file_count} FeedFile(s).")
                    
                    moderate_feed_after_upload(feed_obj)
            except Exception as e:
                logger.error(f"[Moderation thread] error: {e}")

        threading.Thread(target=run_moderation, args=(feed.id,), daemon=True).start()
        # ─────────────────────────────────────────────────────

        return api_response(
            message="Feed created successfully.",
            data=FeedSerializer(feed, context={"request": request}).data,
            status_code=201
        )



class FeedDetailView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        
        # Check if user is blocked (both ways)
        if request.user.is_authenticated:
            profile = request.user.profile
            is_blocked = BlockedUser.objects.filter(
                models.Q(blocker=profile, blocked=feed.profile) |
                models.Q(blocker=feed.profile, blocked=profile)
            ).exists()
            
            if is_blocked:
                # Return 404 to hide existence
                return api_response(success=False, message="Feed not found.", status_code=404)

        serializer = FeedSerializer(feed, context={"request": request})
        return api_response(data=serializer.data)

    def put(self, request, pk):
        feed = get_object_or_404(Feed, id=pk, profile=request.user.profile)
        
        # Update feed fields
        serializer = FeedSerializer(feed, data=request.data, partial=True, context={"request": request})
        if not serializer.is_valid():
            return api_response(success=False, message="Validation error", data=serializer.errors, status_code=400)
        
        updated_feed = serializer.save()
        
        # ✅ Handle file updates - ENHANCED VERSION WITH AUTO DETECTION
        self.handle_file_updates_improved(request, feed)
        
        # Automatically update unlock_price if status changed to locked
        if feed.status == "locked" and not feed.unlock_price:
            tier = getattr(request.user.creator_profile, "tier", CreatorTier.SILVER)
            tier_prices = {
                CreatorTier.SILVER: 500,
                CreatorTier.GOLD: 500,
                CreatorTier.PLATINUM: 750,
                CreatorTier.DIAMOND: 1000,
            }
            feed.unlock_price = tier_prices.get(tier, 500)
            feed.save(update_fields=["unlock_price"])
        
        return api_response(
            message="Feed updated successfully.",
            data=FeedSerializer(updated_feed, context={"request": request}).data
        )

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
    
    def handle_file_updates_improved(self, request, feed):
        """
        Simplified file handling - replaces existing files by default
        1. Remove all existing files first
        2. Upload new files with automatic type detection
        3. Supports multiple field names for flexibility
        """
        # SIMPLE APPROACH: Remove all existing files first
        # Delete from Cloudinary first
        for file_obj in feed.files.all():
            if file_obj.file_public_id:
                try:
                    cloudinary.uploader.destroy(file_obj.file_public_id, resource_type=file_obj.file_type)
                except Exception as e:
                    print(f"Error deleting from Cloudinary: {e}")
        # Delete from database
        feed.files.all().delete()
        
        # Try multiple field names for maximum compatibility
        field_names_to_check = [
            "image", "images", "video", "videos", "file", "files", "media"
        ]
        
        all_files = []
        for field_name in field_names_to_check:
            if field_name in request.FILES:
                all_files.extend(request.FILES.getlist(field_name))
        
        # Process all files with automatic type detection
        for uploaded_file in all_files:
            try:
                # Auto-detect file type based on content type and extension
                content_type = uploaded_file.content_type.lower()
                filename = uploaded_file.name.lower()
                
                # Determine file type
                if content_type.startswith('video/') or any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']):
                    file_type = "video"
                    folder = "feed/videos/"
                elif content_type.startswith('image/') or any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                    file_type = "image"
                    folder = "feed/images/"
                else:
                    # Default to image if we can't determine
                    file_type = "image"
                    folder = "feed/images/"
                
                # Upload to Cloudinary
                cloudinary_result = cloudinary.uploader.upload_large(
                    uploaded_file,
                    resource_type="auto",
                    folder=folder,
                    chunk_size=6000000
                )
                
                # Save to database
                FeedFile.objects.create(
                    feed=feed,
                    file=cloudinary_result['public_id'],
                    file_public_id=cloudinary_result['public_id'],
                    file_type=file_type
                )
                
            except Exception as e:
                print(f"Error uploading file {uploaded_file.name}: {e}")
                # Continue with other files even if one fails
    def handle_file_updates_debug(self, request, feed):
        """
        Debug version to see exactly what's happening
        """
        print(f"DEBUG: Request FILES: {dict(request.FILES)}")
        print(f"DEBUG: Request DATA: {dict(request.data)}")
        print(f"DEBUG: Existing files: {list(feed.files.values_list('file', flat=True))}")
        
        # Check what's actually in the request
        image_files = request.FILES.getlist("image")
        video_files = request.FILES.getlist("video")
        
        print(f"DEBUG: Image files count: {len(image_files)}")
        print(f"DEBUG: Video files count: {len(video_files)}")
        
        for i, img in enumerate(image_files):
            print(f"DEBUG: Image {i}: name={img.name}, size={img.size}, content_type={img.content_type}")
        
        for i, vid in enumerate(video_files):
            print(f"DEBUG: Video {i}: name={vid.name}, size={vid.size}, content_type={vid.content_type}")
        
        # Proceed with upload if files exist
        if image_files or video_files:
            print("DEBUG: Proceeding with upload...")
            self.handle_file_updates_improved(request, feed)
        else:
            print("DEBUG: No new files to upload")
                






# LIKE / UNLIKE TOGGLE


class LikeToggle(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        profile = request.user.profile
        content_type = ContentType.objects.get_for_model(Feed)

        like, created = Like.objects.get_or_create(
            content_type=content_type,
            object_id=feed.id,
            liked_by=profile
        )

        if not created:
            # Already liked → unlike
            like.delete()
            # count will auto update via signal
            return api_response(message="Unliked successfully.", data={"liked": False})

        # Newly liked
        return api_response(message="Liked successfully.", data={"liked": True})



# COMMENT CREATE + LIST

class CommentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        comments = Comment.objects.filter(object_id=feed.id).order_by("-created_at")
        
        if request.user.is_authenticated:
            profile = request.user.profile
            blocked_users = BlockedUser.objects.filter(blocker=profile).values_list('blocked', flat=True)
            blocked_by_users = BlockedUser.objects.filter(blocked=profile).values_list('blocker', flat=True)
            comments = comments.exclude(comment_by__in=blocked_users).exclude(comment_by__in=blocked_by_users)

        serializer = CommentSerializer(comments, many=True, context={"request": request})
        return api_response(data=serializer.data)

    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        
        # Check if comments are enabled on this post
        if not feed.comments_enabled:
            return api_response(
                success=False, 
                message="Comments are disabled for this post.", 
                status_code=403
            )
        
        serializer = CommentSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save(content_object=feed, comment_by=request.user.profile)
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
        
        # Check blocking
        if BlockedUser.objects.filter(
            models.Q(blocker=fan.profile, blocked=feed.profile) |
            models.Q(blocker=feed.profile, blocked=fan.profile)
        ).exists():
            return api_response(success=False, message="Feed not found.", status_code=404)

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

        return api_response(
            message="Feed unlocked successfully.",
            data={
                "feed": FeedSerializer(feed, context={"request": request}).data,
                "fan": {
                    "id": fan.id,
                    "remaining_coins": fan.wallet.balance
                }
            }
        )




# FOLLOW / UNFOLLOW TOGGLE


class FollowToggle(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, creator_id):
        fan = request.user.profile
        creator = get_object_or_404(UserProfile, id=creator_id)

        if fan == creator:
            return api_response(success=False, message="You cannot follow yourself.", status_code=400)

        # Check blocking
        if BlockedUser.objects.filter(
            models.Q(blocker=fan, blocked=creator) |
            models.Q(blocker=creator, blocked=fan)
        ).exists():
            return api_response(success=False, message="User not found.", status_code=404)

        # Prevent race-condition duplicates
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
        
        # Check blocking
        if BlockedUser.objects.filter(
            models.Q(blocker=fan.profile, blocked=creator) |
            models.Q(blocker=creator, blocked=fan.profile)
        ).exists():
            return api_response(success=False, message="User not found.", status_code=404)

        coins = int(request.data.get("coins", 0))

        if coins <= 0:
            return api_response(success=False, message="Invalid coin amount.", status_code=400)

        try:
            # spend + split + ledger
            result = spend_coins(fan=fan, creator=creator.user, service="tip", coins=coins)
        except PermissionError as e:
            return api_response(success=False, message=str(e), status_code=403)
        except ValueError as e:
            return api_response(success=False, message=str(e), status_code=400)

        # FeedTip-এ creator-এর real earned coins রাখব
        FeedTip.objects.create(
            sender=fan.profile,
            receiver=creator,
            amount=result["creator_share"]
        )

        return api_response(
            message=f"Tipped {creator.user.name} successfully.",
            data={
                "coins_spent": result["coins_spent"],
                "creator_share": result["creator_share"],
                "platform_share": result["platform_share"],
                "gross_usd": result["gross_usd"],
                "creator_usd": result["creator_usd"],
                "platform_usd": result["platform_usd"],
                "event_id": result["event_id"],
                "is_creator": creator.is_creator,
            },
            status_code=201
        )

# TOP FANS + MY CREATORS


class CreatorTopFansView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request, creator_id):
        creator = get_object_or_404(UserProfile, id=creator_id)
        fans = TopFan.objects.filter(creator=creator, status="active")
        
        if request.user.is_authenticated:
            profile = request.user.profile
            blocked_users = BlockedUser.objects.filter(blocker=profile).values_list('blocked', flat=True)
            blocked_by_users = BlockedUser.objects.filter(blocked=profile).values_list('blocker', flat=True)
            fans = fans.exclude(fan__in=blocked_users).exclude(fan__in=blocked_by_users)

        fans = fans.order_by("-score")[:20]
        serializer = TopFanSerializer(fans, many=True, context={"request": request})
        return api_response(data=serializer.data)


class MyTopCreatorsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        fan = request.user.profile
        creators = TopFan.objects.filter(fan=fan, status="active")
        
        # Exclude blocked users (both ways)
        blocked_users = BlockedUser.objects.filter(blocker=fan).values_list('blocked', flat=True)
        blocked_by_users = BlockedUser.objects.filter(blocked=fan).values_list('blocker', flat=True)
        creators = creators.exclude(creator__in=blocked_users).exclude(creator__in=blocked_by_users)

        creators = creators.order_by("-score")
        serializer = TopFanSerializer(creators, many=True, context={"request": request})
        return api_response(data=serializer.data)




class MyTopFanListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        creator = request.user.profile
        fans = TopFan.objects.filter(creator=creator, status="active")
        
        # Exclude blocked users (both ways)
        blocked_users = BlockedUser.objects.filter(blocker=creator).values_list('blocked', flat=True)
        blocked_by_users = BlockedUser.objects.filter(blocked=creator).values_list('blocker', flat=True)
        fans = fans.exclude(fan__in=blocked_users).exclude(fan__in=blocked_by_users)

        fans = fans.order_by("-score")
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

        # Exclude blocked users from stories
        blocked_users = BlockedUser.objects.filter(blocker=profile).values_list('blocked', flat=True)
        blocked_by_users = BlockedUser.objects.filter(blocked=profile).values_list('blocker', flat=True)

        stories = Story.objects.filter(
            models.Q(profile=profile) | models.Q(profile__in=following)
        ).exclude(
            profile__in=blocked_users
        ).exclude(
            profile__in=blocked_by_users
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
                        "file": cloudinary.utils.cloudinary_url(i.file, resource_type=i.file_type)[0] if i.file else None,
                        "file_type": i.file_type,
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
            # Detect file type based on content type
            content_type = f.content_type.lower()
            if content_type.startswith('video/'):
                file_type = "video"
            elif content_type.startswith('image/'):
                file_type = "image"
            else:
                # Fallback: try to detect from file extension
                filename = f.name.lower()
                if any(filename.endswith(ext) for ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv']):
                    file_type = "video"
                elif any(filename.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                    file_type = "image"
                else:
                    # Default to image if we can't determine
                    file_type = "image"
            
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
                file_type=file_type,
                expired_at=timezone.now() + timedelta(hours=24),
            )
            uploaded_items.append({
                "id": story_item.id,
                "file": cloudinary.utils.cloudinary_url(story_item.file, resource_type=story_item.file_type)[0],
                "file_type": story_item.file_type,
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



class StoryReplyView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_item_id):
        story_item = get_object_or_404(
            StoryItem,
            id=story_item_id,
            is_active=True,
            expired_at__gt=timezone.now()
        )

        content = request.data.get("content", "").strip()
        if not content:
            return api_response(
                success=False,
                message="Reply cannot be empty.",
                status_code=400
            )

        comment = Comment.objects.create(
            content=content,
            content_object=story_item,
            comment_by=request.user.profile
        )

        serializer = CommentSerializer(
            comment,
            context={"request": request}
        )

        return api_response(
            message="Reply sent successfully.",
            data=serializer.data,
            status_code=201
        )
    


class StoryReactionToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, story_item_id):
        story_item = get_object_or_404(StoryItem, id=story_item_id)

        content_type = ContentType.objects.get_for_model(StoryItem)
        profile = request.user.profile

        reaction, created = Like.objects.get_or_create(
            content_type=content_type,
            object_id=story_item.id,
            liked_by=profile
        )

        if not created:
            reaction.delete()
            return api_response(
                message="Reaction removed.",
                data={"reacted": False}
            )

        return api_response(
            message="Reacted to story.",
            data={"reacted": True}
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



# =======================================
# SEARCH API
# =======================================

class SearchAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        limit = int(request.query_params.get("limit", 20))
        offset = int(request.query_params.get("offset", 0))

        if not query:
            return Response({
                "success": False,
                "status_code": 400,
                "message": "Search query required.",
                "data": []
            }, status=400)

        # 🔍 Step 1: Find users whose name matches query
        user_queryset = UserProfile.objects.filter(
            user__name__icontains=query
        )
        
        # Filter blocked users if authenticated
        blocked_ids = []
        if request.user.is_authenticated:
            profile = request.user.profile
            blocked_users = BlockedUser.objects.filter(blocker=profile).values_list('blocked', flat=True)
            blocked_by_users = BlockedUser.objects.filter(blocked=profile).values_list('blocker', flat=True)
            blocked_ids = list(blocked_users) + list(blocked_by_users)
            
            user_queryset = user_queryset.exclude(id__in=blocked_ids)

        matched_profiles = user_queryset.values_list("id", flat=True)

        # 🔍 Step 2: Find feeds related to either content OR those users
        feeds = Feed.objects.filter(
            Q(profile_id__in=matched_profiles) |
            Q(content__icontains=query)
        )
        
        if request.user.is_authenticated:
            feeds = feeds.exclude(profile_id__in=blocked_ids)
            
        feeds = feeds.select_related("profile", "profile__user").prefetch_related("files").order_by("-created_at")[offset:offset + limit]

        serializer = FeedSerializer(feeds, many=True, context={"request": request})

        return Response({
            "success": True,
            "status_code": 200,
            "message": f"Feeds related to '{query}' fetched successfully.",
            "data": serializer.data
        })

# =======================================
# POST MENU ACTIONS
# =======================================

class ToggleCommentsView(APIView):
    """Toggle comments on/off for a post (post owner only)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk, profile=request.user.profile)
        
        # Toggle comments_enabled
        feed.comments_enabled = not feed.comments_enabled
        feed.save(update_fields=["comments_enabled"])
        
        return api_response(
            message=f"Comments {'enabled' if feed.comments_enabled else 'disabled'} successfully.",
            data={
                "feed_id": feed.id,
                "comments_enabled": feed.comments_enabled
            }
        )


class CopyLinkView(APIView):
    """Generate shareable link for a post"""
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        
        # Build absolute URL for the post
        post_url = request.build_absolute_uri(f"/api/feed/{feed.id}/")
        
        return api_response(
            message="Post link generated successfully.",
            data={
                "feed_id": feed.id,
                "link": post_url
            }
        )


class MutePostToggleView(APIView):
    """Mute/unmute a post (viewer action)"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.feed.models import MutedPost
        
        feed = get_object_or_404(Feed, id=pk)
        user_profile = request.user.profile
        
        # Check if already muted
        muted_post = MutedPost.objects.filter(user=user_profile, post=feed).first()
        
        if muted_post:
            # Unmute
            muted_post.delete()
            return api_response(
                message="Post unmuted successfully.",
                data={
                    "feed_id": feed.id,
                    "is_muted": False
                }
            )
        else:
            # Mute
            MutedPost.objects.create(user=user_profile, post=feed)
            return api_response(
                message="Post muted successfully.",
                data={
                    "feed_id": feed.id,
                    "is_muted": True
                }
            )





class BlockUserToggleView(APIView):
    """Block/unblock a user (viewer action)"""
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, user_id):
        from apps.feed.models import BlockedUser
        
        blocker = request.user.profile
        blocked_user = get_object_or_404(UserProfile, id=user_id)
        
        # Prevent self-blocking
        if blocker == blocked_user:
            return api_response(
                success=False,
                message="You cannot block yourself.",
                status_code=400
            )
        
        # Check if already blocked
        block_relation = BlockedUser.objects.filter(
            blocker=blocker, 
            blocked=blocked_user
        ).first()
        
        if block_relation:
            # Unblock
            block_relation.delete()
            return api_response(
                message="User unblocked successfully.",
                data={
                    "user_id": blocked_user.id,
                    "user_name": blocked_user.user.name,
                    "profile_photo": blocked_user.profile_photo,
                    "is_blocked": False
                }
            )
        else:
            # Block user
            BlockedUser.objects.create(blocker=blocker, blocked=blocked_user)
            
            # Also unfollow if currently following
            Follow.objects.filter(
                follower=blocker, 
                following=blocked_user
            ).delete()
            
            return api_response(
                message="User blocked successfully.",
                data={
                    "user_id": blocked_user.id,
                    "user_name": blocked_user.user.name,
                    "profile_photo": blocked_user.profile_photo,
                    "is_blocked": True
                }
            )


class BlockedUsersListView(APIView):
    """Get list of all blocked users for the current user"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.feed.models import BlockedUser
        from apps.feed.serializers import BlockedUserSerializer
        
        blocker = request.user.profile
        
        # Get all users blocked by current user
        blocked_users = BlockedUser.objects.filter(
            blocker=blocker
        ).select_related('blocked', 'blocked__user').order_by('-created_at')
        
        serializer = BlockedUserSerializer(blocked_users, many=True)
        
        return api_response(
            message="Blocked users retrieved successfully.",
            data={
                "total_blocked": blocked_users.count(),
                "blocked_users": serializer.data
            }
        )


# =======================================
# FRIEND SUGGESTION VIEWS
# =======================================

class SuggestedFriendsView(APIView):
    """
    Get ranked friend suggestions based on user behavior.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.feed.suggestion_engine import get_suggested_friends, recalculate_all_scores_for_user
        from apps.feed.serializers import SuggestedFriendSerializer
        from apps.feed.models import UserInteractionScore
        from django.utils import timezone
        from datetime import timedelta
        
        user = request.user.profile
        
        # Check if we need to recalculate scores (e.g., if no scores or last calc was long ago)
        # For now, doing a quick check if user has any scores
        has_scores = UserInteractionScore.objects.filter(user=user).exists()
        
        # If no scores exist, run initial calculation
        if not has_scores:
            recalculate_all_scores_for_user(user)
        
        # Get suggestions
        suggestions = get_suggested_friends(user, limit=20)
        
        # If still no suggestions (new user), force recalculation including trending
        if not suggestions:
            recalculate_all_scores_for_user(user)
            suggestions = get_suggested_friends(user, limit=20)
        
        serializer = SuggestedFriendSerializer(suggestions, many=True, context={'request': request})
        
        return api_response(
            message="Friend suggestions retrieved successfully.",
            data={
                "total_suggestions": len(suggestions),
                "suggestions": serializer.data
            }
        )

# =======================================
# REPORT POST
# =======================================

class ReportPostView(APIView):
    """
    Allow users to report a post with one or multiple reasons.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        feed = get_object_or_404(Feed, id=pk)
        reporter = request.user.profile
        
        reasons = request.data.get("reasons", [])
        description = request.data.get("description", "")
        
        # Validate reasons
        if not reasons:
            return api_response(success=False, message="At least one reason is required.", status_code=400)
        
        # Ensure reasons is a list
        if not isinstance(reasons, list):
            # If it's a string, try to split if comma separated, or just wrap in list
            if isinstance(reasons, str) and ',' in reasons:
                 reasons = [r.strip() for r in reasons.split(',')]
            else:
                 reasons = [reasons]

        # Check if user already reported this post
        existing_report = ReportedPost.objects.filter(
            reporter=reporter, 
            post=feed
        ).exists()
        
        if existing_report:
            return api_response(
                success=False,
                message="You have already reported this post.",
                status_code=400
            )

        # Create report
        report = ReportedPost.objects.create(
            reporter=reporter,
            post=feed,
            reason=reasons,
            description=description,
            status="pending"
        )
        
        # Use serializer for response
        from apps.feed.serializers import ReportedPostSerializer
        serializer = ReportedPostSerializer(report)
        
        return api_response(
            message="Post reported successfully.",
            data=serializer.data,
            status_code=201
        )
