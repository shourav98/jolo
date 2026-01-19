# # core/models.py

# core/models.py
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field
from django.conf import settings

class InfoSection(models.Model):
    # PAGE_CHOICES = (
    #     ('legal', 'Legal'),
    #     ('support', 'Support & Safety'),
    #     ('legal_user', 'Legal User'),
    #     ('support_user', 'Support & Safety User'),
    # )
    PAGE_CHOICES = (
        ('legal',          'Legal'),
        ('support',        'Support & Safety'),
        ('legal_user',     'Legal User'),
        ('support_user',   'Support & Safety User'),
        ('privacy',        'Privacy Policy'),         # ← new
        ('data_usage',     'Data Usage Overview'),    # ← new
        ('deletion_faq', 'Data Deletion FAQ')       # optional
    )

    page = models.CharField(
        max_length=20,
        choices=PAGE_CHOICES
    )

    title = models.CharField(
        max_length=200,
        help_text="Section title (e.g. Terms of Service)", blank=True, null=True
    )

    content = CKEditor5Field(
        config_name='extends',
        help_text="Rich text content"
    )

    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order on the page"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.page.upper()} - {self.title}"



# core/models.py   (append at bottom)
class DataDeletionRequest(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deletion_requests'
    )
    email = models.EmailField(blank=True)               # fallback if not logged in
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Deletion request by {self.user or self.email} - {self.status}"
