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

import logging
logger = logging.getLogger(__name__)


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

        import cloudinary.uploader

        # Save profile photo on profile
        if profile_photo:
            cloudinary_result = cloudinary.uploader.upload(
                profile_photo,
                resource_type="auto",
                folder="profile_photos/"
            )
            profile.profile_photo = cloudinary_result['secure_url']
            profile.profile_photo_public_id = cloudinary_result['public_id']
            profile.save(update_fields=["profile_photo", "profile_photo_public_id"])

        # Save KYC artifacts on monetization model
        if id_proof:
            cloudinary_result = cloudinary.uploader.upload(
                id_proof,
                resource_type="auto",
                folder="kyc/id_proofs/"
            )
            monet.id_proof = cloudinary_result['secure_url']
            monet.id_proof_public_id = cloudinary_result['public_id']

        if intro_video:
            cloudinary_result = cloudinary.uploader.upload(
                intro_video,
                resource_type="auto",
                folder="kyc/intro_videos/"
            )
            monet.intro_video = cloudinary_result['secure_url']
            monet.intro_video_public_id = cloudinary_result['public_id']

        monet.save(update_fields=["id_proof", "intro_video", "id_proof_public_id", "intro_video_public_id"])

        # Mark monetization as pending (Stripe payout account can be added later)
        monet.status = MonetizationStatus.PENDING
        monet.applied_at = timezone.now()
        monet.save(update_fields=["status", "applied_at"])

        return api_response(
            success=True,
            message="Monetization application submitted successfully. You can connect your Stripe account later.",
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



# -----------------------
# Monetization Approve (10% cut)
# -----------------------
class MonetizationApproveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, user_id):
        from .models import CreatorProfile

        user = CustomUser.objects.get(id=user_id)
        monet, _ = CreatorMonetization.objects.get_or_create(user=user)
        wallet, _ = Wallet.objects.get_or_create(user=user)

        #  active  skip
        if monet.status == MonetizationStatus.ACTIVE:
            return api_response(message=f"{user.name} is already a Creator.")

        # Approve monetization
        monet.status = MonetizationStatus.ACTIVE
        monet.approved_at = timezone.now()
        monet.reviewed_by = request.user
        monet.save(update_fields=["status", "approved_at", "reviewed_by"])

        # 10% cut + 90% 
        total_coins = int(wallet.balance or 0)
        platform_cut = int(total_coins * Decimal("0.10"))
        creator_earning = max(total_coins - platform_cut, 0)

        wallet.balance = creator_earning
        wallet.save(update_fields=["balance"])
        wallet.refresh_from_db()  #  Ensure latest value

        # Creator profile flag
        CreatorProfile.objects.get_or_create(user=user)
        user.profile.is_creator = True
        user.profile.save(update_fields=["is_creator"])

        return api_response(
            success=True,
            message=f"{user.name} is now a Creator. 10% platform cut applied successfully.",
            data={
                "platform_cut": platform_cut,
                "creator_earning": creator_earning,
                "final_balance": wallet.balance,
            },
            status_code=200
        )


# -----------------------
# Vault (User/Creator)
# -----------------------
class VaultView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        wallet, _ = Wallet.objects.get_or_create(user=user)
        wallet.refresh_from_db()  # always get latest wallet balance

        # ──────────────── CREATOR VAULT ────────────────
        if hasattr(user, "monetization") and user.monetization.status == MonetizationStatus.ACTIVE:
            qs = SpendEvent.objects.filter(creator=user)
            coins_from_spend = qs.aggregate(total=Sum("coins_spent"))["total"] or 0

            #no earning use wallet.balance 
            coins_total = coins_from_spend if coins_from_spend > 0 else int(wallet.balance)
            usd_total = Decimal(coins_total) * COIN_VALUE_USD

            # Category breakdown
            category = {
                row["service"]: row["coins"]
                for row in qs.values("service").annotate(coins=Sum("coins_spent"))
            }

            category_labels = {
                "chat": "Messages",
                "tip": "Tips",
                "locked": "Unlocks",
                "photo": "Content",
                "video": "Videos",
            }

            category = {category_labels.get(k, k): v for k, v in category.items()}
            for label in category_labels.values():
                category.setdefault(label, 0)

            now = timezone.now()
            week_since = now - timezone.timedelta(days=7)
            month_since = now - timezone.timedelta(days=30)
            year_since = now - timezone.timedelta(days=365)

            def build_trend(qs_values, field):
                return [{field: str(r[field]), "usd": str(r["usd"])} for r in qs_values]

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

            quick_trend = {
                "weekly": build_trend(weekly, "day"),
                "monthly": build_trend(monthly, "day"),
                "yearly": build_trend(yearly, "month"),
            }

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

            profile = getattr(user, "profile", None)
            top_fans = [
                {"name": tf.fan.user.name if hasattr(tf.fan, "user") else tf.fan.name, "coins": tf.score}
                for tf in TopFan.objects.filter(creator=profile or user.profile).order_by("-score")[:5]
            ]

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
            quick_stats_renamed["gifts" if key == "tip" else key] = value

        for key in ["chat", "gifts"]:
            quick_stats_renamed.setdefault(key, 0)

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


# -----------------------
# Stripe Purchase Restriction
# -----------------------
class CreateStripeCheckout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Prevent creators from buying packages
        monet = getattr(request.user, "monetization", None)
        if monet and monet.status == MonetizationStatus.ACTIVE:
            return api_response(
                success=False,
                message="Creators cannot purchase coin packages.",
                status_code=403
            )

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


# -----------------------
# Stripe Webhook 
# -----------------------
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


# =========================================================
# Stripe Connect — Payout Accounts (replaces bank accounts)
# =========================================================

class PayoutAccountListCreate(APIView):
    """
    GET  → List creator's connected Stripe accounts.
    POST → Create a Stripe Connect Express account and return onboarding URL.
           Body (optional): { "account_name": "My Main Account" }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        accounts = request.user.payout_accounts.all().order_by("-created_at")
        return api_response(data=PayoutAccountSerializer(accounts, many=True).data)

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        account_name = request.data.get("account_name", "")

        try:
            # 1️⃣ Create Stripe Connect Express account
            acct = stripe.Account.create(
                type="express",
                country="US",
                email=getattr(request.user, "email", None) or None,
                capabilities={
                    "card_payments": {"requested": True},
                    "transfers": {"requested": True},
                },
                metadata={"user_id": str(request.user.id)},
            )

            # 2️⃣ Save locally
            payout_account = PayoutAccount.objects.create(
                user=request.user,
                stripe_account_id=acct.id,
                account_name=account_name,
                onboarding_complete=False,
            )

            # Auto-default if first account
            others = request.user.payout_accounts.exclude(id=payout_account.id)
            if not others.exists():
                payout_account.is_default = True
                payout_account.save(update_fields=["is_default"])

            # 3️⃣ Generate onboarding link
            account_link = stripe.AccountLink.create(
                account=acct.id,
                refresh_url=settings.STRIPE_CONNECT_REFRESH_URL,
                return_url=settings.STRIPE_CONNECT_RETURN_URL,
                type="account_onboarding",
            )

            return api_response(
                message="Stripe Connect account created. Complete onboarding using the URL.",
                data={
                    "account": PayoutAccountSerializer(payout_account).data,
                    "onboarding_url": account_link.url,
                },
                status_code=201,
            )

        except stripe.StripeError as e:
            logger.error(f"Stripe Connect error: {e}")
            return api_response(
                success=False,
                message=f"Stripe error: {str(e)}",
                status_code=400,
            )


class StripeConnectCallback(APIView):
    """
    GET → Called after creator completes Stripe onboarding.
          Checks account status and marks onboarding_complete.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Find user's payout accounts that haven't completed onboarding
        accounts = request.user.payout_accounts.filter(onboarding_complete=False)
        updated = []

        for payout_acc in accounts:
            try:
                acct = stripe.Account.retrieve(payout_acc.stripe_account_id)
                if acct.charges_enabled or acct.payouts_enabled or acct.details_submitted:
                    payout_acc.onboarding_complete = True
                    payout_acc.save(update_fields=["onboarding_complete"])
                    updated.append(payout_acc.stripe_account_id)
            except stripe.StripeError as e:
                logger.warning(f"Could not verify Stripe account {payout_acc.stripe_account_id}: {e}")

        if updated:
            return api_response(
                message="Stripe onboarding verified successfully.",
                data={"verified_accounts": updated},
            )
        return api_response(
            success=False,
            message="No accounts were verified. Please complete Stripe onboarding first.",
            status_code=400,
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


# -----------------------
# Creator Payout Eligibility & Request (Stripe Transfer)
# -----------------------
class PayoutEligibility(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not can_earn(request.user):
            return api_response(data={"can_request": False, "reason": "Not monetized"})
        usd = Decimal(request.user.wallet.balance) * COIN_VALUE_USD

        # Check if user has a completed Stripe account
        has_stripe = request.user.payout_accounts.filter(onboarding_complete=True).exists()

        return api_response(data={
            "balance_coins": request.user.wallet.balance,
            "balance_usd": f"{usd:.2f}",
            "threshold_usd": f"{MIN_PAYOUT_USD:.2f}",
            "can_request": usd >= MIN_PAYOUT_USD and has_stripe,
            "has_stripe_account": has_stripe,
        })


class RequestPayout(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not can_earn(request.user):
            return api_response(success=False, message="Not monetized.", status_code=403)

        account_id = request.data.get("account_id")
        if not account_id:
            return api_response(success=False, message="account_id required.", status_code=400)

        # 💲 Get the amount of USD the user wants to withdraw
        withdraw_usd = request.data.get("withdraw_usd")
        if not withdraw_usd:
            return api_response(success=False, message="withdraw_usd required.", status_code=400)
        
        try:
            withdraw_usd = Decimal(str(withdraw_usd))
            if withdraw_usd <= 0:
                raise ValueError
        except Exception:
            return api_response(success=False, message="withdraw_usd must be a valid positive number.", status_code=400)

        if withdraw_usd < MIN_PAYOUT_USD:
            return api_response(
                success=False, 
                message=f"Minimum withdrawal is ${MIN_PAYOUT_USD}.", 
                status_code=400
            )

        try:
            account = PayoutAccount.objects.get(id=account_id, user=request.user)
        except PayoutAccount.DoesNotExist:
            return api_response(success=False, message="Invalid account.", status_code=404)

        # Ensure Stripe onboarding is complete
        if not account.onboarding_complete:
            # Fallback: Check Stripe API directly just in case the callback was missed
            stripe.api_key = settings.STRIPE_SECRET_KEY
            try:
                acct = stripe.Account.retrieve(account.stripe_account_id)
                if acct.charges_enabled or acct.payouts_enabled or acct.details_submitted:
                    account.onboarding_complete = True
                    account.save(update_fields=["onboarding_complete"])
                else:
                    return api_response(
                        success=False,
                        message="Please complete Stripe onboarding before requesting a payout.",
                        status_code=400,
                    )
            except stripe.StripeError as e:
                logger.warning(f"Failed to fetch Stripe account {account.stripe_account_id}: {e}")
                return api_response(
                    success=False,
                    message="Could not verify Stripe account status. Please try again.",
                    status_code=400,
                )

        # Calculate equivalent coins (ceiling division to ensure enough coins are taken for the USD requested)
        import math
        coins_to_withdraw = int(math.ceil(withdraw_usd / COIN_VALUE_USD))

        # Check if they have enough coins in their wallet
        if request.user.wallet.balance < coins_to_withdraw:
            return api_response(
                success=False, 
                message=f"Insufficient balance. You need {coins_to_withdraw} coins for ${withdraw_usd:.2f}, but you only have {request.user.wallet.balance} coins.", 
                status_code=400
            )

        # We will transfer the EXACT usd requested
        usd = withdraw_usd

        # Create Stripe Transfer
        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            transfer = stripe.Transfer.create(
                amount=int(usd * 100),  # Stripe uses cents
                currency="usd",
                destination=account.stripe_account_id,
                description=f"Payout of {coins_to_withdraw} coins for {request.user.name} (user_id={request.user.id})",
                metadata={
                    "user_id": str(request.user.id),
                    "payout_account_id": str(account.id),
                    "coins_withdrawn": str(coins_to_withdraw),
                },
            )

            req = PayoutRequest.objects.create(
                user=request.user,
                amount_usd=usd,
                account=account,
                status="processing",
                stripe_transfer_id=transfer.id,
            )

            # Deduct ONLY the requested coins from the creator's wallet balance
            request.user.wallet.balance -= coins_to_withdraw
            request.user.wallet.save(update_fields=["balance"])

            return api_response(
                message=f"Payout of {coins_to_withdraw} coins (${usd:.2f}) requested successfully.",
                data=PayoutRequestSerializer(req).data,
                status_code=201,
            )

        except stripe.StripeError as e:
            logger.error(f"Stripe Transfer error for user {request.user.id}: {e}")
            return api_response(
                success=False,
                message=f"Stripe transfer failed: {str(e)}",
                status_code=400,
            )
