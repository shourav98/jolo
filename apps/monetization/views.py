import stripe
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from .models import (
    CreatorMonetization, Wallet, CoinPackage, CoinPurchase, MonetizationStatus,
    PayoutAccount, PayoutRequest, COIN_VALUE_USD, MIN_PAYOUT_USD, SpendEvent
)
from apps.account.models import UserProfile
from .serializers import (
    CoinPackageSerializer, CoinPurchaseSerializer, PayoutAccountSerializer,
    PayoutRequestSerializer, MonetizationStatusSerializer
)
from .services import can_earn

#  Monetization Apply / Status / Approve 

class MonetizationApply(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        monet, created = CreatorMonetization.objects.get_or_create(user=request.user)

        #  stop reapply if pending or active
        if monet.status in (MonetizationStatus.PENDING, MonetizationStatus.ACTIVE):
            return Response(
                {"detail": "Already applied or approved", "status": monet.status},
                status=200,
            )

        #  collect uploaded files
        id_proof = request.FILES.get("id_proof")
        intro_video = request.FILES.get("intro_video")
        profile_photo = request.FILES.get("profile_photo")

        # check required uploads
        if not id_proof or not intro_video:
            return Response({"detail": "ID proof and intro video are required"}, status=400)

        # require profile photo if missing
        profile = request.user.profile
        if not profile.profile_photo and not profile_photo:
            return Response({"detail": "Profile photo required if not already set"}, status=400)

        if profile_photo:
            profile.profile_photo = profile_photo

        # store new files in profile
        profile.id_proof = id_proof
        profile.intro_video = intro_video
        profile.save(update_fields=["profile_photo", "id_proof", "intro_video"])

        # check bank info fields (must come with apply)
        bank_name = request.data.get("bank_name")
        account_holder_name = request.data.get("account_holder_name")
        account_number = request.data.get("account_number")

        if not all([bank_name, account_holder_name, account_number]):
            return Response({"detail": "Bank account details are required"}, status=400)

        # create/update bank account
        PayoutAccount.objects.update_or_create(
            user=request.user,
            defaults={
                "bank_name": bank_name,
                "account_holder_name": account_holder_name,
                "account_number": account_number,
                "is_default": True,
            },
        )

        # set monetization status
        monet.status = MonetizationStatus.PENDING
        monet.applied_at = timezone.now()
        monet.save(update_fields=["status", "applied_at"])

        return Response(
            {"detail": "Application submitted successfully", "status": monet.status},
            status=201,
        )
class MonetizationStatusView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        monet, _ = CreatorMonetization.objects.get_or_create(user=request.user)
        data = MonetizationStatusSerializer(monet).data
        data["tier"] = getattr(getattr(request.user, "creator_profile", None), "tier", None)
        return Response(data)

class MonetizationApproveView(APIView):
    permission_classes = [IsAdminUser]
    def post(self, request, user_id):
        from apps.account.models import CustomUser
        from .models import CreatorProfile
        user = CustomUser.objects.get(id=user_id)
        monet = user.monetization
        monet.status = MonetizationStatus.ACTIVE
        monet.approved_at = timezone.now()
        monet.reviewed_by = request.user
        monet.save(update_fields=["status","approved_at","reviewed_by"])
        CreatorProfile.objects.get_or_create(user=user)
        user.profile.is_creator = True
        user.profile.save(update_fields=["is_creator"])
        return Response({"message": f"{user.name} approved as Creator."})

# Vault (User) 

class VaultView(APIView):
    
    permission_classes = [IsAuthenticated]
    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        # purchases
        purchases = CoinPurchase.objects.filter(user=request.user).order_by("-created_at")[:30]
        # Quick stats = how much user spent by category (last 30d)
        since = timezone.now() - timezone.timedelta(days=30)
        spent = (SpendEvent.objects
                 .filter(fan=request.user, created_at__gte=since)
                 .values("service").annotate(total=Sum("coins_spent")))
        return Response({
            "wallet_name": "The Vault",
            "token_name": "Whysper Coins",
            "balance": wallet.balance,
            "balance_usd": f"{Decimal(wallet.balance)*COIN_VALUE_USD:.2f}",
            "quick_stats": {x["service"]: x["total"] for x in spent},
            "history": CoinPurchaseSerializer(purchases, many=True).data
        })

class PackageList(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        packs = CoinPackage.objects.all().order_by("coins")
        return Response(CoinPackageSerializer(packs, many=True).data)

#  Stripe purchase 

class CreateStripeCheckout(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        pack_id = request.data.get("package_id")
        if not pack_id: return Response({"detail":"package_id required"}, status=400)
        pkg = CoinPackage.objects.get(id=pack_id)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"{pkg.name} — {pkg.coins} Whysper Coins"},
                    "unit_amount": int(pkg.price_usd * 100),
                },
                "quantity": 1,
            }],
            metadata={"user_id": request.user.id, "package_id": pkg.id},
            success_url=settings.STRIPE_SUCCESS_URL,
            cancel_url=settings.STRIPE_CANCEL_URL,
        )
        return Response({"url": session.url})

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        data = event["data"]["object"]
        from apps.account.models import CustomUser
        user = CustomUser.objects.get(id=data["metadata"]["user_id"])
        pkg = CoinPackage.objects.get(id=data["metadata"]["package_id"])

        # idempotent coin credit (txn_id unique)
        CoinPurchase.objects.get_or_create(
            txn_id=data["id"],
            defaults={
                "user": user, "package": pkg, "coins_added": pkg.coins,
                "amount_usd": pkg.price_usd, "method": "stripe",
            }
        )
        user.wallet.add(pkg.coins)
    return HttpResponse(status=200)

#  Creator Vault + Payout

class CreatorVault(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not can_earn(request.user):
            return Response({"error":"Not monetized yet"}, status=403)
        qs = SpendEvent.objects.filter(creator=request.user)
        coins_total = qs.aggregate(t=Sum("coins_spent"))["t"] or 0
        usd_total = (Decimal(coins_total) * COIN_VALUE_USD)
        by_service = {r["service"]: r["coins"] for r in qs.values("service").annotate(coins=Sum("coins_spent"))}
        # simple weekly trend
        week_since = timezone.now() - timezone.timedelta(days=7)
        last_week = (qs.filter(created_at__gte=week_since)
                       .extra(select={"d":"date(created_at)"})
                       .values("d").annotate(usd=Sum("usd_creator")).order_by("d"))
        trend = [{"day": r["d"], "usd": str(r["usd"])} for r in last_week]
        return Response({
            "total_coins": coins_total,
            "usd_value": f"{usd_total:.2f}",
            "category": by_service,
            "weekly_trend": trend
        })

class PayoutEligibility(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        if not can_earn(request.user):
            return Response({"can_request": False, "reason":"Not monetized"})
        usd = Decimal(request.user.wallet.balance) * COIN_VALUE_USD
        return Response({
            "balance_coins": request.user.wallet.balance,
            "balance_usd": f"{usd:.2f}",
            "threshold_usd": f"{MIN_PAYOUT_USD:.2f}",
            "can_request": usd >= MIN_PAYOUT_USD
        })

class RequestPayout(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not can_earn(request.user):
            return Response({"detail":"Not monetized"}, status=403)
        account_id = request.data.get("account_id")
        if not account_id:
            return Response({"detail":"account_id required"}, status=400)
        try:
            account = PayoutAccount.objects.get(id=account_id, user=request.user)
        except PayoutAccount.DoesNotExist:
            return Response({"detail":"Invalid account"}, status=404)
        usd = Decimal(request.user.wallet.balance) * COIN_VALUE_USD
        if usd < MIN_PAYOUT_USD:
            return Response({"detail":"Minimum $50 required"}, status=400)
        req = PayoutRequest.objects.create(user=request.user, amount_usd=usd, account=account)
        # zero out coins (hold) – or move to a 'pending' ledger if you prefer
        request.user.wallet.balance = 0
        request.user.wallet.save(update_fields=["balance"])
        return Response(PayoutRequestSerializer(req).data)

#  Payout Accounts CRUD 

class PayoutAccountListCreate(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(PayoutAccountSerializer(request.user.payout_accounts.all(), many=True).data)
    def post(self, request):
        ser = PayoutAccountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        acc = ser.save(user=request.user)
        if acc.is_default:
            request.user.payout_accounts.exclude(id=acc.id).update(is_default=False)
        return Response(PayoutAccountSerializer(acc).data)

class PayoutAccountSetDefault(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request, account_id):
        acc = PayoutAccount.objects.get(id=account_id, user=request.user)
        request.user.payout_accounts.update(is_default=False)
        acc.is_default = True; acc.save(update_fields=["is_default"])
        return Response({"ok": True})


