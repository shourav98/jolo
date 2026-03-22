"""
Hive AI moderation service.
Ported from FastAPI implementation and extended for Django integration.
"""

import requests
from django.conf import settings


HIVE_TEXT_URL = "https://api.thehive.ai/api/v3/hive/text-moderation"
HIVE_VISUAL_URL = "https://api.thehive.ai/api/v3/hive/visual-moderation"

# Thresholds
THRESHOLD_FOR_TEXT = 2   # 2 = warning level, 3 = extreme
THRESHOLD_FOR_VISUAL = 0.85  # Confidence score threshold (0.0 to 1.0)

# Hive AI visual tag list that are considered violating (Facebook-style)
BAD_TAGS_FOR_VISUAL_CONTENT = [
    "general_nsfw",
    "yes_sex_toy",
    "yes_female_nudity",
    "yes_male_nudity",
    "yes_sexual_activity",
    "yes_breast",
    "yes_genitals",
    "yes_butt",
    "yes_sexual_intent",
    "yes_undressed",
    "yes_realistic_nsfw",
    "yes_animated_nsfw",  # Adding this one!
    "animated_gun",
    "gun_in_hand",
    "gun_not_in_hand",
    "knife_in_hand",
    "knife_not_in_hand",
    "a_little_bloody",
    "other_blood",
    "very_bloody",
    "yes_fight",
    "yes_pills",
    "illicit_injectables",
    "yes_nazi",
    "yes_kkk",
    "yes_confederate",
    "yes_middle_finger",
    "yes_terrorist",
    "hanging",
    "noose",
    "animated_corpse",
    "human_corpse",
    "yes_self_harm",
    "yes_emaciated_body",
    "animal_genitalia_and_human",
    "animal_genitalia_only",
    "animated_animal_genitalia",
    "yes_animal_abuse",
]

def _get_headers():
    api_key = getattr(settings, "HIVE_API_KEY", "")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def moderate_text(text: str) -> dict:
    """
    Send text to Hive AI text-moderation endpoint.

    Returns:
        {
            "status": "good" | "bad",
            "bad_categories": [...],
            "all_categories": [...]
        }
    """
    if not text or not text.strip():
        return {"status": "good", "bad_categories": [], "all_categories": []}

    payload = {"input": [{"text": text}]}
    try:
        response = requests.post(HIVE_TEXT_URL, json=payload, headers=_get_headers(), timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        # If Hive AI is unreachable, be safe and allow the content
        return {"status": "error", "detail": str(e), "bad_categories": [], "all_categories": []}

    data = response.json()
    classes = data["output"][0]["classes"]

    bad_classes = [cls for cls in classes if cls["value"] >= THRESHOLD_FOR_TEXT]

    return {
        "status": "bad" if bad_classes else "good",
        "bad_categories": bad_classes,
        "all_categories": classes,
    }


def moderate_visual(media_url: str) -> dict:
    """
    Send image or video URL to Hive AI visual-moderation endpoint.

    Returns:
        {
            "status": "good" | "bad",
            "bad_categories": [...],
            "all_categories": [...]
        }
    """
    if not media_url or not media_url.strip():
        return {"status": "good", "bad_categories": [], "all_categories": []}

    payload = {"input": [{"media_url": media_url}]}
    try:
        response = requests.post(HIVE_VISUAL_URL, json=payload, headers=_get_headers(), timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        return {"status": "error", "detail": str(e), "bad_categories": [], "all_categories": []}

    data = response.json()
    classes = data["output"][0]["classes"]

    above_threshold = [cls for cls in classes if cls["value"] >= THRESHOLD_FOR_VISUAL]
    bad_classes = [cls for cls in above_threshold if cls["class"] in BAD_TAGS_FOR_VISUAL_CONTENT]

    return {
        "status": "bad" if bad_classes else "good",
        "bad_categories": bad_classes,
        "all_categories": classes,
    }


def _build_cloudinary_url(public_id: str, resource_type: str = "image") -> str:
    """
    Build a full Cloudinary URL from a public_id.
    FeedFile.file stores the public_id, NOT the full URL.
    """
    import cloudinary.utils
    url, _ = cloudinary.utils.cloudinary_url(public_id, resource_type=resource_type)
    return url


def scan_feed(feed) -> dict:
    """
    Scan a Feed post: check text content AND all attached media files.
    Call this AFTER FeedFiles have been created (i.e. after Cloudinary upload).

    Returns aggregate result:
        {
            "status": "good" | "bad",
            "content_type": "text" | "visual" | "both" | "none",
            "bad_categories": [...],
            "raw_text_result": {...},
            "raw_visual_results": [...]
        }
    """
    all_bad = []
    text_result = {}
    visual_results = []
    flagged_types = []

    # --- Scan text ---
    if feed.content and feed.content.strip():
        text_result = moderate_text(feed.content)
        if text_result.get("status") == "bad":
            all_bad.extend(text_result["bad_categories"])
            flagged_types.append("text")

    # --- Scan all attached media files ---
    # FeedFile.file stores Cloudinary public_id, so we build the full URL first
    from apps.feed.models import FeedFile  # local import to avoid circular
    files = FeedFile.objects.filter(feed=feed)
    for ffile in files:
        public_id = ffile.file  # e.g. "feed/images/rdgk3eo8lixb2aauyfqt"
        if not public_id:
            continue
        # Build proper URL for Hive AI
        resource_type = "video" if ffile.file_type == "video" else "image"
        media_url = _build_cloudinary_url(public_id, resource_type=resource_type)

        visual_result = moderate_visual(media_url)
        visual_results.append(visual_result)
        if visual_result.get("status") == "bad":
            all_bad.extend(visual_result["bad_categories"])
            if "visual" not in flagged_types:
                flagged_types.append("visual")

    # Determine combined content_type label
    if "text" in flagged_types and "visual" in flagged_types:
        content_type = "both"
    elif "text" in flagged_types:
        content_type = "text"
    elif "visual" in flagged_types:
        content_type = "visual"
    else:
        content_type = "none"

    return {
        "status": "bad" if all_bad else "good",
        "content_type": content_type,
        "bad_categories": all_bad,
        "raw_text_result": text_result,
        "raw_visual_results": visual_results,
    }


def moderate_feed_after_upload(feed) -> dict:
    """
    Entry point called by the Feed POST view AFTER all files are uploaded.
    Runs scan and applies action (remove post, update user strikes).
    Returns dict with 'action_taken' and 'violation' flag.
    """
    import logging
    from django.utils import timezone
    from datetime import timedelta
    from apps.moderation.models import ContentViolationLog, UserModerationProfile

    logger = logging.getLogger(__name__)

    try:
        result = scan_feed(feed)
    except Exception as e:
        logger.error(f"[Moderation] Error scanning feed #{feed.id}: {e}")
        return {"violated": False, "action_taken": "error", "error": str(e)}

    logger.info(
        f"[Moderation] Feed #{feed.id} scan result: {result['status']} | "
        f"content_type={result['content_type']} | bad={result['bad_categories']}"
    )

    if result["status"] != "bad":
        return {"violated": False, "action_taken": "none"}

    # ─── Content is VIOLATING ───
    user = feed.profile.user

    mod_profile, _ = UserModerationProfile.objects.get_or_create(user=user)
    mod_profile.violation_count += 1
    mod_profile.last_violation_at = timezone.now()

    count = mod_profile.violation_count
    if count == 1:
        action = "warned"
        mod_profile.restriction_level = "warned"
    elif count == 2:
        action = "restricted"
        mod_profile.restriction_level = "restricted"
        mod_profile.restricted_until = timezone.now() + timedelta(days=7)
    else:
        action = "banned"
        mod_profile.restriction_level = "banned"
        user.is_active = False
        user.save(update_fields=["is_active"])

    mod_profile.save()

    # Create violation log before deleting the feed
    ContentViolationLog.objects.create(
        feed=feed,
        user=user,
        content_type=result["content_type"],
        violation_categories=result["bad_categories"],
        action_taken=action,
        ai_raw_response={
            "text": result.get("raw_text_result", {}),
            "visual": result.get("raw_visual_results", []),
        },
    )

    logger.warning(
        f"[Moderation] Feed #{feed.id} REMOVED. Action: {action}. "
        f"User #{user.id} total violations: {count}."
    )

    # Delete the violating post
    feed.delete()

    return {
        "violated": True,
        "action_taken": action,
        "violation_count": count,
        "bad_categories": result["bad_categories"],
    }
