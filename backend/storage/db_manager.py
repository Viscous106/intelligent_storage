"""
Intelligent database manager that handles both SQL and NoSQL storage.
Automatically creates schemas and manages data storage.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from django.db import connection
from django.conf import settings
from pymongo import MongoClient
from datetime import datetime

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages both PostgreSQL and MongoDB storage with intelligent schema creation.
    """

    def __init__(self):
        """Initialize database connections."""
        self.mongo_client = None
        self.mongo_db = None
        self._init_mongo()

    def _init_mongo(self):
        """Initialize MongoDB connection."""
        try:
            mongo_settings = settings.MONGODB_SETTINGS
            connection_string = (
                f"mongodb://{mongo_settings['USER']}:{mongo_settings['PASSWORD']}"
                f"@{mongo_settings['HOST']}:{mongo_settings['PORT']}/"
            )
            self.mongo_client = MongoClient(connection_string)
            self.mongo_db = self.mongo_client[mongo_settings['DB']]
            logger.info("MongoDB connection established")
        except Exception as e:
            logger.error(f"MongoDB connection failed: {str(e)}")
            self.mongo_db = None

    def store_json_data(self, data: Dict or List, db_type: str,
                       collection_name: str = None,
                       table_name: str = None,
                       user_comment: str = None) -> Dict:
        """
        Store JSON data in the appropriate database.

        Args:
            data: JSON data to store
            db_type: 'SQL' or 'NoSQL'
            collection_name: Name for MongoDB collection (if NoSQL)
            table_name: Name for PostgreSQL table (if SQL)
            user_comment: Optional user context

        Returns:
            Dict with storage results
        """
        if db_type == 'NoSQL':
            return self._store_in_mongodb(data, collection_name)
        else:
            return self._store_in_postgresql(data, table_name, user_comment)

    def _store_in_mongodb(self, data: Dict or List,
                         collection_name: str = None) -> Dict:
        """
        Store data in MongoDB.

        Args:
            data: Data to store
            collection_name: Collection name (auto-generated if None)

        Returns:
            Storage result dict
        """
        if self.mongo_db is None:
            return {
                'success': False,
                'error': 'MongoDB not available'
            }

        try:
            # Generate collection name if not provided
            if not collection_name:
                collection_name = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            collection = self.mongo_db[collection_name]

            # Generate schema representation
            sample = data[0] if isinstance(data, list) and data else data
            mongo_schema = self._generate_mongo_schema(sample)

            # Insert data
            if isinstance(data, list):
                result = collection.insert_many(data)
                inserted_count = len(result.inserted_ids)
            else:
                result = collection.insert_one(data)
                inserted_count = 1

            return {
                'success': True,
                'database_type': 'MongoDB',
                'collection': collection_name,
                'mongo_schema': mongo_schema,
                'inserted_count': inserted_count,
                'message': f"Successfully stored {inserted_count} document(s) in MongoDB"
            }

        except Exception as e:
            logger.error(f"MongoDB storage failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_mongo_schema(self, sample_data: Dict) -> str:
        """
        Generate a MongoDB schema representation.

        Args:
            sample_data: Sample document

        Returns:
            String representation of the schema
        """
        def get_type(value):
            if isinstance(value, bool):
                return 'Boolean'
            elif isinstance(value, int):
                return 'Number (Int)'
            elif isinstance(value, float):
                return 'Number (Float)'
            elif isinstance(value, str):
                return 'String'
            elif isinstance(value, list):
                if value:
                    return f'Array<{get_type(value[0])}>'
                return 'Array'
            elif isinstance(value, dict):
                return 'Object'
            else:
                return 'Mixed'

        schema_lines = ['{']
        for key, value in sample_data.items():
            type_str = get_type(value)
            schema_lines.append(f'    {key}: {type_str},')
        schema_lines.append('}')

        return '\n'.join(schema_lines)

    def _store_in_postgresql(self, data: Dict or List,
                            table_name: str = None,
                            user_comment: str = None) -> Dict:
        """
        Store data in PostgreSQL with automatic schema creation.

        Args:
            data: Data to store
            table_name: Table name (auto-generated if None)
            user_comment: Optional context for schema generation

        Returns:
            Storage result dict
        """
        try:
            # Generate table name if not provided
            if not table_name:
                table_name = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Sanitize table name
            table_name = self._sanitize_table_name(table_name)

            # Ensure data is a list
            data_list = data if isinstance(data, list) else [data]

            if not data_list:
                return {
                    'success': False,
                    'error': 'No data to store'
                }

            # Generate schema from data
            schema = self._generate_sql_schema(data_list[0])

            # Create table and get SQL statement
            create_sql = self._create_table(table_name, schema)

            # Insert data
            inserted_count = self._insert_data(table_name, schema, data_list)

            return {
                'success': True,
                'database_type': 'PostgreSQL',
                'table': table_name,
                'schema': schema,
                'sql_schema': create_sql,
                'inserted_count': inserted_count,
                'message': f"Successfully stored {inserted_count} row(s) in PostgreSQL"
            }

        except Exception as e:
            logger.error(f"PostgreSQL storage failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _generate_sql_schema(self, sample_data: Dict) -> Dict[str, str]:
        """
        Generate SQL schema from sample data.

        Args:
            sample_data: Sample data object

        Returns:
            Dict mapping field names to SQL types
        """
        schema = {}

        for key, value in sample_data.items():
            sanitized_key = self._sanitize_column_name(key)

            if value is None:
                schema[sanitized_key] = 'TEXT'
            elif isinstance(value, bool):
                schema[sanitized_key] = 'BOOLEAN'
            elif isinstance(value, int):
                schema[sanitized_key] = 'INTEGER'
            elif isinstance(value, float):
                schema[sanitized_key] = 'REAL'
            elif isinstance(value, str):
                # Determine if it's a long text or regular varchar
                max_len = len(value)
                if max_len > 255:
                    schema[sanitized_key] = 'TEXT'
                else:
                    schema[sanitized_key] = 'VARCHAR(255)'
            elif isinstance(value, (dict, list)):
                # Store complex types as JSONB
                schema[sanitized_key] = 'JSONB'
            else:
                schema[sanitized_key] = 'TEXT'

        return schema

    def _create_table(self, table_name: str, schema: Dict[str, str]) -> str:
        """
        Create PostgreSQL table with given schema.

        Args:
            table_name: Name of the table
            schema: Dict mapping column names to SQL types

        Returns:
            The CREATE TABLE SQL statement
        """
        # Build CREATE TABLE statement
        columns = ['id SERIAL PRIMARY KEY']
        for col_name, col_type in schema.items():
            columns.append(f"{col_name} {col_type}")

        # Add metadata columns
        columns.append('created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

        # Join columns with newlines (can't use \n in f-string)
        columns_str = ',\n    '.join(columns)
        create_sql = f"""CREATE TABLE IF NOT EXISTS {table_name} (
    {columns_str}
);"""

        with connection.cursor() as cursor:
            cursor.execute(create_sql)

        logger.info(f"Table '{table_name}' created successfully")
        return create_sql

    def _insert_data(self, table_name: str, schema: Dict[str, str],
                    data_list: List[Dict]) -> int:
        """
        Insert data into PostgreSQL table.

        Args:
            table_name: Table name
            schema: Table schema
            data_list: List of data objects to insert

        Returns:
            Number of rows inserted
        """
        if not data_list:
            return 0

        columns = list(schema.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        columns_str = ', '.join(columns)

        insert_sql = f"""
        INSERT INTO {table_name} ({columns_str})
        VALUES ({placeholders})
        """

        inserted_count = 0
        with connection.cursor() as cursor:
            for data_obj in data_list:
                values = []
                for col in columns:
                    # Find original key (case-insensitive)
                    original_key = self._find_original_key(col, data_obj)
                    value = data_obj.get(original_key)

                    # Convert complex types to JSON string
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)

                    values.append(value)

                cursor.execute(insert_sql, values)
                inserted_count += 1

        return inserted_count

    def _sanitize_table_name(self, name: str) -> str:
        """Sanitize table name for SQL."""
        import re
        # Remove special characters, replace spaces with underscores
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)
        # Ensure it starts with a letter
        if not name[0].isalpha():
            name = 'table_' + name
        return name.lower()[:63]  # PostgreSQL max identifier length

    def _sanitize_column_name(self, name: str) -> str:
        """Sanitize column name for SQL."""
        import re
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '_', name)
        if not name[0].isalpha():
            name = 'col_' + name
        return name.lower()[:63]

    def _find_original_key(self, sanitized_key: str, data_obj: Dict) -> str:
        """Find original key in data object matching sanitized key."""
        for key in data_obj.keys():
            if self._sanitize_column_name(key) == sanitized_key:
                return key
        return sanitized_key

    def get_collection_list(self) -> List[str]:
        """Get list of all MongoDB collections."""
        if self.mongo_db is None:
            return []
        return self.mongo_db.list_collection_names()

    def get_table_list(self) -> List[str]:
        """Get list of all PostgreSQL tables."""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """)
            return [row[0] for row in cursor.fetchall()]

    def query_mongodb(self, collection_name: str,
                     query: Dict = None, limit: int = 100) -> List[Dict]:
        """
        Query MongoDB collection.

        Args:
            collection_name: Collection to query
            query: MongoDB query filter
            limit: Maximum documents to return

        Returns:
            List of documents
        """
        if self.mongo_db is None:
            return []

        try:
            collection = self.mongo_db[collection_name]
            query = query or {}
            results = list(collection.find(query).limit(limit))

            # Convert ObjectId to string for JSON serialization
            for doc in results:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])

            return results
        except Exception as e:
            logger.error(f"MongoDB query failed: {str(e)}")
            return []

    def query_postgresql(self, table_name: str, limit: int = 100) -> List[Dict]:
        """
        Query PostgreSQL table.

        Args:
            table_name: Table to query
            limit: Maximum rows to return

        Returns:
            List of row dicts
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT %s", [limit])
                columns = [col[0] for col in cursor.description]
                return [
                    dict(zip(columns, row))
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"PostgreSQL query failed: {str(e)}")
            return []


# Singleton instance
db_manager = DatabaseManager()
