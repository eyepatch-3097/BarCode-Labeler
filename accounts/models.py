# accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid

class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    public_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    credits = models.DecimalField(max_digits=10, decimal_places=2, default=0) 

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    # attach the custom manager
    objects = UserManager()

    def __str__(self):
        return self.email

class Payment(models.Model):
    STATUS_CHOICES = [
        ("created", "Created"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    credits = models.PositiveIntegerField()
    amount_paise = models.PositiveIntegerField()     # amount in paise
    currency = models.CharField(max_length=8, default="INR")

    razorpay_order_id = models.CharField(max_length=64, unique=True)
    razorpay_payment_id = models.CharField(max_length=64, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=128, blank=True, null=True)

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="created")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)

    @property
    def amount_rupees(self):
        return self.amount_paise / 100

    class Meta:
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["razorpay_order_id"]),
        ]

    def __str__(self):
        return f"{self.user.email} • {self.razorpay_order_id} • {self.status}"