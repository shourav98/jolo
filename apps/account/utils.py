from django.db import models
from django.utils import timezone


class SoftDeleteModel(models.Model):
    """Abstract mixin for soft delete functionality."""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete the object."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        """Restore a soft-deleted object."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the object."""
        return super().delete(using=using, keep_parents=keep_parents)


class TwilioService:
    @staticmethod
    def send_otp(phone, otp_code):
        """
        Send OTP code via Twilio SMS.
        """
        from django.conf import settings
        from twilio.rest import Client
        import logging

        logger = logging.getLogger(__name__)

        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        twilio_phone = settings.TWILIO_PHONE_NUMBER

        if not all([account_sid, auth_token, twilio_phone]):
            logger.warning("Twilio credentials not fully configured. OTP will only be logged.")
            logger.info(f"OTP for {phone}: {otp_code}")
            return False

        try:
            client = Client(account_sid, auth_token)
            message = client.messages.create(
                body=f"Your verification code is: {otp_code}. Valid for 5 minutes.",
                from_=twilio_phone,
                to=phone
            )
            logger.info(f"OTP sent to {phone} via Twilio. SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP via Twilio: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
