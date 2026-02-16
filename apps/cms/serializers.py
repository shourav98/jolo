from rest_framework import serializers
from .models import InfoSection, DataDeletionRequest

class InfoSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InfoSection
        fields = ['id', 'page', 'title', 'content', 'order']

class DataDeletionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataDeletionRequest
        fields = ['id', 'user',  'reason', 'status', 'created_at']
        read_only_fields = ['id', 'user', 'status', 'created_at']

    def create(self, validated_data):
        # The user will be associated in the view
        return super().create(validated_data)
