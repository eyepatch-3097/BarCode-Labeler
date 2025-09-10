# labels/views.py
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Q
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render
from .models import Label
from .utils import slug, pad
from decimal import Decimal

@login_required
def home(request):
    return render(request, "labels/home.html")

@login_required
def api_list(request):
    qn = request.GET.get("name","").lower()
    qt = request.GET.get("type","").lower()
    qc = request.GET.get("category","").lower()
    qs = Label.objects.filter(user=request.user)
    if qn: qs = qs.filter(Q(name__icontains=qn) | Q(code__icontains=qn))
    if qt: qs = qs.filter(sku_type__icontains=qt)
    if qc: qs = qs.filter(category__icontains=qc)
    qs = qs.order_by("-id")[:1000]
    data = [{
        "id": x.id,
        "name": x.name,
        "type": x.sku_type,
        "category": x.category,
        "unitIndex": x.unit_index,
        "code": x.code,
    } for x in qs]
    return JsonResponse({"labels": data})

@login_required
def api_create(request):
    if request.method != "POST":
        return HttpResponseBadRequest("POST only")
    name = request.POST.get("name","").strip()
    units = int(request.POST.get("units","0") or 0)
    sku_type = request.POST.get("type","").strip()
    category = request.POST.get("category","").strip()
    if not (name and units > 0 and sku_type and category):
        return HttpResponseBadRequest("Invalid payload")
    
    # Check credits
    credits_needed = Decimal(units) / Decimal(10)  # 1 credit = 10 labels
    if request.user.credits < credits_needed:
        return JsonResponse({"error": "Not enough credits. Please buy more."}, status=402)

    # Build a base that includes the user's public_id for GLOBAL uniqueness
    user_prefix = str(getattr(request.user, "public_id", request.user.id))
    base = f"{user_prefix[:8]}-{slug(name)}-{slug(sku_type)}-{slug(category)}-"

    with transaction.atomic():
        # Continue numbering per-user per (name,type,category) trio
        max_idx = (Label.objects
                   .filter(user=request.user, code__startswith=base)
                   .aggregate(Max("unit_index"))["unit_index__max"]) or 0
        created = []
        for i in range(1, units+1):
            idx = max_idx + i
            code = f"{base}{pad(idx)}"
            obj = Label.objects.create(
                user=request.user, name=name, sku_type=sku_type,
                category=category, unit_index=idx, code=code
            )
            created.append({"id": obj.id, "code": code, "unitIndex": idx})
        
        # Deduct credits
        request.user.credits = request.user.credits - credits_needed
        request.user.save(update_fields=["credits"])

    return JsonResponse({
        "created": created,
        "credits_left": float(request.user.credits)  # float so JSON is safe
    })
