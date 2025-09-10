# accounts/views.py
from decimal import Decimal
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.utils import timezone
from django.contrib.auth import login

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import SignUpForm
from labels.models import Label
import razorpay
from .models import Payment
from django.db import transaction

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging

logger = logging.getLogger(__name__)

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Your account was created. You’re now signed in.")
            login(request, user)
            return redirect("labels:home")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})

@login_required
def profile_view(request):
    label_count = Label.objects.filter(user=request.user).count()
    return render(request, "accounts/profile.html", {
        "email": request.user.email,
        "public_id": getattr(request.user, "public_id", None),
        "index_id": request.user.id,
        "label_count": label_count,
        "credits": request.user.credits,
    })

@login_required
def buy_credits_view(request):
    return render(request, "accounts/buy_credits.html", {
        "price_per_credit": 50,     # INR
        "labels_per_credit": 10,
        "current_credits": request.user.credits,
    })

@login_required
@require_POST
def api_create_order(request):
    # credits user wants to buy
    try:
        credits = int(request.POST.get("credits", "0"))
    except ValueError:
        credits = 0
    if credits <= 0:
        return HttpResponseBadRequest("Invalid credits")

    # pricing
    amount_rupees = credits * settings.PRICE_PER_CREDIT
    amount_paise = amount_rupees * 100
    currency = settings.CURRENCY

    # create order at Razorpay
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    r_order = client.order.create({
        "amount": amount_paise,
        "currency": currency,
        "payment_capture": 1,
        "notes": {
            "user_id": str(request.user.public_id),
            "email": request.user.email,
            "credits": str(credits),
        }
    })

    # persist our record
    pay = Payment.objects.create(
        user=request.user,
        credits=credits,
        amount_paise=amount_paise,
        currency=currency,
        razorpay_order_id=r_order["id"],
        status="created",
    )

    return JsonResponse({
        "order_id": r_order["id"],
        "amount": amount_paise,
        "currency": currency,
        "credits": credits,
        "key_id": settings.RAZORPAY_KEY_ID,
        "name": settings.SITE_NAME,
        "prefill": {
            "email": request.user.email,
        }
    })


@login_required
@require_POST
def api_payment_success(request):
    """
    Frontend calls this after Razorpay Checkout returns success.
    We verify signature, mark payment Paid (idempotent), and top-up credits.
    """
    order_id = request.POST.get("razorpay_order_id")
    payment_id = request.POST.get("razorpay_payment_id")
    signature = request.POST.get("razorpay_signature")

    if not (order_id and payment_id and signature):
        return HttpResponseBadRequest("Missing params")

    # find our payment record
    try:
        pay = Payment.objects.select_for_update().get(razorpay_order_id=order_id, user=request.user)
    except Payment.DoesNotExist:
        return HttpResponseBadRequest("Order not found")

    # if already processed, just return current credits
    if pay.status == "paid":
        return JsonResponse({"ok": True, "credits_left": float(request.user.credits)})

    # verify signature
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        })
    except razorpay.errors.SignatureVerificationError:
        pay.status = "failed"
        pay.razorpay_payment_id = payment_id
        pay.razorpay_signature = signature
        pay.processed_at = timezone.now()
        pay.save(update_fields=["status", "razorpay_payment_id", "razorpay_signature", "processed_at"])
        return JsonResponse({"ok": False, "error": "Signature verification failed"}, status=400)

    # mark paid + credit the user (atomic via select_for_update above)
    from django.db import transaction
    with transaction.atomic():
        pay.status = "paid"
        pay.razorpay_payment_id = payment_id
        pay.razorpay_signature = signature
        pay.processed_at = timezone.now()
        pay.save(update_fields=["status", "razorpay_payment_id", "razorpay_signature", "processed_at"])

        # add credits (integers)
        request.user.credits = (request.user.credits or Decimal("0")) + Decimal(pay.credits)
        request.user.save(update_fields=["credits"])

    return JsonResponse({"ok": True, "credits_left": float(request.user.credits)})


@csrf_exempt
@require_POST
def webhook_razorpay(request):
    import razorpay

    secret = settings.RAZORPAY_WEBHOOK_SECRET or ""
    sig = request.headers.get("X-Razorpay-Signature", "")

    # --- body bytes -> string once ---
    body_bytes = request.body
    body_str = body_bytes.decode("utf-8")

    # 1) Verify signature (use client.utility)
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        client.utility.verify_webhook_signature(body_str, sig, secret)
    except Exception as e:
        logger.error("Webhook: signature verify failed: %s", e)
        # During dev, return 200 so Razorpay doesn't retry forever
        return JsonResponse({"ok": False, "msg": "invalid signature"}, status=200)

    # 2) Parse JSON (use body_str, not 'body')
    try:
        payload = json.loads(body_str)
    except Exception:
        logger.error("Webhook: bad JSON")
        return JsonResponse({"ok": False, "msg": "bad json"}, status=200)

    event = payload.get("event")
    payment_entity = (payload.get("payload", {}).get("payment", {}) or {}).get("entity") or {}
    order_id = payment_entity.get("order_id")
    payment_id = payment_entity.get("id")
    if not order_id:
        order_entity = (payload.get("payload", {}).get("order", {}) or {}).get("entity") or {}
        order_id = order_entity.get("id")

    if not order_id:
        logger.warning("Webhook: no order_id in payload")
        return JsonResponse({"ok": True, "msg": "no order id"}, status=200)

    # 3) Idempotent credit
    try:
        with transaction.atomic():
            pay = Payment.objects.select_for_update().get(razorpay_order_id=order_id)
            if pay.status == "paid":
                return JsonResponse({"ok": True, "msg": "already paid"}, status=200)

            if event in ("order.paid", "payment.captured", "payment.authorized"):
                pay.status = "paid"
                if payment_id:
                    pay.razorpay_payment_id = payment_id
                pay.processed_at = timezone.now()
                pay.save(update_fields=["status", "razorpay_payment_id", "processed_at"])

                user = pay.user
                user.credits = (user.credits or Decimal("0")) + Decimal(pay.credits)
                user.save(update_fields=["credits"])

                logger.info("Webhook: credited %s credits to %s", pay.credits, user.email)
                return JsonResponse({"ok": True, "msg": "credited", "credits_left": float(user.credits)}, status=200)
            else:
                logger.info("Webhook: ignored event %s", event)
                return JsonResponse({"ok": True, "msg": f"ignored {event}"}, status=200)
    except Payment.DoesNotExist:
        logger.warning("Webhook: payment not found for order %s", order_id)
        return JsonResponse({"ok": True, "msg": "payment not found"}, status=200)

@login_required
def payments_history(request):
    payments = (Payment.objects
                .filter(user=request.user)
                .order_by("-created_at"))
    return render(request, "accounts/payments.html", {"payments": payments})
