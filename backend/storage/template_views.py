"""
Django Template Views for Intelligent Storage System.
Class-based and function-based views for rendering templates.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
)
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from .models import FileSearchStore, MediaFile, DocumentChunk, SearchQuery
from .forms import (
    FileSearchStoreForm, MediaFileForm, SemanticSearchForm,
    MediaFileFilterForm, StoreFilterForm
)


# ===== Dashboard View =====

class DashboardView(TemplateView):
    """Main dashboard view."""
    template_name = 'storage/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Recent files
        context['recent_files'] = MediaFile.objects.select_related(
            'file_search_store'
        ).order_by('-uploaded_at')[:10]

        # Store statistics
        context['stores'] = FileSearchStore.objects.annotate(
            file_count=Count('files'),
            chunk_count=Count('chunks')
        ).order_by('-created_at')[:5]

        # File type distribution
        from django.db.models import Count
        context['file_types'] = MediaFile.objects.values(
            'detected_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')

        # Recent searches
        context['recent_searches'] = SearchQuery.objects.order_by(
            '-created_at'
        )[:10]

        return context


# ===== File Search Store Views =====

class FileSearchStoreListView(ListView):
    """List all file search stores."""
    model = FileSearchStore
    template_name = 'storage/store_list.html'
    context_object_name = 'stores'
    paginate_by = 20

    def get_queryset(self):
        queryset = FileSearchStore.objects.annotate(
            file_count=Count('files'),
            chunk_count=Count('chunks')
        )

        # Apply filters
        form = StoreFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('is_active'):
                is_active = form.cleaned_data['is_active'] == 'true'
                queryset = queryset.filter(is_active=is_active)

            if form.cleaned_data.get('chunking_strategy'):
                queryset = queryset.filter(
                    chunking_strategy=form.cleaned_data['chunking_strategy']
                )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = StoreFilterForm(self.request.GET)
        return context


class FileSearchStoreDetailView(DetailView):
    """Detail view for a file search store."""
    model = FileSearchStore
    template_name = 'storage/store_detail.html'
    context_object_name = 'store'
    slug_field = 'name'
    slug_url_kwarg = 'name'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        store = self.object

        # Get files in this store
        files = MediaFile.objects.filter(
            file_search_store=store
        ).order_by('-uploaded_at')

        paginator = Paginator(files, 20)
        page = self.request.GET.get('page', 1)
        context['files'] = paginator.get_page(page)

        # Statistics
        context['stats'] = {
            'total_files': files.count(),
            'indexed_files': files.filter(is_indexed=True).count(),
            'total_chunks': DocumentChunk.objects.filter(
                file_search_store=store
            ).count(),
        }

        return context


class FileSearchStoreCreateView(CreateView):
    """Create a new file search store."""
    model = FileSearchStore
    form_class = FileSearchStoreForm
    template_name = 'storage/store_form.html'
    success_url = reverse_lazy('storage:store_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Store "{form.instance.display_name}" created successfully!'
        )
        return super().form_valid(form)


class FileSearchStoreUpdateView(UpdateView):
    """Update a file search store."""
    model = FileSearchStore
    form_class = FileSearchStoreForm
    template_name = 'storage/store_form.html'
    slug_field = 'name'
    slug_url_kwarg = 'name'

    def get_success_url(self):
        return reverse_lazy('storage:store_detail', kwargs={'name': self.object.name})

    def form_valid(self, form):
        messages.success(
            self.request,
            f'Store "{form.instance.display_name}" updated successfully!'
        )
        return super().form_valid(form)


class FileSearchStoreDeleteView(DeleteView):
    """Delete a file search store."""
    model = FileSearchStore
    template_name = 'storage/store_confirm_delete.html'
    success_url = reverse_lazy('storage:store_list')
    slug_field = 'name'
    slug_url_kwarg = 'name'

    def delete(self, request, *args, **kwargs):
        messages.success(
            request,
            f'Store "{self.get_object().display_name}" deleted successfully!'
        )
        return super().delete(request, *args, **kwargs)


# ===== Media File Views =====

class MediaFileListView(ListView):
    """List all media files."""
    model = MediaFile
    template_name = 'storage/file_list.html'
    context_object_name = 'files'
    paginate_by = 20

    def get_queryset(self):
        queryset = MediaFile.objects.select_related('file_search_store')

        # Apply filters
        form = MediaFileFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('detected_type'):
                queryset = queryset.filter(
                    detected_type=form.cleaned_data['detected_type']
                )

            if form.cleaned_data.get('file_search_store'):
                queryset = queryset.filter(
                    file_search_store=form.cleaned_data['file_search_store']
                )

            if form.cleaned_data.get('is_indexed'):
                is_indexed = form.cleaned_data['is_indexed'] == 'true'
                queryset = queryset.filter(is_indexed=is_indexed)

            if form.cleaned_data.get('search'):
                search = form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(original_name__icontains=search) |
                    Q(user_comment__icontains=search)
                )

        return queryset.order_by('-uploaded_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = MediaFileFilterForm(self.request.GET)
        return context


class MediaFileDetailView(DetailView):
    """Detail view for a media file."""
    model = MediaFile
    template_name = 'storage/file_detail.html'
    context_object_name = 'file'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get chunks for this file
        context['chunks'] = DocumentChunk.objects.filter(
            media_file=self.object
        ).order_by('chunk_index')[:20]

        return context


class MediaFileUploadView(CreateView):
    """Upload a new media file."""
    model = MediaFile
    form_class = MediaFileForm
    template_name = 'storage/file_upload.html'
    success_url = reverse_lazy('storage:file_list')

    def form_valid(self, form):
        messages.success(
            self.request,
            f'File "{form.instance.original_name}" uploaded successfully!'
        )
        return super().form_valid(form)


# ===== Search Views =====

class SemanticSearchView(TemplateView):
    """Semantic search interface."""
    template_name = 'storage/search.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = SemanticSearchForm(self.request.GET or None)

        # If form is submitted and valid, perform search
        if self.request.GET and context['form'].is_valid():
            query = context['form'].cleaned_data['query']
            # Search logic would go here (using the API)
            context['query'] = query
            context['results'] = []  # Placeholder

        return context


# ===== Statistics Views =====

@cache_page(60 * 5)  # Cache for 5 minutes
def statistics_view(request):
    """Display system statistics."""
    from django.db.models import Avg, Max, Min

    stats = {
        'stores': {
            'total': FileSearchStore.objects.count(),
            'active': FileSearchStore.objects.filter(is_active=True).count(),
            'total_quota': FileSearchStore.objects.aggregate(
                total=Sum('storage_quota')
            )['total'] or 0,
        },
        'files': {
            'total': MediaFile.objects.count(),
            'indexed': MediaFile.objects.filter(is_indexed=True).count(),
            'total_size': MediaFile.objects.aggregate(
                total=Sum('file_size')
            )['total'] or 0,
            'avg_size': MediaFile.objects.aggregate(
                avg=Avg('file_size')
            )['avg'] or 0,
        },
        'chunks': {
            'total': DocumentChunk.objects.count(),
            'avg_per_file': DocumentChunk.objects.values(
                'media_file'
            ).annotate(
                count=Count('id')
            ).aggregate(avg=Avg('count'))['avg'] or 0,
        },
    }

    # File type distribution
    file_types = MediaFile.objects.values(
        'detected_type'
    ).annotate(
        count=Count('id'),
        total_size=Sum('file_size')
    ).order_by('-count')

    stats['file_types'] = list(file_types)

    return render(request, 'storage/statistics.html', {'stats': stats})


# ===== AJAX Views =====

def ajax_store_stats(request, store_id):
    """Get store statistics via AJAX."""
    try:
        store = FileSearchStore.objects.get(id=store_id)
        data = {
            'total_files': store.total_files,
            'total_chunks': store.total_chunks,
            'storage_size_bytes': store.storage_size_bytes,
            'embeddings_size_bytes': store.embeddings_size_bytes,
            'usage_percentage': store.storage_used_percentage,
            'is_quota_exceeded': store.is_quota_exceeded(),
        }
        return JsonResponse(data)
    except FileSearchStore.DoesNotExist:
        return JsonResponse({'error': 'Store not found'}, status=404)


def ajax_file_chunks(request, file_id):
    """Get file chunks via AJAX."""
    try:
        chunks = DocumentChunk.objects.filter(
            media_file_id=file_id
        ).values(
            'chunk_id', 'chunk_index', 'chunk_text',
            'token_count', 'chunking_strategy'
        ).order_by('chunk_index')

        return JsonResponse({'chunks': list(chunks)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
