from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token

from .models import Medicine, UserProfile

User = get_user_model()


class PharmacyAuthTests(APITestCase):
    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser",
            password="secret123"
        )
        self.manager_user = User.objects.create_user(
            username="manageruser",
            password="secret123"
        )
        UserProfile.objects.create(user=self.staff_user, role="staff")
        UserProfile.objects.create(user=self.manager_user, role="manager")

        self.medicine = Medicine.objects.create(
            name="Paracetamol",
            description="Pain reliever",
            price=12.50,
            stock_quantity=50,
            reorder_level=10,
            expiry_date="2030-12-31",
            added_by=self.staff_user,
        )

    def test_login_success(self):
        url = "/api/login/"
        data = {"username": "staffuser", "password": "secret123"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)

    def test_login_failure(self):
        url = "/api/login/"
        data = {"username": "staffuser", "password": "wrongpass"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_cannot_delete_medicine(self):
        self.client.force_authenticate(user=self.staff_user)
        url = f"/api/medicines/{self.medicine.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_can_delete_medicine(self):
        self.client.force_authenticate(user=self.manager_user)
        url = f"/api/medicines/{self.medicine.id}/"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_unauthenticated_user_cannot_access_medicines(self):
        url = "/api/medicines/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)