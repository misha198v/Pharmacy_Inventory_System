from django.urls import path, include
from rest_framework.routers import DefaultRouter 
from .views import (
    MedicineViewSet, login_view, medicine_history, dashboard_summary,
    low_stock_medicines, expired_medicines, near_expiry_medicines,
)
router = DefaultRouter()
router.register(r'medicines', MedicineViewSet, basename='medicine')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', login_view, name='login'),
    path('medicines/<int:medicine_id>/history/', medicine_history, name='medicine-history'),
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('medicines-low-stock/', low_stock_medicines, name='low-stock'),
    path('medicines-expired/', expired_medicines, name='expired'),
    path('medicines-near-expiry/', near_expiry_medicines, name='near-expiry'),
]
router = DefaultRouter()
router.register(r'medicines', MedicineViewSet, basename='medicine')

