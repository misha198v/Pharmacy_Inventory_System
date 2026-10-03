from .permissions import IsManagerOrReadOnly
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from .models import Medicine, UserProfile
from .serializers import MedicineSerializer, UserSerializer


class LoginRateThrottle(ScopedRateThrottle):
    scope = 'auth_login'


# LOGIN VIEW
@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
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
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'role': role,
            },
            'token': token.key,
        })
    return Response({'detail': 'Invalid username or password'}, status=401)


# MEDICINE VIEWSET
class MedicineViewSet(viewsets.ModelViewSet):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [IsManagerOrReadOnly]

    def perform_create(self, serializer):
        # Save who added the medicine
        serializer.save(added_by=self.request.user)