from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Medicine
from .serializers import MedicineSerializer

class MedicineViewSet(viewsets.ModelViewSet):
    serializer_class = MedicineSerializer

    # 1. Search Logic (Filtering)
    def get_queryset(self):
        queryset = Medicine.objects.all()
        query = self.request.query_params.get('search')
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset

    # 2. Sell Medicine Logic (Custom Action)
    # This replaces your 'sell_medicine' function
    @action(detail=True, methods=['post'])
    def sell(self, request, pk=None):
        medicine = self.get_object_or_404(Medicine, pk=pk)
        if medicine.stock_quantity > 0:
            medicine.stock_quantity -= 1
            medicine.save()
            return Response({'status': 'sold', 'new_quantity': medicine.stock_quantity})
        else:
            return Response({'error': 'Out of stock'}, status=status.HTTP_400_BAD_REQUEST)