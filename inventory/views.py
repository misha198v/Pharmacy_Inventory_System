from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Medicine, UserProfile
from .serializers import MedicineSerializer, UserSerializer

# LOGIN VIEW
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user:
        token, _ = Token.objects.get_or_create(user=user)
        try:
            role = user.userprofile.role
        except:
            role = 'staff'
        return Response({'token': token.key, 'username': user.username, 'role': role})
    return Response({'error': 'Invalid credentials'}, status=400)

# MEDICINE VIEWSET
class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        # Save who added the medicine
        serializer.save(added_by=self.request.user)

    def update(self, request, *args, **kwargs):
        # Only managers can edit
        try:
            role = request.user.userprofile.role
        except:
            role = 'staff'
        if role != 'manager':
            return Response({'error': 'Only managers can edit medicines.'}, status=403)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only managers can delete
        try:
            role = request.user.userprofile.role
        except:
            role = 'staff'
        if role != 'manager':
            return Response({'error': 'Only managers can delete medicines.'}, status=403)
        return super().destroy(request, *args, **kwargs)