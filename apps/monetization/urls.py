from django.urls import path
from . import views

urlpatterns = [
    # Monetization
    path("monetization/apply/",  views.MonetizationApply.as_view()),
    path("monetization/status/", views.MonetizationStatusView.as_view()),
    path("monetization/approve/<int:user_id>/", views.MonetizationApproveView.as_view()),

    # Vault (user)
    path("vault/",               views.VaultView.as_view()),
    path("packs/",               views.PackageList.as_view()),

    # Stripe (coin purchase)
    path("checkout/create/",     views.CreateStripeCheckout.as_view()),
    path("stripe/webhook/",      views.stripe_webhook),

    # Stripe Connect (payout accounts)
    path("payout-accounts/",                          views.PayoutAccountListCreate.as_view()),
    path("payout-accounts/<int:account_id>/default/", views.PayoutAccountSetDefault.as_view()),
    path("stripe/connect/callback/",                  views.StripeConnectCallback.as_view()),

    # Creator payout
    path("creator/payout/eligibility/",  views.PayoutEligibility.as_view()),
    path("creator/payout/request/",      views.RequestPayout.as_view()),
]
