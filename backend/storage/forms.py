"""
Django Forms for Intelligent Storage System.
Includes validators, clean methods, and custom widgets.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
import json
import os

from .models import (
    MediaFile, JSONDataStore, FileSearchStore,
    DocumentChunk, SearchQuery, UploadBatch
)


# ===== Custom Validators =====

def validate_file_size(value):
    """Validate file size (max 100MB)."""
    filesize = value.size
    if filesize > 100 * 1024 * 1024:  # 100MB
        raise ValidationError(_('File size cannot exceed 100 MB'))
    return value


def validate_json_data(value):
    """Validate JSON data structure."""
    try:
        if isinstance(value, str):
            json.loads(value)
        elif not isinstance(value, (dict, list)):
            raise ValidationError(_('Invalid JSON data type'))
    except json.JSONDecodeError:
        raise ValidationError(_('Invalid JSON format'))
    return value


def validate_metadata_keys(value):
    """Validate metadata keys (alphanumeric and underscore only)."""
    if isinstance(value, dict):
        for key in value.keys():
            if not key.replace('_', '').isalnum():
                raise ValidationError(
                    _('Metadata keys must contain only alphanumeric characters and underscores')
                )
    return value


def validate_store_name(value):
    """Validate store name (lowercase, alphanumeric, hyphens, underscores)."""
    if not value.replace('-', '').replace('_', '').isalnum():
        raise ValidationError(
            _('Store name must contain only lowercase letters, numbers, hyphens, and underscores')
        )
    if not value.islower():
        raise ValidationError(_('Store name must be lowercase'))
    return value


# ===== Model Forms =====

class FileSearchStoreForm(forms.ModelForm):
    """Form for creating/editing File Search Stores."""

    class Meta:
        model = FileSearchStore
        fields = [
            'name', 'display_name', 'description',
            'chunking_strategy', 'max_tokens_per_chunk', 'max_overlap_tokens',
            'storage_quota', 'custom_metadata', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Describe this store...'}),
            'custom_metadata': forms.Textarea(attrs={'rows': 4, 'placeholder': '{"key": "value"}'}),
            'chunking_strategy': forms.Select(attrs={'class': 'form-select'}),
        }
        help_texts = {
            'name': _('Unique identifier (lowercase, alphanumeric, hyphens, underscores)'),
            'max_tokens_per_chunk': _('Range: 100-2048 tokens'),
            'max_overlap_tokens': _('Range: 0-500 tokens'),
            'storage_quota': _('Storage quota in bytes (default: 1GB)'),
        }

    def clean_name(self):
        """Validate and clean store name."""
        name = self.cleaned_data.get('name', '').strip().lower()
        validate_store_name(name)

        # Check uniqueness (excluding current instance if editing)
        qs = FileSearchStore.objects.filter(name=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError(_('A store with this name already exists'))

        return name

    def clean_custom_metadata(self):
        """Validate and parse custom metadata."""
        metadata = self.cleaned_data.get('custom_metadata')
        if metadata:
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    raise ValidationError(_('Invalid JSON format'))
            validate_metadata_keys(metadata)
        return metadata or {}

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        max_tokens = cleaned_data.get('max_tokens_per_chunk')
        max_overlap = cleaned_data.get('max_overlap_tokens')

        if max_overlap and max_tokens and max_overlap >= max_tokens:
            raise ValidationError({
                'max_overlap_tokens': _('Overlap must be less than chunk size')
            })

        return cleaned_data


class MediaFileForm(forms.ModelForm):
    """Form for uploading/editing media files."""

    file_upload = forms.FileField(
        required=False,
        validators=[validate_file_size],
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '*/*'}),
        help_text=_('Maximum file size: 100MB')
    )

    class Meta:
        model = MediaFile
        fields = [
            'file_search_store', 'user_comment', 'custom_metadata'
        ]
        widgets = {
            'user_comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Add your comments...'}),
            'custom_metadata': forms.Textarea(attrs={'rows': 4, 'placeholder': '{"category": "documents"}'}),
        }

    def clean_custom_metadata(self):
        """Validate and parse custom metadata."""
        metadata = self.cleaned_data.get('custom_metadata')
        if metadata:
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    raise ValidationError(_('Invalid JSON format'))
            validate_metadata_keys(metadata)
        return metadata or {}

    def clean_file_upload(self):
        """Validate uploaded file."""
        file = self.cleaned_data.get('file_upload')
        if file:
            # Additional file type validation can be added here
            ext = os.path.splitext(file.name)[1].lower()
            # You can add specific extension validation if needed
        return file


class FileIndexForm(forms.Form):
    """Form for indexing files into stores."""

    file_id = forms.IntegerField(
        widget=forms.HiddenInput()
    )

    file_search_store = forms.ModelChoiceField(
        queryset=FileSearchStore.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_('Select a store (optional)')
    )

    chunking_strategy = forms.ChoiceField(
        choices=[
            ('', '--- Use Store Default ---'),
            ('auto', 'Auto (Automatic selection)'),
            ('whitespace', 'Whitespace (Word boundaries)'),
            ('semantic', 'Semantic (Paragraphs/sections)'),
            ('fixed', 'Fixed (Fixed size with overlap)')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    max_tokens_per_chunk = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(100), MaxValueValidator(2048)],
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '512'}),
        help_text=_('100-2048 tokens (default: 512)')
    )

    max_overlap_tokens = forms.IntegerField(
        required=False,
        validators=[MinValueValidator(0), MaxValueValidator(500)],
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '50'}),
        help_text=_('0-500 tokens (default: 50)')
    )

    custom_metadata = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': '{"department": "engineering"}'}),
        help_text=_('JSON format')
    )

    def clean_custom_metadata(self):
        """Validate and parse custom metadata."""
        metadata = self.cleaned_data.get('custom_metadata')
        if metadata:
            try:
                metadata = json.loads(metadata)
                validate_metadata_keys(metadata)
            except json.JSONDecodeError:
                raise ValidationError(_('Invalid JSON format'))
        return metadata or {}

    def clean(self):
        """Cross-field validation."""
        cleaned_data = super().clean()
        max_tokens = cleaned_data.get('max_tokens_per_chunk')
        max_overlap = cleaned_data.get('max_overlap_tokens')

        if max_overlap and max_tokens and max_overlap >= max_tokens:
            raise ValidationError({
                'max_overlap_tokens': _('Overlap must be less than chunk size')
            })

        return cleaned_data


class SemanticSearchForm(forms.Form):
    """Form for semantic search with filters."""

    query = forms.CharField(
        max_length=1000,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Enter your search query...',
            'autocomplete': 'off'
        }),
        help_text=_('Enter your search query')
    )

    file_search_stores = forms.ModelMultipleChoiceField(
        queryset=FileSearchStore.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text=_('Filter by stores (leave empty for all)')
    )

    metadata_filter = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': '{"department": "engineering"}'}),
        help_text=_('JSON format for metadata filtering')
    )

    limit = forms.IntegerField(
        initial=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '10'}),
        help_text=_('Number of results (1-100)')
    )

    include_citations = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def clean_metadata_filter(self):
        """Validate and parse metadata filter."""
        metadata = self.cleaned_data.get('metadata_filter')
        if metadata:
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise ValidationError(_('Invalid JSON format'))
        return metadata or {}


class JSONDataStoreForm(forms.ModelForm):
    """Form for JSON data stores."""

    json_data = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'placeholder': '{"key": "value"} or [...]'}),
        help_text=_('Paste your JSON data here'),
        validators=[validate_json_data]
    )

    force_db_type = forms.ChoiceField(
        choices=[
            ('', '--- Let AI Decide ---'),
            ('SQL', 'PostgreSQL (SQL)'),
            ('NoSQL', 'MongoDB (NoSQL)')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_('Override AI recommendation')
    )

    class Meta:
        model = JSONDataStore
        fields = ['name', 'description', 'user_comment']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'user_comment': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_json_data(self):
        """Parse and validate JSON data."""
        data = self.cleaned_data.get('json_data')
        try:
            parsed = json.loads(data)
            return parsed
        except json.JSONDecodeError as e:
            raise ValidationError(_(f'Invalid JSON: {str(e)}'))


class BatchUploadForm(forms.Form):
    """Form for batch file uploads."""

    files = forms.FileField(
        widget=forms.ClearableFileInput(attrs={
            'multiple': True,
            'class': 'form-control',
            'accept': '*/*'
        }),
        help_text=_('Select multiple files (max 100MB each)'),
        validators=[validate_file_size]
    )

    file_search_store = forms.ModelChoiceField(
        queryset=FileSearchStore.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_('Assign all files to this store (optional)')
    )

    user_comment = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'placeholder': 'Comments for all files...'}),
        help_text=_('This comment will be applied to all uploaded files')
    )

    auto_index = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text=_('Automatically index files after upload')
    )


class DocumentChunkForm(forms.ModelForm):
    """Form for editing document chunks (admin use)."""

    class Meta:
        model = DocumentChunk
        fields = [
            'media_file', 'file_search_store', 'chunk_text',
            'metadata', 'page_number'
        ]
        widgets = {
            'chunk_text': forms.Textarea(attrs={'rows': 10}),
            'metadata': forms.Textarea(attrs={'rows': 4}),
        }

    def clean_metadata(self):
        """Validate and parse metadata."""
        metadata = self.cleaned_data.get('metadata')
        if metadata:
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except json.JSONDecodeError:
                    raise ValidationError(_('Invalid JSON format'))
            validate_metadata_keys(metadata)
        return metadata or {}


# ===== Filter Forms =====

class MediaFileFilterForm(forms.Form):
    """Form for filtering media files."""

    detected_type = forms.ChoiceField(
        choices=[('', 'All Types')] + [
            ('document', 'Documents'),
            ('image', 'Images'),
            ('video', 'Videos'),
            ('audio', 'Audio'),
            ('code', 'Code'),
            ('compressed', 'Compressed'),
            ('other', 'Others')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    file_search_store = forms.ModelChoiceField(
        queryset=FileSearchStore.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label='All Stores'
    )

    is_indexed = forms.ChoiceField(
        choices=[
            ('', 'All Files'),
            ('true', 'Indexed Only'),
            ('false', 'Not Indexed')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search files...'
        })
    )


class StoreFilterForm(forms.Form):
    """Form for filtering file search stores."""

    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Stores'),
            ('true', 'Active Only'),
            ('false', 'Inactive Only')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    chunking_strategy = forms.ChoiceField(
        choices=[
            ('', 'All Strategies'),
            ('auto', 'Auto'),
            ('whitespace', 'Whitespace'),
            ('semantic', 'Semantic'),
            ('fixed', 'Fixed')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    quota_status = forms.ChoiceField(
        choices=[
            ('', 'All'),
            ('ok', 'Under 70%'),
            ('warning', '70-90%'),
            ('critical', 'Over 90%'),
            ('exceeded', 'Exceeded')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


# ===== Utility Functions =====

def get_form_errors_as_dict(form):
    """Convert form errors to dictionary format."""
    errors = {}
    for field, error_list in form.errors.items():
        errors[field] = [str(e) for e in error_list]
    return errors


def validate_bulk_metadata(metadata_list):
    """Validate a list of metadata dictionaries."""
    errors = []
    for idx, metadata in enumerate(metadata_list):
        try:
            validate_metadata_keys(metadata)
        except ValidationError as e:
            errors.append(f"Item {idx + 1}: {str(e)}")

    if errors:
        raise ValidationError(errors)
    return True
