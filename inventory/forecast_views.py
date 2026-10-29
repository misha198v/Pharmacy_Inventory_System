from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forecast import build_suggestions

MAX_DAYS = 365


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reorder_suggestions(request):
    try:
        lead = int(request.query_params.get('lead_days', 7))
        cover = int(request.query_params.get('cover_days', 14))
    except ValueError:
        return Response({'detail': 'lead_days and cover_days must be whole numbers.'}, status=400)
    if not (1 <= lead <= MAX_DAYS and 1 <= cover <= MAX_DAYS):
        return Response(
            {'detail': f'lead_days and cover_days must be between 1 and {MAX_DAYS}.'},
            status=400,
        )
    return Response(build_suggestions(lead, cover))