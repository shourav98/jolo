from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import CreatorMonetization, Wallet, CoinPackage, CoinPurchase, MonetizationStatus

class MonetizationApply(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        monet, _ = CreatorMonetization.objects.get_or_create(user=request.user)
        if monet.status == MonetizationStatus.ACTIVE:
            return Response({"detail": "Already approved", "status": monet.status})
        monet.status = MonetizationStatus.PENDING
        monet.applied_at = timezone.now()
        monet.save(update_fields=["status", "applied_at"])
        return Response({"detail": "Application submitted", "status": monet.status})

class MonetizationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        monet, _ = CreatorMonetization.objects.get_or_create(user=request.user)
        tier = getattr(getattr(request.user, "creator_profile", None), "tier", None)
        return Response({
            "status": monet.status,
            "applied_at": monet.applied_at,
            "approved_at": monet.approved_at,
            "tier": tier,
        })

class VaultView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        qs = CoinPurchase.objects.filter(user=request.user).order_by("-created_at")[:30]
        return Response({
            "wallet_name": "The Vault",
            "token_name": "Whysper Coins",
            "balance": wallet.balance,
            "history": [
                {"coins": p.coins_added, "amount": str(p.amount_usd), "method": p.method, "at": p.created_at}
                for p in qs
            ]
        })

class PackageList(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        packs = CoinPackage.objects.all().order_by("coins")
        return Response([{
            "id": p.id, "name": p.name, "coins": p.coins, "price_usd": str(p.price_usd)
        } for p in packs])

class MockAddCoins(APIView):
    """Payment gateway integrate না হওয়া পর্যন্ত প্রাথমিক টেস্টের জন্য।"""
    permission_classes = [IsAuthenticated]
    def post(self, request):
        pack_id = request.data.get("package_id")
        method = request.data.get("method", "card")
        pack = CoinPackage.objects.get(id=pack_id)

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        wallet.add(pack.coins)

        CoinPurchase.objects.create(
            user=request.user, package=pack, coins_added=pack.coins,
            amount_usd=pack.price_usd, method=method,
            txn_id=f"MOCK-{request.user.id}-{timezone.now().timestamp()}",
        )
        return Response({"message": "Coins added", "new_balance": wallet.balance})
