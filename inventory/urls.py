from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    MedicineViewSet,
    login_view,
    medicine_history,
    dashboard_summary,
    low_stock_medicines,
    expired_medicines,
    near_expiry_medicines,
)
from .sales_views import sales
from .scan_views import scan, link_barcode
from .forecast_views import reorder_suggestions
from .ops_views import orders, receive_order, write_off, history, forecast_chart
from .user_views import users, user_active, user_reset_password

router = DefaultRouter()
router.register(r'medicines', MedicineViewSet, basename='medicine')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', login_view, name='login'),
    path('sales/', sales, name='sales'),
    path('scan/', scan, name='scan'),
    path('scan/link/', link_barcode, name='scan-link'),
    path('reorder-suggestions/', reorder_suggestions, name='reorder-suggestions'),
    path('orders/', orders, name='orders'),
    path('orders/<int:order_id>/receive/', receive_order, name='order-receive'),
    path('medicines/<int:medicine_id>/write-off/', write_off, name='write-off'),
    path('history/', history, name='history'),
    path('users/', users, name='users'),
    path('users/<int:user_id>/active/', user_active, name='user-active'),
    path('users/<int:user_id>/reset-password/', user_reset_password, name='user-reset-password'),
    path('forecast-chart/', forecast_chart, name='forecast-chart'),
    path('medicines/<int:medicine_id>/history/', medicine_history, name='medicine-history'),
    path('dashboard/summary/', dashboard_summary, name='dashboard-summary'),
    path('medicines-low-stock/', low_stock_medicines, name='low-stock'),
    path('medicines-expired/', expired_medicines, name='expired'),
    path('medicines-near-expiry/', near_expiry_medicines, name='near-expiry'),
]
