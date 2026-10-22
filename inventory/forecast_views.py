from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .forecast import build_suggestions


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reorder_suggestions(request):
    try:
        lead = int(request.query_params.get('lead_days', 7))
        cover = int(request.query_params.get('cover_days', 14))
    except ValueError:
        return Response({'detail': 'lead_days and cover_days must be whole numbers.'}, status=400)
    if lead < 1 or cover < 1:
        return Response({'detail': 'lead_days and cover_days must be at least 1.'}, status=400)
    return Response(build_suggestions(lead, cover))