import re

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile
from .permissions import IsManager

USERNAME_RE = re.compile(r'^[A-Za-z0-9._-]{3,30}$')
ROLES = ('staff', 'manager')


def _manager_only(request):
    """Return a 403 response if the user is not a manager, otherwise None."""
    if not IsManager().has_permission(request, None):
        return Response({'detail': 'Only managers can do this.'}, status=403)
    return None


def _role_of(user):
    if user.is_superuser:
        return 'manager'
    profile = getattr(user, 'userprofile', None)
    return profile.role if profile else 'staff'


def _user_dict(user):
    return {
        'id': user.id,
        'username': user.username,
        'role': _role_of(user),
        'is_active': user.is_active,
        'last_login': user.last_login.isoformat() if user.last_login else None,
    }


def _check_password(password, user=None):
    """Return an error message if the password is not acceptable, otherwise None."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        return ' '.join(exc.messages)
    return None


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def users(request):
    denied = _manager_only(request)
    if denied:
        return denied

    User = get_user_model()

    if request.method == 'GET':
        everyone = User.objects.select_related('userprofile').order_by('username')
        return Response([_user_dict(u) for u in everyone])

    username = str(request.data.get('username', '')).strip()
    password = str(request.data.get('password', ''))
    role = str(request.data.get('role', 'staff')).strip().lower()

    if not USERNAME_RE.match(username):
        return Response(
            {'detail': 'Username must be 3 to 30 characters: letters, numbers, dots, dashes or underscores.'},
            status=400,
        )
    if role not in ROLES:
        return Response({'detail': 'Role must be staff or manager.'}, status=400)
    if User.objects.filter(username__iexact=username).exists():
        return Response({'detail': 'That username is already taken.'}, status=400)

    problem = _check_password(password, User(username=username))
    if problem:
        return Response({'detail': problem}, status=400)

    with transaction.atomic():
        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.update_or_create(user=user, defaults={'role': role})

    return Response(_user_dict(user), status=201)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_active(request, user_id):
    """Turn an account on or off. A deactivated person can no longer log in."""
    denied = _manager_only(request)
    if denied:
        return denied

    active = request.data.get('is_active')
    if not isinstance(active, bool):
        return Response({'detail': 'is_active must be true or false.'}, status=400)

    User = get_user_model()
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=404)

    if target.pk == request.user.pk and not active:
        return Response({'detail': 'You cannot deactivate your own account.'}, status=400)

    target.is_active = active
    target.save(update_fields=['is_active'])
    if not active:
        Token.objects.filter(user=target).delete()   # end any session they have open

    return Response(_user_dict(target))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def user_reset_password(request, user_id):
    """A manager sets a new password for someone who forgot theirs."""
    denied = _manager_only(request)
    if denied:
        return denied

    User = get_user_model()
    try:
        target = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=404)

    password = str(request.data.get('password', ''))
    problem = _check_password(password, target)
    if problem:
        return Response({'detail': problem}, status=400)

    target.set_password(password)
    target.save(update_fields=['password'])
    if target.pk != request.user.pk:
        Token.objects.filter(user=target).delete()   # they must log in again with the new password

    return Response({'detail': 'Password updated.'})
