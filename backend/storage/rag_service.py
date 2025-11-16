"""
RAG (Retrieval Augmented Generation) service.
Handles document indexing and semantic search using Ollama + PostgreSQL pgvector.
"""

import logging
from typing import List, Dict, Any, Optional
from django.db.models import Q
from pgvector.django import L2Distance

from .models import MediaFile, DocumentChunk, SearchQuery
from .embedding_service import embedding_service
from .chunking_service import chunking_service

logger = logging.getLogger(__name__)


class RAGService:
    """
    Service for RAG operations: indexing documents and semantic search.
    """

    def __init__(self):
        """Initialize RAG service."""
        self.embedding_service = embedding_service
        self.chunking_service = chunking_service

    def index_document(self, media_file: MediaFile) -> Dict[str, Any]:
        """
        Index a document for semantic search.

        Args:
            media_file: MediaFile instance to index

        Returns:
            Dict with indexing results
        """
        try:
            # Extract text from file
            text = self.chunking_service.extract_text_from_file(
                media_file.file_path,
                media_file.detected_type
            )

            if not text or len(text.strip()) < 10:
                return {
                    'success': False,
                    'error': 'No extractable text content',
                    'chunks_created': 0
                }

            # Store the full text in MediaFile for complete document retrieval
            media_file.full_text = text
            media_file.save(update_fields=['full_text'])

            # Create chunks
            chunks_data = self.chunking_service.chunk_text(
                text,
                metadata={
                    'file_type': media_file.detected_type,
                    'file_name': media_file.original_name,
                    'ai_category': media_file.ai_category,
                    'ai_tags': media_file.ai_tags,
                }
            )

            if not chunks_data:
                return {
                    'success': False,
                    'error': 'Failed to create chunks',
                    'chunks_created': 0
                }

            # Generate embeddings and store chunks
            chunks_created = 0
            for chunk_data in chunks_data:
                # Generate embedding
                embedding = self.embedding_service.generate_embedding(
                    chunk_data['chunk_text']
                )

                # Create DocumentChunk
                DocumentChunk.objects.create(
                    media_file=media_file,
                    chunk_index=chunk_data['chunk_index'],
                    chunk_text=chunk_data['chunk_text'],
                    chunk_size=chunk_data['chunk_size'],
                    embedding=embedding,
                    file_name=media_file.original_name,
                    file_type=media_file.detected_type,
                    metadata=chunk_data['metadata']
                )
                chunks_created += 1

            logger.info(
                f"Indexed document '{media_file.original_name}' "
                f"with {chunks_created} chunks"
            )

            return {
                'success': True,
                'chunks_created': chunks_created,
                'file_name': media_file.original_name
            }

        except Exception as e:
            logger.error(f"Failed to index document: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'chunks_created': 0
            }

    def search(
        self,
        query: str,
        limit: int = 10,
        file_type_filter: Optional[str] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across indexed documents.

        Args:
            query: Search query text
            limit: Maximum number of results
            file_type_filter: Optional filter by file type
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of search results with relevance scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.generate_embedding(query)

            # Build query
            queryset = DocumentChunk.objects.all()

            if file_type_filter:
                queryset = queryset.filter(file_type=file_type_filter)

            # Perform vector similarity search
            results = queryset.order_by(
                L2Distance('embedding', query_embedding)
            )[:limit * 3]  # Get more chunks to ensure we have enough unique files

            # Group by media file and return full documents
            seen_files = {}
            search_results = []

            for chunk in results:
                if chunk.media_file:
                    file_id = chunk.media_file.id

                    # Skip if we already have this file and have enough results
                    if file_id in seen_files:
                        continue

                    if len(search_results) >= limit:
                        break

                    # Get the full document text
                    full_text = chunk.media_file.get_full_text()

                    result = {
                        'media_file_id': file_id,
                        'file_name': chunk.file_name,
                        'file_type': chunk.file_type,
                        'full_text': full_text,
                        'matched_chunk_index': chunk.chunk_index,
                        'matched_chunk_text': chunk.chunk_text[:200] + '...' if len(chunk.chunk_text) > 200 else chunk.chunk_text,
                        'metadata': chunk.metadata,
                    }
                    search_results.append(result)
                    seen_files[file_id] = True

            # Save search query for analytics
            SearchQuery.objects.create(
                query_text=query,
                query_embedding=query_embedding,
                results_count=len(search_results),
            )

            return search_results

        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []

    def get_context_for_llm(
        self,
        query: str,
        max_chunks: int = 5,
        file_type_filter: Optional[str] = None
    ) -> str:
        """
        Get relevant context for LLM response generation.

        Args:
            query: User query
            max_chunks: Maximum number of chunks to include
            file_type_filter: Optional file type filter

        Returns:
            Formatted context string for LLM
        """
        results = self.search(
            query=query,
            limit=max_chunks,
            file_type_filter=file_type_filter
        )

        if not results:
            return "No relevant context found."

        context_parts = []
        for i, result in enumerate(results, 1):
            # Use full text for better context, but truncate if too long
            full_text = result.get('full_text', '')
            if len(full_text) > 3000:  # Truncate very long documents
                display_text = full_text[:3000] + "\n\n[...document truncated for brevity...]"
            else:
                display_text = full_text

            context_parts.append(
                f"[Source {i}: {result['file_name']}]\n{display_text}\n"
            )

        return "\n---\n".join(context_parts)

    def generate_rag_response(
        self,
        query: str,
        max_context_chunks: int = 5,
        file_type_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate a response using RAG (Retrieval Augmented Generation).

        Args:
            query: User question
            max_context_chunks: Max chunks to retrieve
            file_type_filter: Optional file type filter

        Returns:
            Dict with response and sources
        """
        import requests
        from django.conf import settings

        try:
            # Get relevant context
            context = self.get_context_for_llm(
                query=query,
                max_chunks=max_context_chunks,
                file_type_filter=file_type_filter
            )

            # Build prompt
            prompt = f"""Based on the following context, answer the user's question.
If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {query}

Answer:"""

            # Generate response using Ollama
            ollama_host = settings.OLLAMA_SETTINGS['HOST']
            ollama_model = settings.OLLAMA_SETTINGS['MODEL']

            logger.warning(f"DEBUG: Calling Ollama at {ollama_host} with model '{ollama_model}'")

            response = requests.post(
                f"{ollama_host}/api/generate",
                json={
                    "model": ollama_model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )

            logger.info(f"Ollama response status: {response.status_code}")

            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', 'No response generated')

                # Get source documents
                sources = self.search(
                    query=query,
                    limit=max_context_chunks,
                    file_type_filter=file_type_filter
                )

                return {
                    'success': True,
                    'answer': answer,
                    'sources': sources,
                    'context_used': context
                }
            else:
                logger.error(
                    f"Ollama generation failed: {response.status_code} - {response.text}"
                )
                return {
                    'success': False,
                    'error': f'Failed to generate response: Ollama returned {response.status_code}'
                }

        except Exception as e:
            import traceback
            logger.error(f"RAG response generation failed: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': f'RAG error: {str(e)}'
            }

    def reindex_all_documents(self) -> Dict[str, Any]:
        """
        Reindex all media files.

        Returns:
            Dict with reindexing statistics
        """
        # Clear existing chunks
        DocumentChunk.objects.all().delete()

        total = 0
        successful = 0
        failed = 0

        # Get all media files that can be indexed
        indexable_types = ['documents', 'others']  # Extend as needed
        media_files = MediaFile.objects.filter(
            detected_type__in=indexable_types
        )

        for media_file in media_files:
            total += 1
            result = self.index_document(media_file)

            if result['success']:
                successful += 1
            else:
                failed += 1

        return {
            'total_processed': total,
            'successful': successful,
            'failed': failed
        }


# Singleton instance
rag_service = RAGService()
