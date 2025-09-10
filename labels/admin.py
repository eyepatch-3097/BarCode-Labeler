from django.contrib import admin
from .models import Label

@admin.register(Label)
class LabelAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "sku_type", "category", "unit_index", "user", "created_at")
    list_filter = ("sku_type", "category", "user")
    search_fields = ("code", "name")
    ordering = ("-id",)
