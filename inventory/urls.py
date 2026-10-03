from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicineViewSet, login_view, medicine_history, dashboard_summary 

router = DefaultRouter()
router.register(r'medicines', MedicineViewSet, basename='medicine')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', login_view, name='login'),
    path('medicines/<int:medicine_id>/history/', medicine_history, name='medicine-history'),
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
]