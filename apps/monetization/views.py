import stripe
from decimal import Decimal
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser

from .models import (
    CreatorMonetization, Wallet, CoinPackage, CoinPurchase, MonetizationStatus,
    PayoutAccount, PayoutRequest, COIN_VALUE_USD, MIN_PAYOUT_USD, SpendEvent
)
from .serializers import (
    CoinPackageSerializer, CoinPurchaseSerializer, PayoutAccountSerializer,
    PayoutRequestSerializer, MonetizationStatusSerializer
)
from .services import can_earn
from apps.account.models import CustomUser
from apps.feed.models import TopFan


from rest_framework_simplejwt.authentication import JWTAuthentication


# -----------------------
# Unified API Response
# -----------------------
def api_response(success=True, message="Success", data=None, status_code=200):
    return Response(
        {
            "success": success,
            "status_code": status_code,
            "message": message,
            "data": data if data is not None else []
        },
        status=status_code
    )


# -----------------------
# Monetization
# -----------------------
class MonetizationApply(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        monet, _ = CreatorMonetization.objects.get_or_create(user=user)

        # Prevent duplicate applications
        if monet.status in (MonetizationStatus.PENDING, MonetizationStatus.ACTIVE):
            return api_response(
                success=False,
                message="You have already applied or are already monetized.",
                data={"status": monet.status},
                status_code=400
            )

        # File validation
        id_proof = request.FILES.get("id_proof")
        intro_video = request.FILES.get("intro_video")
        profile_photo = request.FILES.get("profile_photo")

        if not id_proof or not intro_video:
            return api_response(
                success=False,
                message="Both ID proof and Intro video are required.",
                status_code=400
            )

        profile = user.profile
        if not profile.profile_photo and not profile_photo:
            return api_response(
                success=False,
                message="Profile photo required if not already set.",
                status_code=400
            )

        # Save profile photo on profile
        if profile_photo:
            profile.profile_photo = profile_photo
            profile.save(update_fields=["profile_photo"])

        # Save KYC artifacts on monetization model
        monet.id_proof = id_proof
        monet.intro_video = intro_video
        monet.save(update_fields=["id_proof", "intro_video"])

        # Handle payout account
        bank_name = request.data.get("bank_name")
        account_holder_name = request.data.get("account_holder_name")
        account_number = request.data.get("account_number")

        # Try default first, else any existing account
        default_account = (
            PayoutAccount.objects.filter(user=user, is_default=True).first()
            or PayoutAccount.objects.filter(user=user).first()
        )

        # If no account exists at all and no details provided → block
        if not default_account and not all([bank_name, account_holder_name, account_number]):
            return api_response(
                success=False,
                message="Bank account details are required before applying for monetization.",
                status_code=400
            )

        # If details provided and no account yet → create one and make default
        if not default_account and all([bank_name, account_holder_name, account_number]):
            default_account = PayoutAccount.objects.create(
                user=user,
                bank_name=bank_name,
                account_holder_name=account_holder_name,
                account_number=account_number,
                is_default=True,
            )
            PayoutAccount.objects.filter(user=user).exclude(id=default_account.id).update(is_default=False)

        # Mark monetization as pending
        monet.status = MonetizationStatus.PENDING
        monet.applied_at = timezone.now()
        monet.save(update_fields=["status", "applied_at"])

        return api_response(
            success=True,
            message="Monetization application submitted successfully.",
            data={"status": monet.status, "applied_at": monet.applied_at},
            status_code=201
        )


class MonetizationStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        monet, _ = CreatorMonetization.objects.get_or_create(user=request.user)
        data = MonetizationStatusSerializer(monet).data
        data["tier"] = getattr(getattr(request.user, "creator_profile", None), "tier", None)
        return api_response(data=data)


class MonetizationApproveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        from .models import CreatorProfile

        user = CustomUser.objects.get(id=user_id)
        monet, _ = CreatorMonetization.objects.get_or_create(user=user)

        monet.status = MonetizationStatus.ACTIVE
        monet.approved_at = timezone.now()
        monet.reviewed_by = request.user
        monet.save(update_fields=["status", "approved_at", "reviewed_by"])

        CreatorProfile.objects.get_or_create(user=user)
        user.profile.is_creator = True
        user.profile.save(update_fields=["is_creator"])

        return api_response(message=f"{user.name} approved as Creator.")


# -----------------------
# Vault (User/Creator)
# -----------------------
class VaultView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request):
        user = request.user
        wallet, _ = Wallet.objects.get_or_create(user=user)

        # ──────────────── CREATOR VAULT ────────────────
        if hasattr(user, "monetization") and user.monetization.status == MonetizationStatus.ACTIVE:
            qs = SpendEvent.objects.filter(creator=user)
            coins_total = qs.aggregate(total=Sum("coins_spent"))["total"] or 0
            usd_total = Decimal(coins_total) * COIN_VALUE_USD

            # Category breakdown (service → coins)
            category = {
                row["service"]: row["coins"]
                for row in qs.values("service").annotate(coins=Sum("coins_spent"))
            }

            # UI-friendly labels
            category_labels = {
                "chat": "Messages",
                "tip": "Tips",
                "locked": "Unlocks",
                "photo": "Content",
                "video": "Videos",
            }

            # Map to labels & ensure defaults
            category = {category_labels.get(k, k): v for k, v in category.items()}
            for label in category_labels.values():
                category.setdefault(label, 0)

            # ─── Time-based analytics
            now = timezone.now()
            week_since = now - timezone.timedelta(days=7)
            month_since = now - timezone.timedelta(days=30)
            year_since = now - timezone.timedelta(days=365)

            weekly = (
                qs.filter(created_at__gte=week_since)
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(usd=Sum("usd_creator"))
                .order_by("day")
            )

            monthly = (
                qs.filter(created_at__gte=month_since)
                .annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(usd=Sum("usd_creator"))
                .order_by("day")
            )

            yearly = (
                qs.filter(created_at__gte=year_since)
                .annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(usd=Sum("usd_creator"))
                .order_by("month")
            )

            def build_trend(qs_values, field):
                return [{field: str(r[field]), "usd": str(r["usd"])} for r in qs_values]

            quick_trend = {
                "weekly": build_trend(weekly, "day"),
                "monthly": build_trend(monthly, "day"),
                "yearly": build_trend(yearly, "month"),
            }

            # ─── Top services
            def service_percent(days):
                since = now - timezone.timedelta(days=days)
                total = qs.filter(created_at__gte=since).aggregate(t=Sum("coins_spent"))["t"] or 0
                if not total:
                    return {}
                data = qs.filter(created_at__gte=since).values("service").annotate(total=Sum("coins_spent"))
                return {r["service"]: round((r["total"] / total) * 100, 1) for r in data}

            top_services = {
                "daily": service_percent(1),
                "weekly": service_percent(7),
                "monthly": service_percent(30),
            }

            # ─── Top fans
            profile = getattr(user, "profile", None)
            top_fans = [
                {"name": tf.fan.user.name if hasattr(tf.fan, "user") else tf.fan.name, "coins": tf.score}
                for tf in TopFan.objects.filter(creator=profile or user.profile).order_by("-score")[:5]
            ]

            # ─── Final creator data
            data = {
                "mode": "creator",
                "total_coins": coins_total,
                "usd_value": f"{usd_total:.2f}",
                "category": category,
                "quick_trend": quick_trend,
                "top_services": top_services,
                "top_fans": top_fans,
            }

            return api_response(
                success=True,
                message="Creator Vault analytics fetched successfully.",
                data=data,
                status_code=200,
            )

        # ──────────────── USER VAULT ────────────────
        purchases = CoinPurchase.objects.filter(user=user).order_by("-created_at")[:30]
        since = timezone.now() - timezone.timedelta(days=30)

        spent = (
            SpendEvent.objects.filter(fan=user, created_at__gte=since)
            .values("service")
            .annotate(total=Sum("coins_spent"))
        )

        quick_stats = {x["service"]: x["total"] for x in spent if x["total"] > 0}

        quick_stats_renamed = {}
        for key, value in quick_stats.items():
            if key == "tip":
                quick_stats_renamed["gifts"] = value
            else:
                quick_stats_renamed[key] = value

        #  Ensure default categories always exist
        for key in ["chat", "gifts"]:
            quick_stats_renamed.setdefault(key, 0)

        # ─── Final user data
        data = {
            "mode": "user",
            "wallet_name": "The Vault",
            "token_name": "Whysper Coins",
            "balance": wallet.balance,
            "balance_usd": f"{Decimal(wallet.balance) * COIN_VALUE_USD:.2f}",
            "quick_stats": quick_stats_renamed,
            "history": CoinPurchaseSerializer(purchases, many=True).data,
        }

        return api_response(
            success=True,
            message="User Vault data fetched successfully.",
            data=data,
            status_code=200,
        )


# -----------------------
# Coin Packages + Stripe
# -----------------------
class PackageList(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        packs = CoinPackage.objects.all().order_by("coins")
        return api_response(data=CoinPackageSerializer(packs, many=True).data)


class CreateStripeCheckout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pack_id = request.data.get("package_id")
        if not pack_id:
            return api_response(success=False, message="package_id required.", status_code=400)
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
        return api_response(message="Checkout session created.", data={"url": session.url})


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        return HttpResponse(status=400)

    if event.get("type") == "checkout.session.completed":
        data = event["data"]["object"]
        try:
            user_id = data["metadata"]["user_id"]
            package_id = data["metadata"]["package_id"]
            user = CustomUser.objects.get(id=user_id)
            pkg = CoinPackage.objects.get(id=package_id)
        except Exception:
            # Acknowledge but skip if metadata/user/pkg missing
            return HttpResponse(status=200)

        CoinPurchase.objects.get_or_create(
            txn_id=data["id"],
            defaults={
                "user": user,
                "package": pkg,
                "coins_added": pkg.coins,
                "amount_usd": pkg.price_usd,
                "method": "stripe",
            }
        )
        user.wallet.add(pkg.coins)
    return HttpResponse(status=200)


# -----------------------
# Creator + Payout
# -----------------------
class PayoutEligibility(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can_earn(request.user):
            return api_response(data={"can_request": False, "reason": "Not monetized"})
        usd = Decimal(request.user.wallet.balance) * COIN_VALUE_USD
        return api_response(data={
            "balance_coins": request.user.wallet.balance,
            "balance_usd": f"{usd:.2f}",
            "threshold_usd": f"{MIN_PAYOUT_USD:.2f}",
            "can_request": usd >= MIN_PAYOUT_USD
        })


class RequestPayout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not can_earn(request.user):
            return api_response(success=False, message="Not monetized.", status_code=403)

        account_id = request.data.get("account_id")
        if not account_id:
            return api_response(success=False, message="account_id required.", status_code=400)

        try:
            account = PayoutAccount.objects.get(id=account_id, user=request.user)
        except PayoutAccount.DoesNotExist:
            return api_response(success=False, message="Invalid account.", status_code=404)

        usd = Decimal(request.user.wallet.balance) * COIN_VALUE_USD
        if usd < MIN_PAYOUT_USD:
            return api_response(success=False, message="Minimum $50 required.", status_code=400)

        req = PayoutRequest.objects.create(user=request.user, amount_usd=usd, account=account)
        request.user.wallet.balance = 0
        request.user.wallet.save(update_fields=["balance"])
        return api_response(message="Payout requested successfully.", data=PayoutRequestSerializer(req).data, status_code=201)


# -----------------------
# Payout Accounts CRUD
# -----------------------
class PayoutAccountListCreate(APIView):
   
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = request.user.payout_accounts.all().order_by("-created_at")
        return api_response(data=PayoutAccountSerializer(accounts, many=True).data)

    def post(self, request):
        # Prevent exact duplicates
        bank_name = request.data.get("bank_name")
        account_number = request.data.get("account_number")
        existing = PayoutAccount.objects.filter(
            user=request.user,
            bank_name=bank_name,
            account_number=account_number,
        ).first()
        if existing:
            return api_response(
                success=True,
                message="Payout account already exists.",
                data=PayoutAccountSerializer(existing).data,
                status_code=200,
            )

        ser = PayoutAccountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        acc = ser.save(user=request.user)

        # Auto-default if it's the first account; otherwise honor client default
        others = request.user.payout_accounts.exclude(id=acc.id)
        if not others.exists():
            acc.is_default = True
            acc.save(update_fields=["is_default"])
        elif acc.is_default:
            others.update(is_default=False)

        return api_response(
            message="Payout account created successfully.",
            data=PayoutAccountSerializer(acc).data,
            status_code=201
        )


class PayoutAccountSetDefault(APIView):
    
    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        try:
            account = PayoutAccount.objects.get(id=account_id, user=request.user)
        except PayoutAccount.DoesNotExist:
            return api_response(success=False, message="Account not found.", status_code=404)

        request.user.payout_accounts.update(is_default=False)
        account.is_default = True
        account.save(update_fields=["is_default"])

        return api_response(
            success=True,
            message="Default payout account updated successfully.",
            data=PayoutAccountSerializer(account).data,
            status_code=200,
        )
