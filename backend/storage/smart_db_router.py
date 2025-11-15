"""
Smart Database Router for Intelligent Storage System

Automatically routes JSON data to the optimal database (SQL/NoSQL) based on
structure analysis and provides unified interface for data operations.
"""

import json
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from django.conf import settings
from django.db import connection
from pymongo import MongoClient, ASCENDING, DESCENDING
from .json_analyzer import analyze_json_for_database, AnalysisResult
import logging
import ijson

logger = logging.getLogger(__name__)


class SmartDatabaseRouter:
    """
    Intelligent database router that:
    1. Analyzes JSON structure
    2. Routes to SQL (PostgreSQL) or NoSQL (MongoDB)
    3. Handles storage and retrieval with optimization
    4. Provides caching for fast access
    """

    def __init__(self):
        """Initialize database connections"""
        # MongoDB connection - use MONGODB_SETTINGS from settings.py
        mongo_config = getattr(settings, 'MONGODB_SETTINGS', {})
        mongo_host = mongo_config.get('HOST', 'localhost')
        mongo_port = mongo_config.get('PORT', 27017)
        mongo_user = mongo_config.get('USER') or None  # Convert empty string to None
        mongo_password = mongo_config.get('PASSWORD') or None  # Convert empty string to None
        mongo_db_name = mongo_config.get('DB', 'intelligent_storage_nosql')

        # Build connection URI - only include credentials if both are provided
        if mongo_user and mongo_password:
            mongo_uri = f"mongodb://{mongo_user}:{mongo_password}@{mongo_host}:{mongo_port}/"
        else:
            mongo_uri = f"mongodb://{mongo_host}:{mongo_port}/"

        self.mongo_client = MongoClient(mongo_uri)
        self.mongo_db = self.mongo_client[mongo_db_name]

        # Collections for different data types
        self.json_documents = self.mongo_db['json_documents']
        self.metadata_collection = self.mongo_db['metadata']

        # Create indexes for fast retrieval
        self._setup_indexes()

    def _setup_indexes(self):
        """Create optimized indexes for fast retrieval"""
        try:
            # Indexes for JSON documents
            self.json_documents.create_index([('doc_id', ASCENDING)], unique=True)
            self.json_documents.create_index([('created_at', DESCENDING)])
            self.json_documents.create_index([('admin_id', ASCENDING)])
            self.json_documents.create_index([('db_type', ASCENDING)])
            self.json_documents.create_index([('tags', ASCENDING)])

            # Indexes for metadata
            self.metadata_collection.create_index([('doc_id', ASCENDING)], unique=True)
            self.metadata_collection.create_index([('content_hash', ASCENDING)])

            logger.info("MongoDB indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

    def analyze_and_route(self, json_data: Any, admin_id: str,
                         tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze JSON structure and route to optimal database

        Args:
            json_data: JSON data to store
            admin_id: Admin user ID (for access control)
            tags: Optional tags for categorization

        Returns:
            Dictionary with storage info and analysis results
        """
        # Step 1: Analyze JSON structure
        logger.info("Analyzing JSON structure...")
        analysis = analyze_json_for_database(json_data)

        # Step 2: Generate unique document ID
        doc_id = self._generate_doc_id(json_data)

        # Step 3: Extract detailed schema for frontend display
        schema = self._extract_schema(json_data)

        # Step 4: Route to appropriate database based on intelligent analysis
        try:
            if analysis.recommended_db == 'sql':
                storage_result = self._store_in_sql(json_data, doc_id, admin_id, analysis, tags)
                db_type_used = 'sql'
            else:
                storage_result = self._store_in_nosql(json_data, doc_id, admin_id, analysis, tags)
                db_type_used = 'nosql'

            # Step 5: Store metadata
            self._store_metadata(doc_id, analysis, storage_result, admin_id)

            return {
                'success': True,
                'doc_id': doc_id,
                'database_type': db_type_used,
                'confidence': analysis.confidence,
                'reasons': analysis.reasons,
                'metrics': analysis.metrics,
                'schema': schema,
                'storage_info': storage_result,
                'timestamp': datetime.now().isoformat(),
                'decision_explanation': self._generate_decision_explanation(analysis, db_type_used)
            }

        except Exception as e:
            logger.error(f"Storage error for {doc_id}: {e}", exc_info=True)
            raise Exception(f"Failed to store data in {analysis.recommended_db.upper()}: {str(e)}")

    def analyze_and_route_streaming(self, json_file_obj, admin_id: str,
                                    tags: Optional[List[str]] = None,
                                    chunk_size: int = 1000) -> Dict[str, Any]:
        """
        Stream and parse large JSON files without loading all into memory

        Args:
            json_file_obj: File-like object containing JSON data
            admin_id: Admin user ID
            tags: Optional tags
            chunk_size: Number of records to batch insert at once

        Returns:
            Storage result with statistics
        """
        logger.info("Streaming large JSON file...")

        try:
            # For streaming, we'll parse arrays incrementally
            parser = ijson.items(json_file_obj, 'item')

            # Collect first few items for analysis
            sample_items = []
            all_items = []

            for idx, item in enumerate(parser):
                all_items.append(item)
                if idx < 10:  # Sample first 10 items for analysis
                    sample_items.append(item)

            # Analyze the sample to determine database routing
            if sample_items:
                analysis = analyze_json_for_database(sample_items)
            else:
                # Single object, analyze as-is
                json_file_obj.seek(0)
                data = json.load(json_file_obj)
                return self.analyze_and_route(data, admin_id, tags)

            # Generate document ID
            doc_id = self._generate_doc_id_from_timestamp()

            # Store all items
            if analysis.recommended_db == 'sql':
                result = self._store_streaming_sql(all_items, doc_id, admin_id, analysis, tags, chunk_size)
            else:
                result = self._store_streaming_nosql(all_items, doc_id, admin_id, analysis, tags, chunk_size)

            return {
                'success': True,
                'doc_id': doc_id,
                'database_type': analysis.recommended_db,
                'confidence': analysis.confidence,
                'reasons': analysis.reasons,
                'metrics': analysis.metrics,
                'storage_info': result,
                'timestamp': datetime.now().isoformat(),
                'streaming': True
            }

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            raise

    def _generate_decision_explanation(self, analysis: AnalysisResult, db_type: str) -> Dict[str, Any]:
        """
        Generate user-friendly explanation for database choice

        Args:
            analysis: Analysis result with metrics
            db_type: Chosen database type

        Returns:
            Dictionary with detailed explanation
        """
        explanations = {
            'sql': {
                'summary': 'PostgreSQL (Relational Database) - Best for structured, queryable data',
                'strengths': [
                    '📊 Structured queries with JOINs and aggregations',
                    '🔒 ACID transactions ensure data consistency',
                    '📈 Vertical scaling for growing datasets',
                    '🔍 Complex filtering and indexing',
                    '📝 Schema validation prevents data errors'
                ],
                'ideal_for': [
                    'Consistent schema across records',
                    'Relational data with foreign keys',
                    'Complex analytical queries',
                    'Transactional workloads'
                ],
                'operations': {
                    'read_performance': 'Excellent with proper indexes',
                    'write_performance': 'Good for moderate volume',
                    'query_flexibility': 'Very high with SQL',
                    'scaling': 'Vertical (add more resources)'
                }
            },
            'nosql': {
                'summary': 'MongoDB (Document Database) - Best for flexible, nested data',
                'strengths': [
                    '🚀 Fast writes and horizontal scaling',
                    '📦 Flexible schema for evolving data',
                    '🌳 Natural storage for nested/hierarchical data',
                    '⚡ High-throughput operations',
                    '🌐 Distributed architecture support'
                ],
                'ideal_for': [
                    'Variable or evolving schemas',
                    'Deeply nested JSON structures',
                    'High-volume writes',
                    'Document-oriented data'
                ],
                'operations': {
                    'read_performance': 'Excellent for document retrieval',
                    'write_performance': 'Optimized for high throughput',
                    'query_flexibility': 'High with MongoDB queries',
                    'scaling': 'Horizontal (add more servers)'
                }
            }
        }

        explanation = explanations.get(db_type, explanations['nosql'])

        return {
            **explanation,
            'why_chosen': analysis.reasons,
            'confidence_level': f"{analysis.confidence * 100:.0f}%",
            'metrics': {
                'nesting_depth': analysis.metrics.get('max_depth', 0),
                'total_objects': analysis.metrics.get('total_objects', 0),
                'unique_fields': analysis.metrics.get('unique_fields', 0),
                'schema_consistency': 'High' if analysis.metrics.get('sql_score', 0) > analysis.metrics.get('nosql_score', 0) else 'Variable'
            }
        }

    def _generate_doc_id_from_timestamp(self) -> str:
        """Generate document ID from timestamp only (for streaming)"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
        return f"doc_{timestamp}"

    def _generate_doc_id(self, data: Any) -> str:
        """Generate unique document ID based on content hash"""
        content_str = json.dumps(data, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return f"doc_{timestamp}_{content_hash[:12]}"

    def _store_streaming_sql(self, items: List[Any], doc_id: str, admin_id: str,
                            analysis: AnalysisResult, tags: Optional[List[str]],
                            chunk_size: int) -> Dict[str, Any]:
        """
        Store streamed data in unified SQL table with batching
        """
        logger.info(f"Storing {len(items)} items in PostgreSQL with streaming")

        try:
            # Calculate total size
            data_json = json.dumps(items, ensure_ascii=False)
            file_size_bytes = len(data_json.encode('utf-8'))
            record_count = len(items)

            # Prepare metadata
            metadata = {
                'analysis': {
                    'confidence': analysis.confidence,
                    'reasons': analysis.reasons,
                    'metrics': analysis.metrics,
                    'schema_info': analysis.schema_info
                },
                'record_count': record_count,
                'file_size_bytes': file_size_bytes,
                'streaming': True
            }

            with connection.cursor() as cursor:
                # Insert into unified table
                insert_sql = """
                INSERT INTO json_documents (
                    doc_id, admin_id, document_name, tags, data, metadata,
                    file_size_bytes, record_count, is_compressed, compression_ratio,
                    database_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    data = EXCLUDED.data,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """

                cursor.execute(insert_sql, [
                    doc_id,
                    admin_id,
                    None,
                    tags or [],
                    data_json,  # Store as JSONB
                    json.dumps(metadata),
                    file_size_bytes,
                    record_count,
                    False,
                    None,
                    'sql'
                ])

            return {
                'table_name': 'json_documents',
                'database': 'postgresql',
                'indexed_fields': ['data (GIN)', 'doc_id', 'admin_id', 'search_vector'],
                'optimization': 'Streaming insert with unified table',
                'file_size_bytes': file_size_bytes,
                'record_count': record_count
            }

        except Exception as e:
            logger.error(f"Error in streaming SQL storage: {e}", exc_info=True)
            raise

    def _store_streaming_nosql(self, items: List[Any], doc_id: str, admin_id: str,
                               analysis: AnalysisResult, tags: Optional[List[str]],
                               chunk_size: int) -> Dict[str, Any]:
        """
        Store streamed data in MongoDB with batching
        """
        logger.info(f"Storing {len(items)} items in MongoDB with streaming")

        try:
            # Calculate file size
            data_json = json.dumps(items, ensure_ascii=False)
            file_size_bytes = len(data_json.encode('utf-8'))
            record_count = len(items)

            document = {
                'doc_id': doc_id,
                'admin_id': admin_id,
                'data': items,
                'database_type': 'nosql',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'tags': tags or [],
                'document_name': None,
                'file_size_bytes': file_size_bytes,
                'record_count': record_count,
                'is_compressed': False,
                'compression_ratio': None,
                'metadata': {
                    'analysis': {
                        'confidence': analysis.confidence,
                        'reasons': analysis.reasons,
                        'metrics': analysis.metrics,
                        'schema_info': analysis.schema_info
                    },
                    'streaming': True
                }
            }

            result = self.json_documents.insert_one(document)

            return {
                'collection': 'json_documents',
                'database': 'mongodb',
                'object_id': str(result.inserted_id),
                'indexed_fields': ['doc_id', 'admin_id', 'created_at', 'database_type', 'tags'],
                'optimization': 'Streaming insert with batching',
                'file_size_bytes': file_size_bytes,
                'record_count': record_count
            }

        except Exception as e:
            logger.error(f"Error in streaming NoSQL storage: {e}", exc_info=True)
            raise

    def _store_in_sql(self, data: Any, doc_id: str, admin_id: str,
                      analysis: AnalysisResult, tags: Optional[List[str]]) -> Dict[str, Any]:
        """
        Store data in PostgreSQL unified json_documents table

        Instead of creating separate tables, all JSON is stored in a single
        unified table with JSONB for efficient querying and indexing
        """
        logger.info(f"Storing {doc_id} in PostgreSQL unified table")

        try:
            # Calculate file size and record count
            data_json = json.dumps(data, ensure_ascii=False)
            file_size_bytes = len(data_json.encode('utf-8'))
            record_count = len(data) if isinstance(data, list) else 1

            with connection.cursor() as cursor:
                # Insert into unified json_documents table
                insert_sql = """
                INSERT INTO json_documents (
                    doc_id, admin_id, document_name, tags, data, metadata,
                    file_size_bytes, record_count, is_compressed, compression_ratio,
                    database_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (doc_id) DO UPDATE SET
                    data = EXCLUDED.data,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                """

                # Prepare metadata
                metadata = {
                    'analysis': {
                        'confidence': analysis.confidence,
                        'reasons': analysis.reasons,
                        'metrics': analysis.metrics,
                        'schema_info': analysis.schema_info
                    },
                    'record_count': record_count,
                    'file_size_bytes': file_size_bytes
                }

                cursor.execute(insert_sql, [
                    doc_id,
                    admin_id,
                    None,  # document_name (can be added later)
                    tags or [],
                    data_json,  # Store as JSONB
                    json.dumps(metadata),
                    file_size_bytes,
                    record_count,
                    False,  # is_compressed
                    None,  # compression_ratio
                    'sql'
                ])

            return {
                'table_name': 'json_documents',
                'database': 'postgresql',
                'indexed_fields': ['data (GIN)', 'doc_id', 'admin_id', 'search_vector'],
                'optimization': 'Unified table with JSONB and full-text search',
                'file_size_bytes': file_size_bytes,
                'record_count': record_count
            }

        except Exception as e:
            logger.error(f"Error storing in PostgreSQL: {e}", exc_info=True)
            raise Exception(f"PostgreSQL storage failed: {str(e)}. Check database connection and schema.")

    def _store_in_nosql(self, data: Any, doc_id: str, admin_id: str,
                        analysis: AnalysisResult, tags: Optional[List[str]]) -> Dict[str, Any]:
        """
        Store data in MongoDB with optimized structure
        """
        logger.info(f"Storing {doc_id} in MongoDB (NoSQL)")

        try:
            # Calculate file size and record count
            data_json = json.dumps(data, ensure_ascii=False)
            file_size_bytes = len(data_json.encode('utf-8'))
            record_count = len(data) if isinstance(data, list) else 1

            document = {
                'doc_id': doc_id,
                'admin_id': admin_id,
                'data': data,
                'database_type': 'nosql',
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'tags': tags or [],
                'document_name': None,
                'file_size_bytes': file_size_bytes,
                'record_count': record_count,
                'is_compressed': False,
                'compression_ratio': None,
                'metadata': {
                    'analysis': {
                        'confidence': analysis.confidence,
                        'reasons': analysis.reasons,
                        'metrics': analysis.metrics,
                        'schema_info': analysis.schema_info
                    }
                }
            }

            result = self.json_documents.insert_one(document)

            return {
                'collection': 'json_documents',
                'database': 'mongodb',
                'object_id': str(result.inserted_id),
                'indexed_fields': ['doc_id', 'admin_id', 'created_at', 'database_type', 'tags'],
                'optimization': 'Document storage with compound indexes',
                'file_size_bytes': file_size_bytes,
                'record_count': record_count
            }

        except Exception as e:
            logger.error(f"Error storing in NoSQL: {e}", exc_info=True)
            raise

    def _extract_schema(self, data: Any) -> Dict[str, Any]:
        """Extract detailed schema from JSON data for user reference"""
        def get_field_type(value):
            if isinstance(value, bool):
                return 'boolean'
            elif isinstance(value, int):
                return 'integer'
            elif isinstance(value, float):
                return 'number'
            elif isinstance(value, str):
                return 'string'
            elif isinstance(value, list):
                if value:
                    return f"array<{get_field_type(value[0])}>"
                return 'array'
            elif isinstance(value, dict):
                return 'object'
            elif value is None:
                return 'null'
            return 'unknown'

        def extract_from_dict(obj: dict, prefix='') -> dict:
            schema = {}
            for key, value in obj.items():
                full_key = f"{prefix}.{key}" if prefix else key

                if isinstance(value, dict):
                    schema[full_key] = {
                        'type': 'object',
                        'fields': extract_from_dict(value, full_key)
                    }
                elif isinstance(value, list) and value and isinstance(value[0], dict):
                    schema[full_key] = {
                        'type': 'array<object>',
                        'item_schema': extract_from_dict(value[0], f"{full_key}[]")
                    }
                else:
                    schema[full_key] = {
                        'type': get_field_type(value),
                        'sample': str(value)[:100] if value is not None else None
                    }
            return schema

        if isinstance(data, list):
            if data and isinstance(data[0], dict):
                # For arrays of objects, extract schema from first item
                return {
                    'type': 'array',
                    'item_count': len(data),
                    'item_schema': extract_from_dict(data[0])
                }
            else:
                return {
                    'type': 'array',
                    'item_count': len(data),
                    'item_type': get_field_type(data[0]) if data else 'unknown'
                }
        elif isinstance(data, dict):
            return {
                'type': 'object',
                'fields': extract_from_dict(data)
            }
        else:
            return {
                'type': get_field_type(data)
            }

    def _store_metadata(self, doc_id: str, analysis: AnalysisResult,
                       storage_result: Dict[str, Any], admin_id: str):
        """Store metadata about the document for tracking"""
        try:
            # Extract schema from the data
            schema_info = analysis.schema_info if hasattr(analysis, 'schema_info') else {}

            metadata = {
                'doc_id': doc_id,
                'admin_id': admin_id,
                'database_type': analysis.recommended_db,
                'confidence': analysis.confidence,
                'reasons': analysis.reasons,
                'metrics': analysis.metrics,
                'schema_info': schema_info,
                'storage_info': storage_result,
                'created_at': datetime.now()
            }

            self.metadata_collection.update_one(
                {'doc_id': doc_id},
                {'$set': metadata},
                upsert=True
            )
            logger.info(f"Metadata stored for {doc_id}")

        except Exception as e:
            logger.error(f"Error storing metadata: {e}")

    def retrieve(self, doc_id: str, admin_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by ID (admin-only access)

        Args:
            doc_id: Document ID
            admin_id: Admin user ID (for access control)

        Returns:
            Document data or None if not found/unauthorized
        """
        # Check metadata to determine database type
        metadata = self.metadata_collection.find_one({'doc_id': doc_id})

        if not metadata:
            logger.warning(f"Document {doc_id} not found")
            return None

        # Admin-only access control
        if metadata.get('admin_id') != admin_id:
            logger.warning(f"Unauthorized access attempt to {doc_id} by {admin_id}")
            return None

        db_type = metadata.get('database_type')

        try:
            if db_type == 'sql':
                return self._retrieve_from_sql(doc_id, metadata)
            else:
                return self._retrieve_from_nosql(doc_id)

        except Exception as e:
            logger.error(f"Error retrieving {doc_id}: {e}")
            return None

    def _retrieve_from_sql(self, doc_id: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve data from PostgreSQL unified json_documents table"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT data, tags, created_at, updated_at, file_size_bytes,
                           record_count, metadata, document_name
                    FROM json_documents
                    WHERE doc_id = %s
                """, [doc_id])

                row = cursor.fetchone()

                if not row:
                    return None

                # Parse the JSONB data
                data = json.loads(row[0]) if isinstance(row[0], str) else row[0]

                return {
                    'doc_id': doc_id,
                    'data': data,
                    'database_type': 'sql',
                    'tags': row[1],
                    'created_at': row[2].isoformat() if row[2] else None,
                    'updated_at': row[3].isoformat() if row[3] else None,
                    'file_size_bytes': row[4],
                    'record_count': row[5],
                    'document_name': row[7],
                    'metadata': json.loads(row[6]) if isinstance(row[6], str) else row[6]
                }

        except Exception as e:
            logger.error(f"Error retrieving from SQL: {e}", exc_info=True)
            return None

    def _retrieve_from_nosql(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve data from MongoDB"""
        try:
            document = self.json_documents.find_one({'doc_id': doc_id})

            if not document:
                return None

            # Remove MongoDB internal ID
            document.pop('_id', None)

            return {
                'doc_id': doc_id,
                'data': document.get('data'),
                'database_type': 'nosql',
                'metadata': {
                    'created_at': document.get('created_at'),
                    'tags': document.get('tags'),
                    'analysis': document.get('analysis')
                }
            }

        except Exception as e:
            logger.error(f"Error retrieving from NoSQL: {e}")
            return None

    def list_documents(self, admin_id: str, db_type: Optional[str] = None,
                      limit: int = 100) -> List[Dict[str, Any]]:
        """
        List all documents for an admin (admin-only)

        Args:
            admin_id: Admin user ID
            db_type: Filter by 'sql' or 'nosql' (optional)
            limit: Maximum number of results

        Returns:
            List of document metadata
        """
        query = {'admin_id': admin_id}
        if db_type:
            query['database_type'] = db_type

        try:
            documents = self.metadata_collection.find(query).sort('created_at', DESCENDING).limit(limit)

            results = []
            for doc in documents:
                doc.pop('_id', None)
                results.append(doc)

            return results

        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []

    def delete_document(self, doc_id: str, admin_id: str) -> bool:
        """
        Delete document (admin-only)

        Args:
            doc_id: Document ID
            admin_id: Admin user ID

        Returns:
            True if deleted, False otherwise
        """
        # Check access
        metadata = self.metadata_collection.find_one({'doc_id': doc_id})

        if not metadata or metadata.get('admin_id') != admin_id:
            logger.warning(f"Unauthorized delete attempt for {doc_id}")
            return False

        db_type = metadata.get('database_type')

        try:
            if db_type == 'sql':
                # Delete from unified json_documents table
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM json_documents WHERE doc_id = %s AND admin_id = %s",
                                 [doc_id, admin_id])
            else:
                # Delete from MongoDB
                self.json_documents.delete_one({'doc_id': doc_id, 'admin_id': admin_id})

            # Delete metadata
            self.metadata_collection.delete_one({'doc_id': doc_id})

            logger.info(f"Document {doc_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Error deleting {doc_id}: {e}", exc_info=True)
            return False


# Global router instance
_router_instance = None


def get_db_router() -> SmartDatabaseRouter:
    """Get singleton database router instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = SmartDatabaseRouter()
    return _router_instance
