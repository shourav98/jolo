from django.urls import path
from . import views

urlpatterns = [
    path("monetization/apply/",  views.MonetizationApply.as_view()),
    path("monetization/status/", views.MonetizationStatusView.as_view()),
    path("vault/",               views.VaultView.as_view()),
    path("packs/",               views.PackageList.as_view()),
    path("add-coins/",           views.MockAddCoins.as_view()),  # mock top-up
]
