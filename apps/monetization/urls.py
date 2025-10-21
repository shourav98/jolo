from django.urls import path
from . import views

urlpatterns = [
    path("monetization/apply/",  views.MonetizationApply.as_view()),
    path("monetization/status/", views.MonetizationStatusView.as_view()),
    path("vault/",               views.VaultView.as_view()),
    path("packs/",               views.PackageList.as_view()),
    path("add-coins/",           views.MockAddCoins.as_view()),  # mock top-up
    path('test-monetization/',   views.TestMonetizationView.as_view(), name='test-monetization'),
    path('debug-wallet/',       views.DebugWalletView.as_view(), name='test-wallet-basic'),
    path('debug-both-wallets/', views.DebugBothWalletsView.as_view(), name='debug-both-wallets'),
    path('test-wallet-comprehensive/', views.TestWalletComprehensiveView.as_view(), name='test-wallet-comprehensive'),
]
