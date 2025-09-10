# accounts/admin.py
from decimal import Decimal
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User
from .models import Payment

@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User

    # LIST PAGE
    list_display = ("email", "credits", "public_id", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email", "public_id")
    ordering = ("email",)

    # (Optional) inline list editing of 'credits':
    list_editable = ("credits",)          # enable editing credits from list
    list_display_links = ("email",)       # ensure clicking email opens detail page

    # DETAIL PAGE (user edit)
    fieldsets = (
        (None, {"fields": ("email", "password", "public_id", "credits")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    # ADD USER PAGE
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active", "credits"),
        }),
    )

    # QUICK TOP-UP ACTIONS
    actions = ["topup_1_credit", "topup_5_credits", "topup_10_credits", "zero_credits"]

    @admin.action(description="Top up +1 credit")
    def topup_1_credit(self, request, queryset):
        self._topup(request, queryset, Decimal("1"))

    @admin.action(description="Top up +5 credits")
    def topup_5_credits(self, request, queryset):
        self._topup(request, queryset, Decimal("5"))

    @admin.action(description="Top up +10 credits")
    def topup_10_credits(self, request, queryset):
        self._topup(request, queryset, Decimal("10"))

    @admin.action(description="Set credits to 0")
    def zero_credits(self, request, queryset):
        for u in queryset:
            u.credits = Decimal("0")
            u.save(update_fields=["credits"])

    def _topup(self, request, queryset, amount: Decimal):
        for u in queryset:
            u.credits = (u.credits or Decimal("0")) + amount
            u.save(update_fields=["credits"])



@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("razorpay_order_id", "user", "credits", "amount_paise", "status", "created_at")
    list_filter = ("status", "currency")
    search_fields = ("razorpay_order_id", "razorpay_payment_id", "user__email")
    ordering = ("-created_at",)
