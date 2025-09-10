# labels/models.py
from django.conf import settings
from django.db import models

class Label(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="labels"
    )
    name = models.CharField(max_length=120)
    sku_type = models.CharField(max_length=80)
    category = models.CharField(max_length=80)
    unit_index = models.PositiveIntegerField()
    # Globally unique code now
    code = models.CharField(max_length=300, unique=True)  # e.g., <userId>-name-type-category-001
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # NOTE: removed unique_together = (("user", "code"),)
        indexes = [
            models.Index(fields=["user", "name"]),
            models.Index(fields=["user", "sku_type"]),
            models.Index(fields=["user", "category"]),
            # code already gets an index automatically via unique=True
        ]

    def __str__(self):
        return self.code
