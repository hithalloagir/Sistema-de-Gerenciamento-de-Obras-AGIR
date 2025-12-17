from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("usuarios/", views.UserManagementView.as_view(), name="manage_users"),
]
