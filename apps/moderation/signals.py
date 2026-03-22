"""
NOTE: We intentionally do NOT use a post_save signal for Feed moderation.

Reason: The feed POST view uploads images/videos to Cloudinary AFTER the Feed
is saved to the DB. A post_save signal fires immediately after Feed.save(),
at which point no FeedFile records exist yet — so visual moderation would
see zero files and miss all media violations.

Solution: moderation is triggered explicitly from FeedListCreateView.post()
AFTER all Cloudinary uploads and FeedFile records are created.
See: apps/feed/views.py → FeedListCreateView.post()
"""

# signals.py intentionally left empty — see note above.

