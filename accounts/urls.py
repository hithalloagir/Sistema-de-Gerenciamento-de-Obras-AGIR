from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("usuarios/", views.UserManagementView.as_view(), name="manage_users"),
    path("usuarios/<int:pk>/editar/", views.UserEditView.as_view(), name="edit_user"),
    path("usuarios/<int:pk>/excluir/", views.UserDeleteView.as_view(), name="delete_user"),
]
