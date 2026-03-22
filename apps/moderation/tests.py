# Content Moderation System Manual
# This document provides a comprehensive guide on how the Content Moderation System works, how it automatically handles violations, and how administrators can manage user restrictions, appeals, and settings.

# 1. How the Automated System Works
# The moderation system integrates with Hive AI to automatically scan every new Feed post (including text and attached images/videos) in the background. It is designed to mimic Facebook's approach: Detect -> Remove -> Penalize.

# The Flow
# User Creates a Post: A user uploads a Feed post via the API.
# Background Scan: The text and any Cloudinary image/video URLs are sent to Hive AI.
# Threshold Check:
# Text: If the AI confidence score is >= 2 (Warning/Extreme level).
# Visual: If the AI confidence score is >= 0.85 (85%) AND matches our predefined BAD_TAGS.
# Action Taken: If flagged as violating:
# The post is immediately and permanently deleted.
# A Content Violation Log is generated.
# The user receives a strike, and their restriction level escalates.
# Escalating Penalties (Strikes)
# When a user violates the rules, the system keeps track of their violation count in their 
# UserModerationProfile
# . The penalties escalate automatically:

# 1st Violation (Warning):
# The violating post is removed.
# The user's status becomes warned.
# 2nd Violation (Restriction):
# The violating post is removed.
# The user's status becomes 
# restricted
# .
# They receive a temporary 7-day ban from posting.
# 3rd Violation (Permanent Ban):
# The violating post is removed.
# The user's status becomes banned.
# The user's account is automatically deactivated (is_active = False), meaning they can no longer log into the app.
# 2. Configuring AI Rules & Thresholds
# If you find the AI is being too strict or too lenient, a developer can adjust the settings in 
# apps/moderation/services.py
# .

# THRESHOLD_FOR_TEXT (Default: 2)
# Hive AI uses integers (1-3) for text severity. 2 catches warnings and severe hate/violence.
# THRESHOLD_FOR_VISUAL (Default: 0.85)
# Hive AI returns visual confidence from 0.0 to 1.0. 0.85 means the AI must be 85% sure the image contains a bad visual element.
# BAD_TAGS_FOR_VISUAL_CONTENT
# This is a list in 
# services.py
#  containing tags like "yes_female_nudity", "animated_corpse", and "yes_animated_nsfw". To block a new type of content, add the specific Hive AI tag exactly as spelled to this list.
# 3. Administrator Guide (Django Admin)
# As an administrator, you manage the entire moderation system from the Django Admin Panel (http://127.0.0.1:8000/admin/).

# A. Viewing Violation Logs
# Go to Content Moderation > Content Violation Logs. This is your master audit trail. Every time the AI flags a post, a record is added here.

# What you can see:
# The User who posted it.
# The Content Type (
# text
# , 
# visual
# , or both).
# The exact bad tags the AI detected (e.g., ['violence', 'child_safety']).
# The automated action taken (warned, 
# restricted
# , or banned).
# The exact raw JSON output from the AI (useful if you need to debug why something was flagged).
# B. Handling User Appeals
# Sometimes users will appeal an automated decision if they think the AI made a mistake.

# In the Content Violation Logs list, find the disputed log.
# If the user sent an appeal message, you will see it in the Appeal message field.
# Review the AI's raw output.
# Set the Appeal Status:
# approved: Means the AI was wrong. (Note: You currently must manually restore strikes if you approve an appeal. The system does not auto-recover deleted posts).
# rejected: Means the AI was right, and the strike remains.
# Save the log.
# Pro-Tip: You can manually approve/reject multiple appeals at once by selecting the checkboxes next to the logs and using the "Action" dropdown at the top of the list.

# C. Managing User Profiles & Restrictions
# Go to Content Moderation > User Moderation Profiles. This screen allows you to view and manually edit the strike count and restriction level of any user.

# Resetting Strikes: If a user has reformed, you can open their profile and change their Violation count back to 0, and set their Restriction level to none.
# Manual Bans: If a user is causing trouble but dodging the AI, you can manually open their profile, set them to banned, and then go to their 
# CustomUser
#  account and uncheck Active.
# Bulk Actions: From the list view, select multiple users and use the top dropdown actions to quickly "Reset strikes to zero", "Manually ban selected users", or "Unban selected users".
# 4. Testing & Maintenance
# Manually Testing the AI Connection
# If you suspect the Hive API is down or the API key is expired, you can run a live test directly from your server terminal:

# bash
# python manage.py test_hive_api
# This script will send sample clean text, sample bad text, and a sample NSFW image url to Hive AI, and print the raw JSON responses to the terminal. If it succeeds, your Moderation System is fully online.

# Future Improvements
# Right now, the system permanently deletes offending posts. If you want admins to have the ability to restore a post after an appeal, the system would need to be updated to implement "Soft Deletion" (marking is_deleted=True instead of completely removing it from the database).






# Here is how the Appeal System works currently, and how you manage it:

# 1. How Admins Process Appeals (The Admin Side)
# When an admin needs to review a disputed moderation decision, they have two ways to do it:

# Option A: Using the Django Admin Panel (Easiest)

# Go to http://127.0.0.1:8000/admin/moderation/contentviolationlog/
# Open the specific violation log you want to review.
# Scroll down to the Appeal System section.
# Change the Appeal status from Pending (or None) to approved or rejected.
# Save the log.
# What happens under the hood when you click approved: The system automatically forgives the strike on the user's 

# UserModerationProfile
# . So if the user had 1 strike, it goes back to 0. If the user was permanently banned, it reactivates their account automatically!
# (Note: The post itself is not restored, because the original system instantly deletes offending files to save space on Cloudinary).
# Option B: Using the Admin REST API If you launch an admin dashboard app, you can hit this endpoint as an admin: PATCH /api/moderate/logs/<id>/appeal/ (Requires Admin Token)

# Body:

# json
# {
#     "decision": "approved",  // or "rejected"
#     "admin_notes": "Reviewed manually, AI made a mistake."
# }
# 2. How Users Submit Appeals (The User Side)
# Currently, the system is fully featured for the Admin resolution of appeals, but we haven't exposed a public API endpoint for an ordinary user to natively "submit" an appeal from their mobile app/frontend yet.

# Right now, the assumption is that users would contact your platform's customer support email (with their username), and the admin would manually look up their logs in the Django Admin panel.

# Would you like me to build a new public API endpoint so users can click an "Appeal" button inside your frontend app and submit an appeal directly into the system?