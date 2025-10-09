from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from .models import Feed, FeedVideo, Comment, Like, Unlike

# Helper Function 
def update_object_count(instance, field_name, increment=True):
    """Generic function to increment/decrement count fields."""
    model_class = instance.content_type.model_class()
    try:
        obj = model_class.objects.get(id=instance.object_id)
        value = getattr(obj, field_name, 0)
        if increment:
            setattr(obj, field_name, value + 1)
        else:
            setattr(obj, field_name, max(value - 1, 0))
        obj.save(update_fields=[field_name])
    except model_class.DoesNotExist:
        pass


#  COMMENT SIGNALS 
@receiver(post_save, sender=Comment)
def increase_comment_count(sender, instance, created, **kwargs):
    if created:
        update_object_count(instance, 'total_comment', increment=True)


@receiver(post_delete, sender=Comment)
def decrease_comment_count(sender, instance, **kwargs):
    update_object_count(instance, 'total_comment', increment=False)


#  LIKE SIGNALS 
@receiver(post_save, sender=Like)
def increase_like_count(sender, instance, created, **kwargs):
    if created:
        update_object_count(instance, 'total_like', increment=True)


@receiver(post_delete, sender=Like)
def decrease_like_count(sender, instance, **kwargs):
    update_object_count(instance, 'total_like', increment=False)


#  UNLIKE SIGNALS 
@receiver(post_save, sender=Unlike)
def increase_unlike_count(sender, instance, created, **kwargs):
    if created:
        update_object_count(instance, 'total_unlike', increment=True)


@receiver(post_delete, sender=Unlike)
def decrease_unlike_count(sender, instance, **kwargs):
    update_object_count(instance, 'total_unlike', increment=False)
