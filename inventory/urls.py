from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicineViewSet, login_view

router = DefaultRouter()
router.register(r'medicines', MedicineViewSet, basename='medicine')

urlpatterns = [
    path('', include(router.urls)),
    path('login/', login_view, name='login'),
]