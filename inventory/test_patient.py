import json
from datetime import date, timedelta

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from .models import DrugBarcode, DrugInfo, Medicine
from .patient_views import patient_lookup, patient_search


def make_drug(name='Amoxicillin 500mg', **kw):
    defaults = dict(
        generic_name='Amoxicillin', also_sold_as='Amoxil, Moxal', drug_group='Antibiotic',
        purpose='TREATS', purpose_note='Treats infections caused by bacteria.',
        what_it_is_for='An antibiotic for bacterial infections.',
        how_it_is_usually_taken='Three times a day.\n\nFinish the course.\n',
        before_you_take_it='Not for penicillin allergy.',
        get_help_if='Swelling of the face.',
        similar_medicines='Ampicillin\nCo-amoxiclav',
    )
    defaults.update(kw)
    return DrugInfo.objects.create(name=name, **defaults)


class PatientTests(TestCase):
    def setUp(self):
        cache.clear()                       # the endpoints are rate limited
        self.factory = APIRequestFactory()
        self.drug = make_drug()
        DrugBarcode.objects.create(code='5012345678900', drug=self.drug)

    def lookup(self, **params):
        return patient_lookup(self.factory.get('/patient/lookup/', params))

    def search(self, q):
        return patient_search(self.factory.get('/patient/search/', {'q': q}))

    # ---- finding a drug ----
    def test_by_drug_barcode_without_logging_in(self):
        r = self.lookup(code='5012345678900')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data['found'])
        self.assertEqual(r.data['drug']['name'], 'Amoxicillin 500mg')

    def test_by_barcode_the_pharmacy_linked_to_its_own_stock(self):
        Medicine.objects.create(
            name='amoxicillin 500MG', batch_number='A1', price=1, stock_quantity=5,
            expiry_date=timezone.localdate() + timedelta(days=30), barcode='1001',
        )
        r = self.lookup(code='1001')
        self.assertTrue(r.data['found'])
        self.assertEqual(r.data['drug']['id'], self.drug.pk)

    def test_unknown_barcode_says_so_and_does_not_guess(self):
        r = self.lookup(code='999')
        self.assertFalse(r.data['found'])
        self.assertIn('ask your pharmacist', r.data['message'])
        self.assertNotIn('drug', r.data)

    def test_stocked_medicine_with_no_drug_record(self):
        Medicine.objects.create(
            name='Mystery Pill', batch_number='M1', price=1, stock_quantity=5,
            expiry_date=timezone.localdate() + timedelta(days=30), barcode='2002',
        )
        self.assertFalse(self.lookup(code='2002').data['found'])

    def test_by_name_ignores_case_and_spaces(self):
        self.assertTrue(self.lookup(name='  AMOXICILLIN 500mg ').data['found'])

    def test_by_id(self):
        self.assertTrue(self.lookup(id=str(self.drug.pk)).data['found'])
        self.assertFalse(self.lookup(id='9999').data['found'])
        self.assertFalse(self.lookup(id='abc').data['found'])

    def test_nothing_given_is_refused(self):
        self.assertEqual(self.lookup().status_code, 400)

    # ---- what the patient sees ----
    def test_card_content(self):
        d = self.lookup(code='5012345678900').data['drug']
        self.assertEqual(d['purpose'], 'TREATS')
        self.assertEqual(d['purpose_label'], 'Treats')
        self.assertEqual(d['also_sold_as'], ['Amoxil', 'Moxal'])
        self.assertEqual(d['how_it_is_usually_taken'], ['Three times a day.', 'Finish the course.'])
        self.assertEqual(d['similar_medicines'], ['Ampicillin', 'Co-amoxiclav'])
        self.assertIn('does not replace advice', d['disclaimer'])

    def test_unreviewed_until_a_pharmacist_signs_it_off(self):
        d = self.lookup(code='5012345678900').data['drug']
        self.assertFalse(d['reviewed'])
        self.assertIsNone(d['reviewed_by'])
        self.drug.reviewed_by = 'A. Pharmacist'
        self.drug.save()
        self.assertFalse(self.lookup(code='5012345678900').data['drug']['reviewed'])   # needs a date too
        self.drug.reviewed_on = date(2026, 11, 1)
        self.drug.save()
        d = self.lookup(code='5012345678900').data['drug']
        self.assertTrue(d['reviewed'])
        self.assertEqual((d['reviewed_by'], d['reviewed_on']), ('A. Pharmacist', '2026-11-01'))

    def test_no_pharmacy_data_is_exposed(self):
        Medicine.objects.create(
            name='Amoxicillin 500mg', batch_number='SECRET-BATCH', price=1234, stock_quantity=777,
            expiry_date=timezone.localdate() + timedelta(days=30), barcode='1001', supplier='Hidden Ltd',
        )
        text = json.dumps(self.lookup(code='1001').data)
        for secret in ('SECRET-BATCH', '1234', '777', 'Hidden Ltd', 'price', 'stock', 'batch_number', 'supplier'):
            self.assertNotIn(secret, text, secret)

    # ---- searching ----
    def test_search_by_name_ingredient_or_brand(self):
        for q in ('amox', 'AMOXICILLIN', 'moxal'):
            self.assertEqual([x['name'] for x in self.search(q).data['results']],
                             ['Amoxicillin 500mg'], q)

    def test_search_needs_two_letters_and_handles_no_match(self):
        self.assertEqual(self.search('a').data['results'], [])
        self.assertEqual(self.search('zzzz').data['results'], [])

    def test_search_returns_at_most_ten(self):
        for i in range(15):
            make_drug(name=f'Testol {i}', generic_name='Testol')
        self.assertEqual(len(self.search('testol').data['results']), 10)

    def test_search_result_has_the_tag_but_not_the_full_card(self):
        r = self.search('amox').data['results'][0]
        self.assertEqual(r['purpose_label'], 'Treats')
        self.assertNotIn('how_it_is_usually_taken', r)