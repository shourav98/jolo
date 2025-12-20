# # core/models.py

# core/models.py
from django.db import models
from django_ckeditor_5.fields import CKEditor5Field

class InfoSection(models.Model):
    PAGE_CHOICES = (
        ('legal', 'Legal'),
        ('support', 'Support & Safety'),
    )

    page = models.CharField(
        max_length=20,
        choices=PAGE_CHOICES
    )

    title = models.CharField(
        max_length=200,
        help_text="Section title (e.g. Terms of Service)"
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



# from django.db import models
# from django_ckeditor_5.fields import CKEditor5Field

# class InfoSection(models.Model):
#     PAGE_CHOICES = (
#         ('legal', 'Legal'),
#         ('support', 'Support & Safety'),
#     )

#     page = models.CharField(max_length=20, choices=PAGE_CHOICES)
#     title = CKEditor5Field(config_name='extends')
#     content = CKEditor5Field(config_name='extends')
#     order = models.PositiveIntegerField(default=0)
#     is_active = models.BooleanField(default=True)

#     class Meta:
#         ordering = ['order']

#     def __str__(self):
#         return f"{self.page} - {self.title}"
