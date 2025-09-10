# accounts/urls.py
from django.urls import path
from django.urls import path
from .views import (
    profile_view,
    signup_view,
    buy_credits_view,
    api_create_order,        # <-- add this
    api_payment_success,     # <-- and this
    webhook_razorpay,
    payments_history,
)


urlpatterns = [
    path("profile/", profile_view, name="profile"),
    path("signup/", signup_view, name="signup"),
    path("buy-credits/", buy_credits_view, name="buy_credits"),
    path("api/create-order/", api_create_order, name="api_create_order"),
    path("api/payment-success/", api_payment_success, name="api_payment_success"),
    path("api/webhook/razorpay/", webhook_razorpay, name="razorpay_webhook"),  # <-- new
    path("payments/", payments_history, name="payments_history"),
]
