# labels/urls.py
from django.urls import path
from . import views

app_name = "labels"
urlpatterns = [
    path("", views.home, name="home"),
    path("api/list/", views.api_list, name="api_list"),
    path("api/create/", views.api_create, name="api_create"),
]
