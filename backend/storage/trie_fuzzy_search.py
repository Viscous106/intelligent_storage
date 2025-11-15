"""
Trie-based Adaptive Fuzzy Search Algorithm
Professional, market-ready implementation for intelligent file search.

Features:
- Trie data structure for efficient prefix matching
- Levenshtein distance for fuzzy matching
- User behavior learning and adaptation
- Semantic understanding
- Advanced filtering capabilities
"""

import re
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TrieNode:
    """Node in the Trie data structure."""

    def __init__(self):
        self.children = {}
        self.is_end_of_word = False
        self.file_references = []  # Files that match this prefix
        self.frequency = 0  # How often this path is traversed


class AdaptiveTrieFuzzySearch:
    """
    Market-ready Trie-based fuzzy search with machine learning adaptation.

    This implementation provides:
    1. O(m) prefix search where m is query length
    2. Fuzzy matching with configurable edit distance
    3. User behavior tracking for personalization
    4. Semantic keyword expansion
    5. Advanced filtering (@type:, @size:, @date:)
    """

    def __init__(self):
        self.root = TrieNode()
        self.files_index = {}  # file_id -> file_data
        self.user_interactions = defaultdict(lambda: {
            'view_count': 0,
            'download_count': 0,
            'search_selections': 0,
            'last_accessed': None,
            'search_queries': []
        })
        self.search_history = []
        self.semantic_map = self._build_semantic_map()

    def _build_semantic_map(self) -> Dict[str, List[str]]:
        """Build semantic keyword mappings for intelligent search."""
        return {
            # Images - map to 'image' type
            'photo': ['image'],
            'photos': ['image'],
            'picture': ['image'],
            'pictures': ['image'],
            'img': ['image'],
            'screenshot': ['image'],
            'screenshots': ['image'],

            # Videos - map to 'video' type
            'video': ['video'],
            'videos': ['video'],
            'movie': ['video'],
            'movies': ['video'],
            'film': ['video'],
            'clip': ['video'],
            'clips': ['video'],

            # Audio - map to 'audio' type
            'audio': ['audio'],
            'music': ['audio'],
            'song': ['audio'],
            'songs': ['audio'],
            'track': ['audio'],
            'podcast': ['audio'],
            'podcasts': ['audio'],
            'sound': ['audio'],

            # Documents - map to 'document' type
            'document': ['document'],
            'documents': ['document'],
            'doc': ['document'],
            'docs': ['document'],
            'pdf': ['document'],
            'pdfs': ['document'],
            'text': ['document'],
            'report': ['document'],
            'reports': ['document'],
            'spreadsheet': ['document'],
            'spreadsheets': ['document'],
            'presentation': ['document'],
            'presentations': ['document'],

            # Code - map to 'code' type
            'code': ['code'],
            'script': ['code'],
            'scripts': ['code'],
            'program': ['code'],
            'source': ['code'],

            # Archives - map to 'compressed' type
            'archive': ['compressed'],
            'archives': ['compressed'],
            'zip': ['compressed'],
            'compressed': ['compressed'],
        }

    def insert_word(self, word: str, file_id: int):
        """Insert a word into the Trie with file reference."""
        word = word.lower()
        node = self.root

        for char in word:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
            node.frequency += 1
            if file_id not in node.file_references:
                node.file_references.append(file_id)

        node.is_end_of_word = True

    def index_file(self, file_data: Dict[str, Any]):
        """
        Index a file for searching.

        Args:
            file_data: Dictionary containing file information
                {
                    'id': int,
                    'name': str,
                    'type': str,
                    'size': int,
                    'uploaded_at': str/datetime,
                    'tags': List[str],
                    'extension': str,
                    'metadata': dict
                }
        """
        file_id = file_data['id']
        self.files_index[file_id] = file_data

        # Index filename
        filename = file_data.get('name', '')
        words = re.findall(r'\w+', filename.lower())
        for word in words:
            self.insert_word(word, file_id)

        # Index full filename
        self.insert_word(filename.lower().replace(' ', ''), file_id)

        # Index file type
        if file_data.get('type'):
            self.insert_word(file_data['type'].lower(), file_id)

        # Index extension
        if file_data.get('extension'):
            self.insert_word(file_data['extension'].lower().replace('.', ''), file_id)

        # Index tags
        for tag in file_data.get('tags', []):
            self.insert_word(tag.lower(), file_id)

    def levenshtein_distance(self, s1: str, s2: str, max_distance: int = 3) -> int:
        """
        Calculate Levenshtein distance with early termination.

        Args:
            s1: First string
            s2: Second string
            max_distance: Maximum acceptable distance (early termination optimization)

        Returns:
            Edit distance or max_distance + 1 if too far
        """
        if abs(len(s1) - len(s2)) > max_distance:
            return max_distance + 1

        if len(s1) < len(s2):
            s1, s2 = s2, s1

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)

        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            min_in_row = i + 1

            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)

                current_value = min(insertions, deletions, substitutions)
                current_row.append(current_value)
                min_in_row = min(min_in_row, current_value)

            # Early termination
            if min_in_row > max_distance:
                return max_distance + 1

            previous_row = current_row

        return previous_row[-1]

    def fuzzy_search_trie(self, prefix: str, max_distance: int = 2) -> List[int]:
        """
        Fuzzy search using Trie with Levenshtein distance.

        Args:
            prefix: Search query
            max_distance: Maximum edit distance allowed

        Returns:
            List of file IDs matching the fuzzy search
        """
        prefix = prefix.lower()
        results = set()

        def dfs(node: TrieNode, current_word: str, distance: int):
            """Depth-first search with fuzzy matching."""
            if distance > max_distance:
                return

            # Calculate distance to prefix
            curr_distance = self.levenshtein_distance(current_word, prefix[:len(current_word)], max_distance)

            # If current word matches within threshold
            if len(current_word) >= len(prefix) and curr_distance <= max_distance:
                results.update(node.file_references)

            # Continue searching if there's potential for matches
            if curr_distance <= max_distance or len(current_word) < len(prefix):
                for char, child_node in node.children.items():
                    dfs(child_node, current_word + char, curr_distance)

        dfs(self.root, '', 0)
        return list(results)

    def exact_prefix_search(self, prefix: str) -> List[int]:
        """Fast exact prefix search using Trie."""
        prefix = prefix.lower()
        node = self.root

        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]

        # Collect all files under this prefix
        results = set()

        def collect_files(n: TrieNode):
            results.update(n.file_references)
            for child in n.children.values():
                collect_files(child)

        collect_files(node)
        return list(results)

    def semantic_expand_query(self, query: str) -> List[str]:
        """Expand query with semantic keywords."""
        query_lower = query.lower()
        expanded = [query_lower]

        if query_lower in self.semantic_map:
            expanded.extend(self.semantic_map[query_lower])

        return expanded

    def parse_advanced_filters(self, query: str) -> Dict[str, Any]:
        """
        Parse advanced search filters.

        Supports:
        - @type:image
        - @size:>1mb
        - @date:>2024-01-01
        - @ext:pdf
        """
        filters = {
            'type': None,
            'size_min': None,
            'size_max': None,
            'date_from': None,
            'date_to': None,
            'extension': None,
            'search_terms': []
        }

        # Extract @type: filter
        type_match = re.search(r'@type:(\w+)', query, re.IGNORECASE)
        if type_match:
            filters['type'] = type_match.group(1).lower()
            query = query.replace(type_match.group(0), '').strip()

        # Extract @ext: filter
        ext_match = re.search(r'@ext:(\w+)', query, re.IGNORECASE)
        if ext_match:
            filters['extension'] = ext_match.group(1).lower()
            query = query.replace(ext_match.group(0), '').strip()

        # Extract @size: filter
        size_match = re.search(r'@size:([><])?(\d+\.?\d*)(kb|mb|gb)?', query, re.IGNORECASE)
        if size_match:
            operator = size_match.group(1) or '>'
            size = float(size_match.group(2))
            unit = (size_match.group(3) or 'kb').lower()

            # Convert to bytes
            multipliers = {'kb': 1024, 'mb': 1024**2, 'gb': 1024**3}
            size_bytes = size * multipliers.get(unit, 1024)

            if operator == '>':
                filters['size_min'] = size_bytes
            else:
                filters['size_max'] = size_bytes

            query = query.replace(size_match.group(0), '').strip()

        # Extract @date: filter
        date_match = re.search(r'@date:([><])?(\d{4}-\d{2}-\d{2})', query, re.IGNORECASE)
        if date_match:
            operator = date_match.group(1) or '>'
            date_str = date_match.group(2)
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')

            if operator == '>':
                filters['date_from'] = date_obj
            else:
                filters['date_to'] = date_obj

            query = query.replace(date_match.group(0), '').strip()

        # Remaining text is search terms
        filters['search_terms'] = [term for term in query.split() if term]

        return filters

    def apply_filters(self, file_id: int, filters: Dict[str, Any]) -> bool:
        """Check if file matches the given filters."""
        file_data = self.files_index.get(file_id)
        if not file_data:
            return False

        # Type filter
        if filters['type'] and file_data.get('type', '').lower() != filters['type']:
            return False

        # Extension filter
        if filters['extension']:
            file_ext = file_data.get('extension', '').lower().replace('.', '')
            if file_ext != filters['extension']:
                return False

        # Size filters
        file_size = file_data.get('size', 0)
        if filters['size_min'] is not None and file_size < filters['size_min']:
            return False
        if filters['size_max'] is not None and file_size > filters['size_max']:
            return False

        # Date filters
        if filters['date_from'] or filters['date_to']:
            uploaded_at = file_data.get('uploaded_at')
            if isinstance(uploaded_at, str):
                try:
                    uploaded_at = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00'))
                except:
                    uploaded_at = None

            if uploaded_at:
                if filters['date_from'] and uploaded_at < filters['date_from']:
                    return False
                if filters['date_to'] and uploaded_at > filters['date_to']:
                    return False

        return True

    def calculate_score(self, file_id: int, query: str, match_type: str) -> float:
        """
        Calculate relevance score for a file.

        Factors:
        - Match type (exact > prefix > fuzzy > semantic)
        - User interaction history
        - File popularity
        - Recency
        """
        file_data = self.files_index.get(file_id)
        if not file_data:
            return 0.0

        score = 0.0

        # Base score by match type
        match_scores = {
            'exact': 100,
            'prefix': 80,
            'fuzzy': 60,
            'semantic': 40
        }
        score += match_scores.get(match_type, 30)

        # Filename match bonus
        filename = file_data.get('name', '').lower()
        query_lower = query.lower()

        if query_lower == filename:
            score += 50
        elif filename.startswith(query_lower):
            score += 30
        elif query_lower in filename:
            score += 20

        # User interaction boost
        interactions = self.user_interactions.get(file_id, {})
        score += interactions.get('view_count', 0) * 2
        score += interactions.get('download_count', 0) * 5
        score += interactions.get('search_selections', 0) * 10

        # Recency boost
        last_accessed = interactions.get('last_accessed')
        if last_accessed:
            days_since = (datetime.now() - last_accessed).days
            if days_since < 7:
                score += (7 - days_since) * 3

        # Query history boost
        if query_lower in interactions.get('search_queries', []):
            score += 15

        return score

    def search(self, query: str, limit: int = 50, use_fuzzy: bool = True) -> List[Dict[str, Any]]:
        """
        Perform adaptive fuzzy search.

        Args:
            query: Search query (supports advanced filters)
            limit: Maximum number of results
            use_fuzzy: Enable fuzzy matching

        Returns:
            List of ranked search results with scores
        """
        if not query or not query.strip():
            return []

        # Parse filters
        filters = self.parse_advanced_filters(query)
        search_terms = ' '.join(filters['search_terms'])

        # Track search
        self.search_history.append({
            'query': query,
            'timestamp': datetime.now()
        })

        # If search term is a semantic keyword (like "photo", "photos"), convert to type filter
        if search_terms and not filters['type']:
            search_lower = search_terms.lower()
            if search_lower in self.semantic_map:
                # This is a semantic type query (e.g., "photos")
                semantic_types = self.semantic_map[search_lower]
                if semantic_types:
                    filters['type'] = semantic_types[0]  # Use the mapped type
                    search_terms = ''  # Don't search for the word itself

        # Collect matching file IDs with their match types
        matches = {}  # file_id -> match_type

        if search_terms:
            # Expand query semantically for additional matching
            expanded_queries = self.semantic_expand_query(search_terms)

            for expanded_query in expanded_queries:
                match_type = 'exact' if expanded_query == search_terms else 'semantic'

                # Try exact prefix match first (fastest)
                exact_matches = self.exact_prefix_search(expanded_query)
                for file_id in exact_matches:
                    if file_id not in matches:
                        matches[file_id] = match_type

                # Fuzzy search if enabled
                if use_fuzzy:
                    fuzzy_matches = self.fuzzy_search_trie(expanded_query, max_distance=2)
                    for file_id in fuzzy_matches:
                        if file_id not in matches:
                            matches[file_id] = 'fuzzy'
        else:
            # Only filters, no search terms - return all files
            matches = {file_id: 'filter' for file_id in self.files_index.keys()}

        # Apply filters
        filtered_matches = {
            file_id: match_type
            for file_id, match_type in matches.items()
            if self.apply_filters(file_id, filters)
        }

        # Calculate scores and rank
        scored_results = []
        for file_id, match_type in filtered_matches.items():
            score = self.calculate_score(file_id, search_terms, match_type)
            file_data = self.files_index[file_id].copy()
            file_data['search_score'] = score
            file_data['match_type'] = match_type
            scored_results.append(file_data)

        # Sort by score
        scored_results.sort(key=lambda x: x['search_score'], reverse=True)

        return scored_results[:limit]

    def record_interaction(self, file_id: int, interaction_type: str, query: Optional[str] = None):
        """
        Record user interaction for learning.

        Args:
            file_id: File that was interacted with
            interaction_type: 'view', 'download', 'select'
            query: Search query that led to this interaction
        """
        interactions = self.user_interactions[file_id]

        if interaction_type == 'view':
            interactions['view_count'] += 1
        elif interaction_type == 'download':
            interactions['download_count'] += 1
        elif interaction_type == 'select':
            interactions['search_selections'] += 1

        interactions['last_accessed'] = datetime.now()

        if query and query.lower() not in interactions['search_queries']:
            interactions['search_queries'].append(query.lower())

    def get_stats(self) -> Dict[str, Any]:
        """Get search engine statistics."""
        return {
            'total_files_indexed': len(self.files_index),
            'total_searches': len(self.search_history),
            'unique_files_with_interactions': len(self.user_interactions),
            'trie_depth': self._get_trie_depth(self.root),
        }

    def _get_trie_depth(self, node: TrieNode, current_depth: int = 0) -> int:
        """Calculate maximum depth of Trie."""
        if not node.children:
            return current_depth
        return max(self._get_trie_depth(child, current_depth + 1)
                  for child in node.children.values())


# Global instance for the application
trie_search_engine = AdaptiveTrieFuzzySearch()
