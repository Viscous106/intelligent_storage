"""
Advanced Query Builder for JSON Data
Supports filtering, range queries, pagination, and search across SQL and NoSQL
"""

import json
import base64
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class QueryBuilder:
    """
    Builds optimized queries for both PostgreSQL (JSONB) and MongoDB
    """

    def __init__(self, database_type='sql'):
        """
        Initialize query builder

        Args:
            database_type: 'sql' or 'nosql'
        """
        self.database_type = database_type
        self.filters = {}
        self.sort_fields = []
        self.limit_value = 100
        self.offset_value = 0
        self.cursor_data = None
        self.select_fields = []

    def add_filter(self, field: str, value: Any, operator: str = 'eq') -> 'QueryBuilder':
        """
        Add a filter condition

        Args:
            field: Field name (supports dot notation for nested fields)
            value: Filter value
            operator: 'eq', 'gt', 'gte', 'lt', 'lte', 'in', 'contains', 'between'

        Returns:
            self for chaining
        """
        if field not in self.filters:
            self.filters[field] = []

        self.filters[field].append({
            'operator': operator,
            'value': value
        })

        return self

    def add_filters_from_dict(self, filter_dict: Dict) -> 'QueryBuilder':
        """
        Add filters from a dictionary (API request format)

        Format:
        {
            "data.age": {"$gt": 25, "$lt": 65},
            "data.status": "active",
            "data.created_at": {"$gte": "2024-01-01"},
            "tags": {"$contains": "important"}
        }
        """
        for field, value in filter_dict.items():
            if isinstance(value, dict):
                # Operator-based filters
                for op_key, op_value in value.items():
                    operator_map = {
                        '$eq': 'eq',
                        '$gt': 'gt',
                        '$gte': 'gte',
                        '$lt': 'lt',
                        '$lte': 'lte',
                        '$in': 'in',
                        '$contains': 'contains',
                        '$between': 'between',
                        '$regex': 'regex',
                        '$exists': 'exists'
                    }
                    operator = operator_map.get(op_key, 'eq')
                    self.add_filter(field, op_value, operator)
            else:
                # Simple equality filter
                self.add_filter(field, value, 'eq')

        return self

    def add_sort(self, field: str, order: str = 'asc') -> 'QueryBuilder':
        """
        Add sort field

        Args:
            field: Field name to sort by
            order: 'asc' or 'desc'
        """
        self.sort_fields.append({
            'field': field,
            'order': order.lower()
        })
        return self

    def set_limit(self, limit: int) -> 'QueryBuilder':
        """Set result limit"""
        self.limit_value = min(limit, 1000)  # Max 1000 per request
        return self

    def set_offset(self, offset: int) -> 'QueryBuilder':
        """Set result offset"""
        self.offset_value = offset
        return self

    def set_cursor(self, cursor: str) -> 'QueryBuilder':
        """
        Set cursor for cursor-based pagination

        Args:
            cursor: Base64 encoded cursor string
        """
        if cursor:
            try:
                decoded = base64.b64decode(cursor).decode('utf-8')
                self.cursor_data = json.loads(decoded)
            except Exception as e:
                logger.error(f"Invalid cursor: {e}")
                self.cursor_data = None
        return self

    def select_fields(self, fields: List[str]) -> 'QueryBuilder':
        """
        Select specific fields to return

        Args:
            fields: List of field names (e.g., ['data.name', 'data.email'])
        """
        self.select_fields = fields
        return self

    def build_sql_query(self, admin_id: str) -> Tuple[str, List]:
        """
        Build PostgreSQL query with JSONB operators

        Returns:
            (query_string, parameters_list)
        """
        conditions = ["admin_id = %s"]
        params = [admin_id]

        # Add filters
        for field, filter_list in self.filters.items():
            for filter_item in filter_list:
                operator = filter_item['operator']
                value = filter_item['value']

                if field.startswith('data.'):
                    # JSONB field
                    json_path = field.replace('data.', '')

                    if operator == 'eq':
                        conditions.append(f"data->>'{json_path}' = %s")
                        params.append(str(value))

                    elif operator == 'gt':
                        conditions.append(f"(data->>'{json_path}')::numeric > %s")
                        params.append(float(value))

                    elif operator == 'gte':
                        # Try numeric first, fall back to timestamp
                        if isinstance(value, (int, float)):
                            conditions.append(f"(data->>'{json_path}')::numeric >= %s")
                            params.append(float(value))
                        else:
                            conditions.append(f"(data->>'{json_path}')::timestamp >= %s")
                            params.append(value)

                    elif operator == 'lt':
                        conditions.append(f"(data->>'{json_path}')::numeric < %s")
                        params.append(float(value))

                    elif operator == 'lte':
                        if isinstance(value, (int, float)):
                            conditions.append(f"(data->>'{json_path}')::numeric <= %s")
                            params.append(float(value))
                        else:
                            conditions.append(f"(data->>'{json_path}')::timestamp <= %s")
                            params.append(value)

                    elif operator == 'in':
                        placeholders = ', '.join(['%s'] * len(value))
                        conditions.append(f"data->>'{json_path}' IN ({placeholders})")
                        params.extend([str(v) for v in value])

                    elif operator == 'contains':
                        # Use JSONB containment operator
                        conditions.append("data @> %s::jsonb")
                        params.append(json.dumps({json_path: value}))

                    elif operator == 'between':
                        conditions.append(f"(data->>'{json_path}')::numeric BETWEEN %s AND %s")
                        params.extend([float(value[0]), float(value[1])])

                    elif operator == 'regex':
                        conditions.append(f"data->>'{json_path}' ~* %s")
                        params.append(value)

                elif field == 'tags':
                    if operator == 'contains':
                        conditions.append("%s = ANY(tags)")
                        params.append(value)
                    elif operator == 'in':
                        conditions.append("tags && %s")
                        params.append(value)

                else:
                    # Regular column
                    if operator == 'eq':
                        conditions.append(f"{field} = %s")
                        params.append(value)
                    elif operator in ['gt', 'gte', 'lt', 'lte']:
                        op_symbol = {'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<='}[operator]
                        conditions.append(f"{field} {op_symbol} %s")
                        params.append(value)

        # Add cursor condition
        if self.cursor_data:
            conditions.append("id > %s")
            params.append(self.cursor_data.get('last_id', 0))

        # Build WHERE clause
        where_clause = " AND ".join(conditions)

        # Build ORDER BY clause
        if self.sort_fields:
            order_parts = []
            for sort in self.sort_fields:
                field = sort['field']
                order = 'DESC' if sort['order'] == 'desc' else 'ASC'

                if field.startswith('data.'):
                    json_path = field.replace('data.', '')
                    order_parts.append(f"data->>'{json_path}' {order}")
                else:
                    order_parts.append(f"{field} {order}")
            order_clause = ", ".join(order_parts)
        else:
            order_clause = "created_at DESC"

        # Build SELECT clause
        if self.select_fields:
            select_parts = ['id', 'doc_id']
            for field in self.select_fields:
                if field.startswith('data.'):
                    json_path = field.replace('data.', '')
                    select_parts.append(f"data->>'{json_path}' as \"{field}\"")
                else:
                    select_parts.append(field)
            select_clause = ", ".join(select_parts)
        else:
            select_clause = "*"

        # Build complete query
        query = f"""
        SELECT {select_clause}
        FROM json_documents
        WHERE {where_clause}
        ORDER BY {order_clause}
        LIMIT %s OFFSET %s
        """

        params.extend([self.limit_value, self.offset_value])

        return query, params

    def build_count_query(self, admin_id: str) -> Tuple[str, List]:
        """
        Build count query for pagination

        Returns:
            (count_query, parameters)
        """
        conditions = ["admin_id = %s"]
        params = [admin_id]

        # Add same filters as main query (without cursor)
        for field, filter_list in self.filters.items():
            for filter_item in filter_list:
                operator = filter_item['operator']
                value = filter_item['value']

                if field.startswith('data.'):
                    json_path = field.replace('data.', '')

                    if operator == 'eq':
                        conditions.append(f"data->>'{json_path}' = %s")
                        params.append(str(value))
                    elif operator == 'gt':
                        conditions.append(f"(data->>'{json_path}')::numeric > %s")
                        params.append(float(value))
                    # ... (similar to build_sql_query)

        where_clause = " AND ".join(conditions)

        query = f"SELECT COUNT(*) FROM json_documents WHERE {where_clause}"

        return query, params

    def build_mongodb_query(self, admin_id: str) -> Tuple[Dict, Dict]:
        """
        Build MongoDB query

        Returns:
            (filter_dict, options_dict)
        """
        query = {'admin_id': admin_id}

        # Add filters
        for field, filter_list in self.filters.items():
            for filter_item in filter_list:
                operator = filter_item['operator']
                value = filter_item['value']

                operator_map = {
                    'eq': None,  # Direct equality
                    'gt': '$gt',
                    'gte': '$gte',
                    'lt': '$lt',
                    'lte': '$lte',
                    'in': '$in',
                    'contains': '$regex',
                    'exists': '$exists'
                }

                if operator == 'eq':
                    query[field] = value
                elif operator in operator_map:
                    if field not in query:
                        query[field] = {}
                    query[field][operator_map[operator]] = value
                elif operator == 'between':
                    query[field] = {
                        '$gte': value[0],
                        '$lte': value[1]
                    }

        # Add cursor condition
        if self.cursor_data:
            query['_id'] = {'$gt': self.cursor_data.get('last_id')}

        # Build options
        options = {
            'limit': self.limit_value,
            'skip': self.offset_value if not self.cursor_data else 0
        }

        # Add sort
        if self.sort_fields:
            sort_list = []
            for sort in self.sort_fields:
                direction = -1 if sort['order'] == 'desc' else 1
                sort_list.append((sort['field'], direction))
            options['sort'] = sort_list
        else:
            options['sort'] = [('created_at', -1)]

        # Add projection
        if self.select_fields:
            projection = {field: 1 for field in self.select_fields}
            projection['_id'] = 1
            projection['doc_id'] = 1
            options['projection'] = projection

        return query, options

    @staticmethod
    def create_cursor(last_id: int) -> str:
        """
        Create base64 encoded cursor

        Args:
            last_id: ID of last item in current page

        Returns:
            Base64 encoded cursor string
        """
        cursor_data = {'last_id': last_id}
        cursor_json = json.dumps(cursor_data)
        cursor_b64 = base64.b64encode(cursor_json.encode()).decode()
        return cursor_b64

    @staticmethod
    def create_pagination_response(
        total: int,
        page: int,
        page_size: int,
        has_next: bool = False,
        cursor: str = None
    ) -> Dict:
        """
        Create standardized pagination metadata

        Returns:
            Pagination metadata dict
        """
        total_pages = math.ceil(total / page_size) if page_size > 0 else 0

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'has_next': has_next or (page < total_pages),
            'has_prev': page > 1,
            'next_cursor': cursor if cursor else None
        }


# Convenience functions
def parse_query_params(request_data: Dict) -> QueryBuilder:
    """
    Parse API request into QueryBuilder

    Expected format:
    {
        "filter": {
            "data.age": {"$gt": 25},
            "data.status": "active"
        },
        "sort": [
            {"field": "data.created_at", "order": "desc"}
        ],
        "pagination": {
            "page": 1,
            "page_size": 50
        } or {
            "cursor": "eyJsYXN0X2lkIjoxMjN9",
            "limit": 50
        },
        "fields": ["data.name", "data.email"]
    }
    """
    builder = QueryBuilder()

    # Add filters
    if 'filter' in request_data:
        builder.add_filters_from_dict(request_data['filter'])

    # Add sorting
    if 'sort' in request_data:
        for sort_item in request_data['sort']:
            builder.add_sort(
                sort_item.get('field', 'created_at'),
                sort_item.get('order', 'desc')
            )

    # Add pagination
    if 'pagination' in request_data:
        pagination = request_data['pagination']

        if 'cursor' in pagination:
            # Cursor-based pagination
            builder.set_cursor(pagination['cursor'])
            builder.set_limit(pagination.get('limit', 50))
        else:
            # Offset-based pagination
            page = pagination.get('page', 1)
            page_size = pagination.get('page_size', 50)
            builder.set_limit(page_size)
            builder.set_offset((page - 1) * page_size)
    else:
        # Default pagination
        builder.set_limit(50)
        builder.set_offset(0)

    # Add field selection
    if 'fields' in request_data:
        builder.select_fields(request_data['fields'])

    return builder
