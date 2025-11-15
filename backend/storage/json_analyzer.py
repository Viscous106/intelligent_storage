"""
JSON Structure Analyzer for SQL vs NoSQL Database Selection

This module analyzes JSON data structure and determines the optimal database type
(SQL or NoSQL) based on multiple factors including schema consistency, nesting depth,
data relationships, and query patterns.
"""

import json
from typing import Dict, List, Any, Tuple, Set
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class AnalysisResult:
    """Results from JSON analysis with decision metrics"""
    recommended_db: str  # 'sql' or 'nosql'
    confidence: float  # 0.0 to 1.0
    reasons: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    schema_info: Dict[str, Any] = field(default_factory=dict)


class JSONAnalyzer:
    """
    Analyzes JSON structure to determine optimal database type (SQL vs NoSQL)

    Decision Criteria:
    1. Schema Consistency: Uniform structure → SQL, Varied → NoSQL
    2. Nesting Depth: Flat (≤2 levels) → SQL, Deep (>2 levels) → NoSQL
    3. Data Relationships: Relational → SQL, Hierarchical/Embedded → NoSQL
    4. Array Complexity: Simple arrays → SQL, Complex nested arrays → NoSQL
    5. Field Variability: Consistent fields → SQL, Variable fields → NoSQL
    6. Data Size: Small-medium → SQL, Large/scalable → NoSQL
    """

    def __init__(self):
        self.reset_metrics()

    def reset_metrics(self):
        """Reset analysis metrics"""
        self.max_depth = 0
        self.total_objects = 0
        self.field_occurrences = defaultdict(int)
        self.field_types = defaultdict(set)
        self.array_depths = []
        self.has_nested_arrays = False
        self.has_mixed_types = False
        self.total_fields = 0

    def analyze(self, data: Any) -> AnalysisResult:
        """
        Main analysis method - determines SQL vs NoSQL

        Args:
            data: JSON data (dict, list, or primitive)

        Returns:
            AnalysisResult with recommendation and detailed reasoning
        """
        self.reset_metrics()

        # Handle different input types
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return AnalysisResult(
                    recommended_db='nosql',
                    confidence=0.5,
                    reasons=['Invalid JSON - defaulting to NoSQL for flexibility']
                )

        # Analyze structure
        self._analyze_structure(data, depth=0)

        # Calculate decision scores
        sql_score = 0.0
        nosql_score = 0.0
        reasons = []

        # 1. Schema Consistency Analysis
        schema_score, schema_reason = self._analyze_schema_consistency()
        if schema_score > 0:
            sql_score += schema_score
            reasons.append(f"✓ SQL: {schema_reason}")
        else:
            nosql_score += abs(schema_score)
            reasons.append(f"✓ NoSQL: {schema_reason}")

        # 2. Nesting Depth Analysis
        depth_score, depth_reason = self._analyze_nesting_depth()
        if depth_score > 0:
            sql_score += depth_score
            reasons.append(f"✓ SQL: {depth_reason}")
        else:
            nosql_score += abs(depth_score)
            reasons.append(f"✓ NoSQL: {depth_reason}")

        # 3. Array Complexity Analysis
        array_score, array_reason = self._analyze_array_complexity()
        if array_score > 0:
            sql_score += array_score
            reasons.append(f"✓ SQL: {array_reason}")
        else:
            nosql_score += abs(array_score)
            reasons.append(f"✓ NoSQL: {array_reason}")

        # 4. Field Variability Analysis
        field_score, field_reason = self._analyze_field_variability()
        if field_score > 0:
            sql_score += field_score
            reasons.append(f"✓ SQL: {field_reason}")
        else:
            nosql_score += abs(field_score)
            reasons.append(f"✓ NoSQL: {field_reason}")

        # 5. Data Type Consistency
        type_score, type_reason = self._analyze_type_consistency()
        if type_score > 0:
            sql_score += type_score
            reasons.append(f"✓ SQL: {type_reason}")
        else:
            nosql_score += abs(type_score)
            reasons.append(f"✓ NoSQL: {type_reason}")

        # 6. Data Volume and Scaling Considerations
        volume_score, volume_reason = self._analyze_data_volume()
        if volume_score > 0:
            sql_score += volume_score
            reasons.append(f"✓ SQL: {volume_reason}")
        else:
            nosql_score += abs(volume_score)
            reasons.append(f"✓ NoSQL: {volume_reason}")

        # 7. Relationship Patterns
        relationship_score, relationship_reason = self._analyze_relationships()
        if relationship_score > 0:
            sql_score += relationship_score
            reasons.append(f"✓ SQL: {relationship_reason}")
        else:
            nosql_score += abs(relationship_score)
            reasons.append(f"✓ NoSQL: {relationship_reason}")

        # Determine recommendation
        total_score = sql_score + nosql_score
        if total_score == 0:
            total_score = 1.0  # Prevent division by zero

        if sql_score > nosql_score:
            recommended_db = 'sql'
            confidence = sql_score / total_score
        else:
            recommended_db = 'nosql'
            confidence = nosql_score / total_score

        # Build metrics summary
        metrics = {
            'max_depth': self.max_depth,
            'total_objects': self.total_objects,
            'unique_fields': len(self.field_occurrences),
            'total_fields': self.total_fields,
            'has_nested_arrays': self.has_nested_arrays,
            'has_mixed_types': self.has_mixed_types,
            'sql_score': round(sql_score, 2),
            'nosql_score': round(nosql_score, 2),
        }

        # Schema information for database creation
        schema_info = self._generate_schema_info()

        return AnalysisResult(
            recommended_db=recommended_db,
            confidence=round(confidence, 2),
            reasons=reasons,
            metrics=metrics,
            schema_info=schema_info
        )

    def _analyze_structure(self, data: Any, depth: int = 0):
        """Recursively analyze JSON structure"""
        self.max_depth = max(self.max_depth, depth)

        if isinstance(data, dict):
            self.total_objects += 1
            self.total_fields += len(data)

            for key, value in data.items():
                self.field_occurrences[key] += 1
                value_type = type(value).__name__
                self.field_types[key].add(value_type)

                # Check for mixed types
                if len(self.field_types[key]) > 1:
                    self.has_mixed_types = True

                # Recurse
                self._analyze_structure(value, depth + 1)

        elif isinstance(data, list):
            self.array_depths.append(depth)

            # Check for nested arrays
            for item in data:
                if isinstance(item, (list, dict)):
                    if isinstance(item, list):
                        self.has_nested_arrays = True
                self._analyze_structure(item, depth + 1)

    def _analyze_schema_consistency(self) -> Tuple[float, str]:
        """
        Analyze schema consistency across objects
        Returns: (score, reason) - positive for SQL, negative for NoSQL
        """
        if self.total_objects == 0:
            return (-2.0, "No objects found - NoSQL better for unstructured data")

        # Check field consistency
        if self.total_objects > 1:
            avg_occurrences = sum(self.field_occurrences.values()) / len(self.field_occurrences)
            consistency_ratio = avg_occurrences / self.total_objects

            if consistency_ratio > 0.9:
                return (3.0, f"Highly consistent schema ({consistency_ratio:.0%} field consistency)")
            elif consistency_ratio > 0.7:
                return (1.5, f"Moderately consistent schema ({consistency_ratio:.0%} consistency)")
            else:
                return (-2.5, f"Variable schema ({consistency_ratio:.0%} consistency)")

        return (1.0, "Single object - schema consistency assumed")

    def _analyze_nesting_depth(self) -> Tuple[float, str]:
        """
        Analyze nesting depth
        Returns: (score, reason) - positive for SQL, negative for NoSQL
        """
        if self.max_depth <= 2:
            return (2.5, f"Shallow nesting (depth={self.max_depth}) - suitable for relational tables")
        elif self.max_depth <= 4:
            return (-1.0, f"Moderate nesting (depth={self.max_depth}) - better as documents")
        else:
            return (-3.0, f"Deep nesting (depth={self.max_depth}) - optimal for document storage")

    def _analyze_array_complexity(self) -> Tuple[float, str]:
        """
        Analyze array complexity
        Returns: (score, reason) - positive for SQL, negative for NoSQL
        """
        if not self.array_depths:
            return (1.5, "No arrays - simple relational structure")

        if self.has_nested_arrays:
            return (-2.5, "Complex nested arrays - better suited for document storage")

        avg_array_depth = sum(self.array_depths) / len(self.array_depths)
        if avg_array_depth <= 1:
            return (1.0, "Simple arrays at top level - can normalize to SQL tables")
        else:
            return (-1.5, "Arrays at deeper levels - document storage more natural")

    def _analyze_field_variability(self) -> Tuple[float, str]:
        """
        Analyze field name variability
        Returns: (score, reason) - positive for SQL, negative for NoSQL
        """
        if self.total_objects == 0:
            return (0.0, "No objects to analyze")

        # Calculate how many fields appear in all objects
        consistent_fields = sum(1 for count in self.field_occurrences.values()
                               if count == self.total_objects)
        total_unique_fields = len(self.field_occurrences)

        if total_unique_fields == 0:
            return (0.0, "No fields found")

        consistency_rate = consistent_fields / total_unique_fields

        if consistency_rate > 0.8:
            return (2.0, f"{consistent_fields}/{total_unique_fields} fields always present - fixed schema works well")
        elif consistency_rate > 0.5:
            return (0.5, f"{consistent_fields}/{total_unique_fields} fields consistent - borderline case")
        else:
            return (-2.0, f"Only {consistent_fields}/{total_unique_fields} fields consistent - flexible schema needed")

    def _analyze_type_consistency(self) -> Tuple[float, str]:
        """
        Analyze data type consistency for fields
        Returns: (score, reason) - positive for SQL, negative for NoSQL
        """
        if not self.field_types:
            return (0.0, "No fields to analyze")

        mixed_type_fields = sum(1 for types in self.field_types.values() if len(types) > 1)
        total_fields = len(self.field_types)

        if mixed_type_fields == 0:
            return (2.0, "All fields have consistent types - strong typing possible")
        elif mixed_type_fields / total_fields < 0.2:
            return (0.5, f"Mostly consistent types ({mixed_type_fields}/{total_fields} fields vary)")
        else:
            return (-1.5, f"Inconsistent types ({mixed_type_fields}/{total_fields} fields vary) - flexible schema needed")

    def _analyze_data_volume(self) -> Tuple[float, str]:
        """
        Analyze data volume for scaling considerations
        Returns: (score, reason) - positive for SQL, negative for NoSQL
        """
        if self.total_objects == 0:
            return (0.0, "No data to analyze volume")

        if self.total_objects < 1000:
            return (1.0, f"Small dataset ({self.total_objects} records) - vertical scaling in SQL works well")
        elif self.total_objects < 100000:
            return (0.0, f"Medium dataset ({self.total_objects} records) - both SQL and NoSQL suitable")
        else:
            return (-1.5, f"Large dataset ({self.total_objects}+ records) - NoSQL horizontal scaling beneficial")

    def _analyze_relationships(self) -> Tuple[float, str]:
        """
        Analyze potential relationships and foreign key patterns
        Returns: (score, reason) - positive for SQL, negative for NoSQL
        """
        # Look for common foreign key patterns like 'id', 'user_id', etc.
        fk_patterns = ['_id', 'Id']
        id_fields = [field for field in self.field_occurrences.keys()
                     if any(pattern in field for pattern in fk_patterns)]

        if not id_fields:
            return (-0.5, "No obvious relationship fields - document storage acceptable")

        # Check for multiple ID fields (suggesting relationships)
        if len(id_fields) > 2:
            return (2.0, f"Multiple ID fields ({', '.join(id_fields[:3])}) suggest relational data")
        elif len(id_fields) > 0:
            return (0.5, f"Some ID fields present ({', '.join(id_fields)}) - mild relational tendency")

        return (0.0, "No clear relationship pattern")

    def _generate_schema_info(self) -> Dict[str, Any]:
        """Generate schema information for database creation"""
        fields = {}

        for field_name, types in self.field_types.items():
            occurrence_rate = self.field_occurrences[field_name] / max(self.total_objects, 1)

            # Determine primary type
            primary_type = list(types)[0] if len(types) == 1 else 'mixed'

            fields[field_name] = {
                'types': list(types),
                'primary_type': primary_type,
                'occurrence_rate': round(occurrence_rate, 2),
                'required': occurrence_rate > 0.9
            }

        return {
            'fields': fields,
            'estimated_objects': self.total_objects,
            'max_nesting_depth': self.max_depth,
            'has_arrays': len(self.array_depths) > 0
        }


def analyze_json_for_database(json_data: Any) -> AnalysisResult:
    """
    Convenience function to analyze JSON and get database recommendation

    Args:
        json_data: JSON data (string, dict, or list)

    Returns:
        AnalysisResult with recommendation and reasoning
    """
    analyzer = JSONAnalyzer()
    return analyzer.analyze(json_data)


# Example usage and testing
if __name__ == '__main__':
    # Test case 1: Flat, consistent structure (SQL)
    sql_data = [
        {"id": 1, "name": "Alice", "age": 30, "email": "alice@example.com"},
        {"id": 2, "name": "Bob", "age": 25, "email": "bob@example.com"},
        {"id": 3, "name": "Charlie", "age": 35, "email": "charlie@example.com"}
    ]

    # Test case 2: Deep nesting, variable structure (NoSQL)
    nosql_data = {
        "user": {
            "profile": {
                "personal": {
                    "name": "Alice",
                    "contacts": [
                        {"type": "email", "value": "alice@example.com"},
                        {"type": "phone", "value": "+1234567890", "verified": True}
                    ]
                },
                "preferences": {
                    "theme": "dark",
                    "notifications": {"email": True, "sms": False}
                }
            },
            "activity": [
                {"date": "2024-01-01", "events": [{"type": "login", "ip": "192.168.1.1"}]}
            ]
        }
    }

    print("=" * 80)
    print("SQL-Friendly Data Analysis:")
    print("=" * 80)
    result1 = analyze_json_for_database(sql_data)
    print(f"Recommendation: {result1.recommended_db.upper()}")
    print(f"Confidence: {result1.confidence * 100:.0f}%")
    print(f"\nReasons:")
    for reason in result1.reasons:
        print(f"  {reason}")
    print(f"\nMetrics: {result1.metrics}")

    print("\n" + "=" * 80)
    print("NoSQL-Friendly Data Analysis:")
    print("=" * 80)
    result2 = analyze_json_for_database(nosql_data)
    print(f"Recommendation: {result2.recommended_db.upper()}")
    print(f"Confidence: {result2.confidence * 100:.0f}%")
    print(f"\nReasons:")
    for reason in result2.reasons:
        print(f"  {reason}")
    print(f"\nMetrics: {result2.metrics}")
