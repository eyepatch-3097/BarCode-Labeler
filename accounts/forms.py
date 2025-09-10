# accounts/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class SignUpForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email",)
        widgets = {
            "email": forms.EmailInput(attrs={
                "class":"w-full border rounded px-3 py-2",
                "placeholder":"you@brand.com"
            })
        }
