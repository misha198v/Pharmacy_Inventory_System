from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include

urlpatterns = [
    path('', lambda request: redirect('http://localhost:3000/')),
    path('admin/', admin.site.urls),
    path('api/', include('inventory.urls')), # Add this line for DRF's login/logout views
]