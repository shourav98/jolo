from rest_framework import serializers
from .models import CoinPackage, CoinPurchase, PayoutAccount, PayoutRequest, CreatorMonetization

class CoinPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPackage
        fields = ("id","name","coins","price_usd")

class CoinPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinPurchase
        fields = ("coins_added","amount_usd","method","created_at")

class PayoutAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutAccount
        fields = ("id","bank_name","account_holder_name","account_number","is_default","created_at")

class PayoutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutRequest
        fields = ("id","amount_usd","status","created_at","processed_at","account")

class MonetizationStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatorMonetization
        fields = ("status","applied_at","approved_at")
