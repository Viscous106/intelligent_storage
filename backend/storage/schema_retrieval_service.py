"""
Schema Retrieval Service

Provides intelligent schema retrieval with:
- Date range filtering
- Database type filtering
- Natural language query parsing using LLM
- Multiple selection criteria
"""

import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.conf import settings
from .models import MediaFile, JSONDataStore

logger = logging.getLogger(__name__)


class SchemaQueryParser:
    """Parse natural language queries into structured schema filters using LLM."""

    def __init__(self):
        self.ollama_base_url = getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self.model = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:latest')

    def parse_query(self, query: str) -> Dict[str, Any]:
        """
        Parse natural language query into structured filters.

        Args:
            query: Natural language query (e.g., "show me all SQL schemas from last week")

        Returns:
            Dictionary with parsed filters:
            {
                'database_type': 'sql' | 'nosql' | 'all',
                'date_range': {
                    'start_date': 'YYYY-MM-DD',
                    'end_date': 'YYYY-MM-DD'
                },
                'name_pattern': str,
                'tags': List[str],
                'limit': int
            }
        """
        try:
            # Create prompt for LLM
            prompt = self._create_parsing_prompt(query)

            # Call Ollama API
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                parsed_json = json.loads(result.get('response', '{}'))

                # Validate and normalize the parsed result
                return self._normalize_filters(parsed_json)
            else:
                logger.warning(f"LLM query parsing failed: {response.status_code}")
                return self._get_default_filters()

        except Exception as e:
            logger.error(f"Error parsing query with LLM: {e}")
            return self._get_default_filters()

    def _create_parsing_prompt(self, query: str) -> str:
        """Create a prompt for the LLM to parse the query."""
        current_date = datetime.now().strftime('%Y-%m-%d')

        return f"""You are a query parser for a schema retrieval system. Parse the following natural language query into a JSON structure.

Current date: {current_date}

User query: "{query}"

Parse this query and extract the following information:
1. database_type: Should be "sql", "nosql", or "all" (default: "all")
2. date_range: Extract start_date and end_date if mentioned
   - Support relative dates like "last week", "last month", "yesterday", "last 7 days"
   - Support absolute dates
   - If only one date is mentioned, use it as end_date and set start_date to 30 days before
   - Format: YYYY-MM-DD
3. name_pattern: Any specific name or keyword to search for in schema names
4. tags: List of relevant tags extracted from the query
5. limit: Number of results to return (default: 20, max: 100)

Examples:
- "show me all SQL schemas from last week" → {{"database_type": "sql", "date_range": {{"start_date": "2025-11-09", "end_date": "2025-11-16"}}, "limit": 20}}
- "get NoSQL schemas created in October" → {{"database_type": "nosql", "date_range": {{"start_date": "2025-10-01", "end_date": "2025-10-31"}}, "limit": 20}}
- "find schemas with 'user' in the name from last month" → {{"database_type": "all", "name_pattern": "user", "date_range": {{"start_date": "2025-10-16", "end_date": "2025-11-16"}}, "limit": 20}}

Return ONLY valid JSON without any explanation. If you cannot determine a value, omit that field or use the default.

JSON:"""

    def _normalize_filters(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize and validate parsed filters."""
        filters = {
            'database_type': parsed.get('database_type', 'all').lower(),
            'name_pattern': parsed.get('name_pattern', ''),
            'tags': parsed.get('tags', []),
            'limit': min(int(parsed.get('limit', 20)), 100)
        }

        # Normalize database type
        if filters['database_type'] not in ['sql', 'nosql', 'all']:
            filters['database_type'] = 'all'

        # Handle date range
        if 'date_range' in parsed:
            date_range = parsed['date_range']
            filters['date_range'] = {
                'start_date': date_range.get('start_date'),
                'end_date': date_range.get('end_date')
            }

        return filters

    def _get_default_filters(self) -> Dict[str, Any]:
        """Return default filters when parsing fails."""
        return {
            'database_type': 'all',
            'name_pattern': '',
            'tags': [],
            'limit': 20
        }


class SchemaRetrievalService:
    """Service for retrieving schema files with various filters."""

    def __init__(self):
        self.query_parser = SchemaQueryParser()

    def retrieve_schemas(
        self,
        database_type: Optional[str] = 'all',
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        name_pattern: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        user=None
    ) -> Dict[str, Any]:
        """
        Retrieve schemas based on filters.

        Args:
            database_type: 'sql', 'nosql', or 'all'
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            name_pattern: Pattern to search in schema names
            tags: List of tags to filter by
            limit: Maximum number of results
            user: User object for filtering by ownership

        Returns:
            Dictionary with schemas and metadata
        """
        try:
            # Start with base query for schema files
            query = MediaFile.objects.filter(
                storage_category='schemas',
                is_deleted=False
            )

            # Filter by user if provided
            if user:
                query = query.filter(user=user)

            # Filter by database type
            if database_type and database_type != 'all':
                query = query.filter(storage_subcategory=database_type.lower())

            # Filter by date range
            if start_date:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(uploaded_at__gte=start_datetime)

            if end_date:
                # Include the entire end date
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(uploaded_at__lt=end_datetime)

            # Filter by name pattern
            if name_pattern:
                query = query.filter(original_name__icontains=name_pattern)

            # Filter by tags
            if tags:
                for tag in tags:
                    query = query.filter(ai_tags__contains=[tag])

            # Order by most recent
            query = query.order_by('-uploaded_at')

            # Limit results
            schemas = query[:limit]

            # Build response
            schema_list = []
            for schema_file in schemas:
                # Get associated JSONDataStore if exists
                json_store = JSONDataStore.objects.filter(schema_file=schema_file).first()

                schema_info = {
                    'id': schema_file.id,
                    'filename': schema_file.original_name,
                    'database_type': schema_file.storage_subcategory.upper(),
                    'file_path': schema_file.relative_path,
                    'file_size': schema_file.file_size,
                    'mime_type': schema_file.mime_type,
                    'created_at': schema_file.uploaded_at.isoformat(),
                    'description': schema_file.ai_description,
                    'tags': schema_file.ai_tags,
                    'download_url': f'/api/smart/schemas/download/{schema_file.id}'
                }

                # Add JSON store info if available
                if json_store:
                    schema_info['json_store'] = {
                        'name': json_store.name,
                        'table_name': json_store.table_name,
                        'collection_name': json_store.collection_name,
                        'record_count': json_store.record_count,
                        'confidence_score': json_store.confidence_score
                    }

                schema_list.append(schema_info)

            return {
                'success': True,
                'count': len(schema_list),
                'total_available': query.count(),
                'schemas': schema_list,
                'filters_applied': {
                    'database_type': database_type,
                    'start_date': start_date,
                    'end_date': end_date,
                    'name_pattern': name_pattern,
                    'tags': tags,
                    'limit': limit
                }
            }

        except Exception as e:
            logger.error(f"Error retrieving schemas: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'schemas': []
            }

    def retrieve_schemas_by_query(self, natural_query: str, user=None) -> Dict[str, Any]:
        """
        Retrieve schemas using natural language query.

        Args:
            natural_query: Natural language query string
            user: User object for filtering by ownership

        Returns:
            Dictionary with schemas and metadata
        """
        # Parse the query using LLM
        filters = self.query_parser.parse_query(natural_query)

        logger.info(f"Parsed query '{natural_query}' into filters: {filters}")

        # Extract date range
        date_range = filters.get('date_range', {})
        start_date = date_range.get('start_date') if date_range else None
        end_date = date_range.get('end_date') if date_range else None

        # Call retrieve_schemas with parsed filters
        result = self.retrieve_schemas(
            database_type=filters.get('database_type', 'all'),
            start_date=start_date,
            end_date=end_date,
            name_pattern=filters.get('name_pattern'),
            tags=filters.get('tags'),
            limit=filters.get('limit', 20),
            user=user
        )

        # Add parsed query info
        result['parsed_query'] = filters
        result['original_query'] = natural_query

        return result

    def get_schema_content(self, schema_id: int, user=None) -> Dict[str, Any]:
        """
        Get the actual content of a schema file.

        Args:
            schema_id: MediaFile ID of the schema
            user: User object for permission checking

        Returns:
            Dictionary with schema content
        """
        try:
            query = MediaFile.objects.filter(
                id=schema_id,
                storage_category='schemas',
                is_deleted=False
            )

            if user:
                query = query.filter(user=user)

            schema_file = query.first()

            if not schema_file:
                return {
                    'success': False,
                    'error': 'Schema not found or unauthorized'
                }

            # Read file content
            with open(schema_file.file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                'success': True,
                'schema_id': schema_id,
                'filename': schema_file.original_name,
                'database_type': schema_file.storage_subcategory.upper(),
                'mime_type': schema_file.mime_type,
                'content': content,
                'created_at': schema_file.uploaded_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error reading schema content: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_schema_statistics(self, user=None) -> Dict[str, Any]:
        """
        Get statistics about stored schemas.

        Args:
            user: User object for filtering by ownership

        Returns:
            Dictionary with schema statistics
        """
        try:
            query = MediaFile.objects.filter(
                storage_category='schemas',
                is_deleted=False
            )

            if user:
                query = query.filter(user=user)

            total_schemas = query.count()
            sql_schemas = query.filter(storage_subcategory='sql').count()
            nosql_schemas = query.filter(storage_subcategory='nosql').count()

            # Get date range
            oldest = query.order_by('uploaded_at').first()
            newest = query.order_by('-uploaded_at').first()

            # Get total size
            total_size = sum(s.file_size for s in query)

            return {
                'success': True,
                'statistics': {
                    'total_schemas': total_schemas,
                    'sql_schemas': sql_schemas,
                    'nosql_schemas': nosql_schemas,
                    'total_size_bytes': total_size,
                    'oldest_schema': oldest.uploaded_at.isoformat() if oldest else None,
                    'newest_schema': newest.uploaded_at.isoformat() if newest else None
                }
            }

        except Exception as e:
            logger.error(f"Error getting schema statistics: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
_schema_retrieval_service = None


def get_schema_retrieval_service() -> SchemaRetrievalService:
    """Get or create the schema retrieval service singleton."""
    global _schema_retrieval_service
    if _schema_retrieval_service is None:
        _schema_retrieval_service = SchemaRetrievalService()
    return _schema_retrieval_service
