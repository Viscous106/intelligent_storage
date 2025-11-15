"""
Advanced JSON Query Views
Provides filtering, pagination, search, and aggregation for JSON data
"""

import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from pymongo import MongoClient
from bson import ObjectId
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from .admin_auth import require_admin
from .query_builder import QueryBuilder, parse_query_params

logger = logging.getLogger(__name__)


# Database connections
def get_pg_connection():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        dbname=settings.DATABASES['default']['NAME'],
        user=settings.DATABASES['default']['USER'],
        password=settings.DATABASES['default']['PASSWORD'],
        host=settings.DATABASES['default']['HOST'],
        port=settings.DATABASES['default']['PORT']
    )


def get_mongo_client():
    """Get MongoDB client"""
    mongo_settings = settings.MONGODB_SETTINGS
    return MongoClient(
        host=mongo_settings['HOST'],
        port=mongo_settings['PORT'],
        username=mongo_settings.get('USER'),
        password=mongo_settings.get('PASSWORD')
    )


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def advanced_query_json(request):
    """
    Advanced JSON query with filtering, pagination, and sorting

    POST /api/smart/query/json
    Header: Authorization: Bearer <token>

    Body:
    {
        "filter": {
            "data.age": {"$gt": 25, "$lt": 65},
            "data.status": "active",
            "data.created_at": {"$gte": "2024-01-01"},
            "tags": {"$contains": "important"}
        },
        "sort": [
            {"field": "data.created_at", "order": "desc"},
            {"field": "data.name", "order": "asc"}
        ],
        "pagination": {
            "page": 1,
            "page_size": 50
        },
        "fields": ["data.name", "data.age", "data.email"],
        "database_type": "sql"  // optional: "sql" or "nosql"
    }

    Response:
    {
        "success": true,
        "data": [...],
        "pagination": {
            "total": 500,
            "page": 1,
            "page_size": 50,
            "total_pages": 10,
            "has_next": true,
            "has_prev": false
        },
        "query_time_ms": 45
    }
    """
    try:
        import time
        start_time = time.time()

        admin_id = request.admin_id
        request_data = json.loads(request.body)

        # Determine database type
        db_type = request_data.get('database_type', 'sql')

        # Parse query parameters
        builder = parse_query_params(request_data)

        if db_type == 'sql':
            # Query PostgreSQL
            result = _query_postgresql(builder, admin_id)
        else:
            # Query MongoDB
            result = _query_mongodb(builder, admin_id)

        # Calculate query time
        query_time = int((time.time() - start_time) * 1000)

        return JsonResponse({
            'success': True,
            'data': result['data'],
            'pagination': result['pagination'],
            'query_time_ms': query_time
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _query_postgresql(builder: QueryBuilder, admin_id: str) -> dict:
    """
    Execute PostgreSQL query with pagination

    Returns:
        {
            'data': [...],
            'pagination': {...}
        }
    """
    conn = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build query
        query, params = builder.build_sql_query(admin_id)
        count_query, count_params = builder.build_count_query(admin_id)

        # Get total count
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()['count']

        # Execute main query
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to list of dicts
        data = []
        for row in rows:
            item = dict(row)
            # Parse JSONB if present
            if 'data' in item and isinstance(item['data'], str):
                item['data'] = json.loads(item['data'])
            data.append(item)

        # Create pagination metadata
        page = (builder.offset_value // builder.limit_value) + 1 if builder.limit_value > 0 else 1
        pagination = QueryBuilder.create_pagination_response(
            total=total,
            page=page,
            page_size=builder.limit_value,
            has_next=builder.offset_value + builder.limit_value < total
        )

        # Generate cursor for cursor-based pagination
        if data and builder.cursor_data is not None:
            last_item = data[-1]
            next_cursor = QueryBuilder.create_cursor(last_item['id'])
            pagination['next_cursor'] = next_cursor

        return {
            'data': data,
            'pagination': pagination
        }

    finally:
        if conn:
            conn.close()


def _query_mongodb(builder: QueryBuilder, admin_id: str) -> dict:
    """
    Execute MongoDB query with pagination

    Returns:
        {
            'data': [...],
            'pagination': {...}
        }
    """
    client = None
    try:
        client = get_mongo_client()
        db = client[settings.MONGODB_SETTINGS['DB']]
        collection = db['json_documents']

        # Build query
        query, options = builder.build_mongodb_query(admin_id)

        # Get total count
        total = collection.count_documents(query)

        # Execute query
        cursor = collection.find(query, **options)
        data = []

        for doc in cursor:
            # Convert ObjectId to string
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])
            data.append(doc)

        # Create pagination metadata
        page = (options['skip'] // builder.limit_value) + 1 if builder.limit_value > 0 else 1
        pagination = QueryBuilder.create_pagination_response(
            total=total,
            page=page,
            page_size=builder.limit_value,
            has_next=options['skip'] + builder.limit_value < total
        )

        # Generate cursor for cursor-based pagination
        if data and builder.cursor_data is not None:
            last_item = data[-1]
            next_cursor = QueryBuilder.create_cursor(str(last_item.get('_id', '')))
            pagination['next_cursor'] = next_cursor

        return {
            'data': data,
            'pagination': pagination
        }

    finally:
        if client:
            client.close()


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def search_json(request):
    """
    Full-text search across JSON data

    POST /api/smart/search/json
    Header: Authorization: Bearer <token>

    Body:
    {
        "query": "john smith",
        "filters": {
            "data.department": "engineering",
            "tags": {"$contains": "employee"}
        },
        "limit": 20,
        "database_type": "sql"  // optional
    }

    Response:
    {
        "success": true,
        "results": [
            {
                "doc_id": "doc_123",
                "data": {...},
                "score": 0.95,
                "highlight": "...John Smith..."
            }
        ],
        "total": 5,
        "query_time_ms": 23
    }
    """
    try:
        import time
        start_time = time.time()

        admin_id = request.admin_id
        request_data = json.loads(request.body)

        query_text = request_data.get('query', '')
        filters = request_data.get('filters', {})
        limit = min(request_data.get('limit', 20), 100)
        db_type = request_data.get('database_type', 'sql')

        if not query_text:
            return JsonResponse({
                'success': False,
                'error': 'Query text required'
            }, status=400)

        if db_type == 'sql':
            results = _search_postgresql(query_text, filters, admin_id, limit)
        else:
            results = _search_mongodb(query_text, filters, admin_id, limit)

        query_time = int((time.time() - start_time) * 1000)

        return JsonResponse({
            'success': True,
            'results': results,
            'total': len(results),
            'query_time_ms': query_time
        })

    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _search_postgresql(query_text: str, filters: dict, admin_id: str, limit: int) -> list:
    """
    Full-text search in PostgreSQL using tsvector

    Args:
        query_text: Search query
        filters: Additional filters
        admin_id: Admin ID
        limit: Result limit

    Returns:
        List of search results with scores
    """
    conn = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build filter conditions
        conditions = ["admin_id = %s"]
        params = [admin_id]

        # Add custom filters
        for field, value in filters.items():
            if field.startswith('data.'):
                json_path = field.replace('data.', '')
                if isinstance(value, dict) and '$contains' in value:
                    conditions.append("data @> %s::jsonb")
                    params.append(json.dumps({json_path: value['$contains']}))
                else:
                    conditions.append(f"data->>'{json_path}' = %s")
                    params.append(str(value))
            elif field == 'tags' and isinstance(value, dict) and '$contains' in value:
                conditions.append("%s = ANY(tags)")
                params.append(value['$contains'])

        where_clause = " AND ".join(conditions)

        # Full-text search query
        query = f"""
        SELECT
            doc_id,
            data,
            tags,
            created_at,
            ts_rank(search_vector, query) as score,
            ts_headline('english', data::text, query,
                'MaxWords=35, MinWords=15, ShortWord=3,
                 HighlightAll=FALSE, MaxFragments=3') as highlight
        FROM json_documents,
             to_tsquery('english', %s) query
        WHERE {where_clause}
          AND search_vector @@ query
        ORDER BY score DESC
        LIMIT %s
        """

        # Convert query text to tsquery format
        tsquery = ' & '.join(query_text.split())
        params.extend([tsquery, limit])

        cursor.execute(query, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            result = dict(row)
            # Parse JSONB
            if isinstance(result['data'], str):
                result['data'] = json.loads(result['data'])
            results.append(result)

        return results

    finally:
        if conn:
            conn.close()


def _search_mongodb(query_text: str, filters: dict, admin_id: str, limit: int) -> list:
    """
    Full-text search in MongoDB

    Args:
        query_text: Search query
        filters: Additional filters
        admin_id: Admin ID
        limit: Result limit

    Returns:
        List of search results with scores
    """
    client = None
    try:
        client = get_mongo_client()
        db = client[settings.MONGODB_SETTINGS['DB']]
        collection = db['json_documents']

        # Build query
        query = {
            'admin_id': admin_id,
            '$text': {'$search': query_text}
        }

        # Add filters
        for field, value in filters.items():
            if isinstance(value, dict) and '$contains' in value:
                query[field] = {'$regex': value['$contains'], '$options': 'i'}
            else:
                query[field] = value

        # Execute search
        cursor = collection.find(
            query,
            {'score': {'$meta': 'textScore'}}
        ).sort([
            ('score', {'$meta': 'textScore'})
        ]).limit(limit)

        results = []
        for doc in cursor:
            # Convert ObjectId to string
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])

            # MongoDB doesn't provide highlights, but we can add the score
            doc['highlight'] = f"Score: {doc.get('score', 0):.2f}"
            results.append(doc)

        return results

    finally:
        if client:
            client.close()


@csrf_exempt
@require_http_methods(["POST"])
@require_admin
def aggregate_json(request):
    """
    Aggregate JSON data

    POST /api/smart/aggregate/json
    Header: Authorization: Bearer <token>

    Body:
    {
        "operation": "count" | "sum" | "avg" | "min" | "max",
        "field": "data.age",  // for sum/avg/min/max
        "group_by": "data.department",  // optional
        "filters": {...},  // optional
        "database_type": "sql"  // optional
    }

    Response:
    {
        "success": true,
        "result": {
            "engineering": 150,
            "sales": 75,
            "marketing": 50
        }
    }
    """
    try:
        admin_id = request.admin_id
        request_data = json.loads(request.body)

        operation = request_data.get('operation', 'count')
        field = request_data.get('field')
        group_by = request_data.get('group_by')
        filters = request_data.get('filters', {})
        db_type = request_data.get('database_type', 'sql')

        if operation in ['sum', 'avg', 'min', 'max'] and not field:
            return JsonResponse({
                'success': False,
                'error': f'{operation} operation requires a field'
            }, status=400)

        if db_type == 'sql':
            result = _aggregate_postgresql(operation, field, group_by, filters, admin_id)
        else:
            result = _aggregate_mongodb(operation, field, group_by, filters, admin_id)

        return JsonResponse({
            'success': True,
            'operation': operation,
            'result': result
        })

    except Exception as e:
        logger.error(f"Aggregation error: {e}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def _aggregate_postgresql(operation: str, field: str, group_by: str, filters: dict, admin_id: str) -> dict:
    """PostgreSQL aggregation"""
    conn = None
    try:
        conn = get_pg_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Build base conditions
        conditions = ["admin_id = %s"]
        params = [admin_id]

        # Add filters
        for filter_field, value in filters.items():
            if filter_field.startswith('data.'):
                json_path = filter_field.replace('data.', '')
                conditions.append(f"data->>'{json_path}' = %s")
                params.append(str(value))

        where_clause = " AND ".join(conditions)

        # Build aggregation query
        if group_by:
            # Group by aggregation
            group_path = group_by.replace('data.', '')

            if operation == 'count':
                agg_expression = "COUNT(*)"
            elif operation in ['sum', 'avg', 'min', 'max']:
                field_path = field.replace('data.', '')
                agg_expression = f"{operation.upper()}((data->>'{field_path}')::numeric)"

            query = f"""
            SELECT
                data->>'{group_path}' as group_key,
                {agg_expression} as value
            FROM json_documents
            WHERE {where_clause}
            GROUP BY data->>'{group_path}'
            ORDER BY value DESC
            """
        else:
            # Simple aggregation
            if operation == 'count':
                query = f"SELECT COUNT(*) as value FROM json_documents WHERE {where_clause}"
            else:
                field_path = field.replace('data.', '')
                query = f"""
                SELECT {operation.upper()}((data->>'{field_path}')::numeric) as value
                FROM json_documents
                WHERE {where_clause}
                """

        cursor.execute(query, params)

        if group_by:
            rows = cursor.fetchall()
            return {row['group_key']: float(row['value']) for row in rows}
        else:
            row = cursor.fetchone()
            return {'value': float(row['value']) if row['value'] else 0}

    finally:
        if conn:
            conn.close()


def _aggregate_mongodb(operation: str, field: str, group_by: str, filters: dict, admin_id: str) -> dict:
    """MongoDB aggregation using aggregation pipeline"""
    client = None
    try:
        client = get_mongo_client()
        db = client[settings.MONGODB_SETTINGS['DB']]
        collection = db['json_documents']

        # Build pipeline
        pipeline = [
            {'$match': {'admin_id': admin_id}}
        ]

        # Add filters
        if filters:
            for filter_field, value in filters.items():
                pipeline[0]['$match'][filter_field] = value

        # Add group stage
        if group_by:
            if operation == 'count':
                group_stage = {
                    '$group': {
                        '_id': f'${group_by}',
                        'value': {'$sum': 1}
                    }
                }
            else:
                op_map = {'sum': '$sum', 'avg': '$avg', 'min': '$min', 'max': '$max'}
                group_stage = {
                    '$group': {
                        '_id': f'${group_by}',
                        'value': {op_map[operation]: f'${field}'}
                    }
                }

            pipeline.append(group_stage)
            pipeline.append({'$sort': {'value': -1}})

            results = list(collection.aggregate(pipeline))
            return {item['_id']: item['value'] for item in results}
        else:
            # Simple aggregation
            if operation == 'count':
                return {'value': collection.count_documents(pipeline[0]['$match'])}
            else:
                op_map = {'sum': '$sum', 'avg': '$avg', 'min': '$min', 'max': '$max'}
                pipeline.append({
                    '$group': {
                        '_id': None,
                        'value': {op_map[operation]: f'${field}'}
                    }
                })

                results = list(collection.aggregate(pipeline))
                return {'value': results[0]['value'] if results else 0}

    finally:
        if client:
            client.close()
