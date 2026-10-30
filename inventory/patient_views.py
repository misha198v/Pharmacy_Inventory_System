"""Public endpoints for the patient page.

Anyone can call these without logging in, so they return drug information only:
no stock, prices, batches, pharmacy or customer data.
"""

from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from .models import DrugBarcode, DrugInfo, Medicine

DISCLAIMER = (
    "This page is for learning. It does not replace advice from your doctor, "
    "clinician or pharmacist. Do not change, swap or stop a medicine without asking one of them."
)

NOT_FOUND_MESSAGE = (
    "We do not have information about this medicine yet. Please ask your pharmacist. "
    "We do not guess, because a wrong answer about a medicine can cause harm."
)


class PatientRateThrottle(AnonRateThrottle):
    # Set here so no change to settings.py is needed.
    rate = '60/min'


def _lines(text):
    return [line.strip() for line in (text or '').splitlines() if line.strip()]


def card(drug):
    return {
        'id': drug.pk,
        'name': drug.name,
        'generic_name': drug.generic_name,
        'also_sold_as': [b.strip() for b in drug.also_sold_as.split(',') if b.strip()],
        'drug_group': drug.drug_group,
        'purpose': drug.purpose,
        'purpose_label': drug.get_purpose_display(),
        'purpose_note': drug.purpose_note,
        'what_it_is_for': drug.what_it_is_for,
        'how_it_is_usually_taken': _lines(drug.how_it_is_usually_taken),
        'before_you_take_it': _lines(drug.before_you_take_it),
        'get_help_if': _lines(drug.get_help_if),
        'similar_medicines': _lines(drug.similar_medicines),
        'reviewed': drug.is_reviewed,
        'reviewed_by': drug.reviewed_by or None,
        'reviewed_on': str(drug.reviewed_on) if drug.reviewed_on else None,
        'disclaimer': DISCLAIMER,
    }


def drug_for_name(name):
    return DrugInfo.objects.filter(name__iexact=(name or '').strip()).first()


def drug_for_code(code):
    """Find a drug by barcode: first the drug record's own barcodes, then the
    barcode this pharmacy linked to one of its medicines."""
    hit = DrugBarcode.objects.filter(code=code).select_related('drug').first()
    if hit:
        return hit.drug
    medicine = Medicine.objects.filter(barcode=code).first()
    return drug_for_name(medicine.name) if medicine else None


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([PatientRateThrottle])
def patient_lookup(request):
    """Look up one drug by ?code= (barcode), ?name= or ?id=."""
    code = request.query_params.get('code', '').strip()
    name = request.query_params.get('name', '').strip()
    drug_id = request.query_params.get('id', '').strip()

    if not (code or name or drug_id):
        return Response({'detail': 'Give a barcode (code), a medicine name (name) or an id.'}, status=400)

    if code:
        drug = drug_for_code(code)
    elif name:
        drug = drug_for_name(name)
    else:
        drug = DrugInfo.objects.filter(pk=drug_id).first() if drug_id.isdigit() else None

    if drug is None:
        return Response({'found': False, 'message': NOT_FOUND_MESSAGE})
    return Response({'found': True, 'drug': card(drug)})


@api_view(['GET'])
@permission_classes([AllowAny])
@throttle_classes([PatientRateThrottle])
def patient_search(request):
    """Search by name, active ingredient or brand name, for people with no barcode."""
    q = request.query_params.get('q', '').strip()
    if len(q) < 2:
        return Response({'results': []})
    drugs = DrugInfo.objects.filter(
        Q(name__icontains=q) | Q(generic_name__icontains=q) | Q(also_sold_as__icontains=q)
    )[:10]
    return Response({
        'results': [
            {
                'id': d.pk,
                'name': d.name,
                'generic_name': d.generic_name,
                'purpose': d.purpose,
                'purpose_label': d.get_purpose_display(),
            }
            for d in drugs
        ]
    })