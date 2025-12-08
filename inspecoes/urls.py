from django.urls import path
from . import views

urlpatterns = [
    # criar inspeção para uma obra específica
    path("nova/<int:obra_id>/", views.InspecaoCreateView.as_view(), name="nova_inspecao"),
    path("obra/<int:obra_id>/", views.InspecaoObraListView.as_view(), name="lista_obra"),
]
