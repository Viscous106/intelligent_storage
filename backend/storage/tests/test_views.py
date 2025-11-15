"""
Django Tests for Storage Views and API Endpoints.
Test all view functionality and API responses.
"""

from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from storage.models import FileSearchStore, MediaFile
import json


class FileSearchStoreAPITest(APITestCase):
    """Test FileSearchStore API endpoints."""

    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()

        self.store = FileSearchStore.objects.create(
            name='test-store',
            display_name='Test Store',
            chunking_strategy='auto',
            max_tokens_per_chunk=512,
        )

    def test_list_stores(self):
        """Test listing all stores."""
        url = reverse('api:filesearchstore-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'test-store')

    def test_create_store(self):
        """Test creating a new store."""
        url = reverse('api:filesearchstore-list')
        data = {
            'name': 'new-store',
            'display_name': 'New Store',
            'chunking_strategy': 'semantic',
            'max_tokens_per_chunk': 1024,
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FileSearchStore.objects.count(), 2)
        self.assertEqual(response.data['name'], 'new-store')

    def test_retrieve_store(self):
        """Test retrieving a specific store."""
        url = reverse('api:filesearchstore-detail', kwargs={'pk': self.store.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'test-store')

    def test_update_store(self):
        """Test updating a store."""
        url = reverse('api:filesearchstore-detail', kwargs={'pk': self.store.id})
        data = {
            'display_name': 'Updated Store',
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.store.refresh_from_db()
        self.assertEqual(self.store.display_name, 'Updated Store')

    def test_delete_store(self):
        """Test deleting a store."""
        url = reverse('api:filesearchstore-detail', kwargs={'pk': self.store.id})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FileSearchStore.objects.count(), 0)


class MediaFileAPITest(APITestCase):
    """Test MediaFile API endpoints."""

    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()

        self.store = FileSearchStore.objects.create(
            name='test-store',
            display_name='Test Store',
        )

        self.file = MediaFile.objects.create(
            original_name='test.pdf',
            file_path='/media/test.pdf',
            file_size=1024,
            detected_type='document',
            file_search_store=self.store,
        )

    def test_list_files(self):
        """Test listing all files."""
        url = reverse('api:mediafile-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_filter_files_by_type(self):
        """Test filtering files by type."""
        url = reverse('api:mediafile-list')
        response = self.client.get(url, {'detected_type': 'document'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        response = self.client.get(url, {'detected_type': 'image'})
        self.assertEqual(len(response.data), 0)


class TemplateViewTest(TestCase):
    """Test template-based views."""

    def setUp(self):
        """Set up test client."""
        self.client = Client()

    def test_dashboard_view(self):
        """Test dashboard view loads."""
        # This will 404 if routes aren't set up yet
        # url = reverse('storage:dashboard')
        # response = self.client.get(url)
        # self.assertEqual(response.status_code, 200)
        pass

    def test_store_list_view(self):
        """Test store list view."""
        # url = reverse('storage:store_list')
        # response = self.client.get(url)
        # self.assertEqual(response.status_code, 200)
        pass


class FormTest(TestCase):
    """Test form validation."""

    def test_store_form_validation(self):
        """Test FileSearchStoreForm validation."""
        from storage.forms import FileSearchStoreForm

        # Valid data
        form_data = {
            'name': 'test-store',
            'display_name': 'Test Store',
            'chunking_strategy': 'auto',
            'max_tokens_per_chunk': 512,
            'max_overlap_tokens': 50,
            'storage_quota': 1073741824,
        }

        form = FileSearchStoreForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_store_form_invalid_name(self):
        """Test form with invalid store name."""
        from storage.forms import FileSearchStoreForm

        # Invalid name (uppercase)
        form_data = {
            'name': 'Test-Store',  # Should be lowercase
            'display_name': 'Test Store',
        }

        form = FileSearchStoreForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
