"""
Intelligent Search Suggestion System

Combines multiple strategies for smart search suggestions:
1. Search history tracking - Learns from user behavior
2. Smart caching - Fast repeated searches with popularity scoring
3. AI-powered semantic suggestions - Understanding intent
4. Context-aware suggestions - Based on file types and patterns
5. Trending searches - Popular recent queries
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class IntelligentSearchSuggestions:
    """
    Advanced search suggestion engine combining history, cache, and AI
    """

    def __init__(self, storage_path: str = None):
        # Storage paths
        self.storage_path = Path(storage_path) if storage_path else Path('search_suggestions_data')
        self.storage_path.mkdir(exist_ok=True)

        self.history_file = self.storage_path / 'search_history.json'
        self.cache_file = self.storage_path / 'search_cache.json'
        self.trends_file = self.storage_path / 'trending_searches.json'

        # In-memory data structures
        self.search_history = []  # List of {query, timestamp, admin_id, results_count, clicked_file}
        self.search_cache = {}  # {query: {results, timestamp, hit_count, avg_click_position}}
        self.trending_searches = {}  # {query: {count, last_searched, users}}
        self.user_preferences = defaultdict(lambda: {'frequent_terms': Counter(), 'file_types': Counter()})

        # Configuration
        self.max_history_size = 1000
        self.max_cache_size = 200
        self.cache_ttl = 3600  # 1 hour
        self.trending_window = 86400  # 24 hours

        # Load existing data
        self.load_data()

    def load_data(self):
        """Load history and cache from disk"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    self.search_history = json.load(f)

            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    self.search_cache = json.load(f)

            if self.trends_file.exists():
                with open(self.trends_file, 'r') as f:
                    self.trending_searches = json.load(f)

            # Build user preferences from history
            self._rebuild_user_preferences()

            logger.info(f"Loaded {len(self.search_history)} history items, "
                       f"{len(self.search_cache)} cached queries")
        except Exception as e:
            logger.error(f"Error loading search data: {e}")

    def save_data(self):
        """Save history and cache to disk"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.search_history[-self.max_history_size:], f, indent=2)

            with open(self.cache_file, 'w') as f:
                json.dump(self.search_cache, f, indent=2)

            with open(self.trends_file, 'w') as f:
                json.dump(self.trending_searches, f, indent=2)

            logger.info("Search data saved successfully")
        except Exception as e:
            logger.error(f"Error saving search data: {e}")

    def _rebuild_user_preferences(self):
        """Rebuild user preferences from history"""
        for entry in self.search_history:
            admin_id = entry.get('admin_id')
            query = entry.get('query', '').lower()

            # Track search terms
            words = query.split()
            for word in words:
                if len(word) > 2:  # Skip very short words
                    self.user_preferences[admin_id]['frequent_terms'][word] += 1

    def record_search(self, query: str, admin_id: str, results_count: int = 0,
                     results: List[Dict] = None, clicked_file: str = None):
        """
        Record a search query for learning

        Args:
            query: Search query string
            admin_id: User identifier
            results_count: Number of results returned
            results: Actual search results
            clicked_file: File clicked from results (if any)
        """
        timestamp = time.time()
        query_lower = query.lower().strip()

        # Add to history
        history_entry = {
            'query': query,
            'query_lower': query_lower,
            'timestamp': timestamp,
            'admin_id': admin_id,
            'results_count': results_count,
            'clicked_file': clicked_file
        }
        self.search_history.append(history_entry)

        # Update cache
        if query_lower not in self.search_cache:
            self.search_cache[query_lower] = {
                'query': query,
                'results': results or [],
                'timestamp': timestamp,
                'hit_count': 1,
                'last_accessed': timestamp,
                'click_positions': []
            }
        else:
            self.search_cache[query_lower]['hit_count'] += 1
            self.search_cache[query_lower]['last_accessed'] = timestamp

        # Update trending
        if query_lower not in self.trending_searches:
            self.trending_searches[query_lower] = {
                'query': query,
                'count': 1,
                'last_searched': timestamp,
                'users': {admin_id}
            }
        else:
            self.trending_searches[query_lower]['count'] += 1
            self.trending_searches[query_lower]['last_searched'] = timestamp
            if isinstance(self.trending_searches[query_lower]['users'], list):
                self.trending_searches[query_lower]['users'] = set(self.trending_searches[query_lower]['users'])
            self.trending_searches[query_lower]['users'].add(admin_id)

        # Update user preferences
        words = query_lower.split()
        for word in words:
            if len(word) > 2:
                self.user_preferences[admin_id]['frequent_terms'][word] += 1

        # Trim history if too large
        if len(self.search_history) > self.max_history_size:
            self.search_history = self.search_history[-self.max_history_size:]

        # Clean old cache entries
        self._clean_cache()

        # Auto-save periodically
        if len(self.search_history) % 10 == 0:
            self.save_data()

    def record_click(self, query: str, clicked_file: str, position: int):
        """Record when user clicks a search result"""
        query_lower = query.lower().strip()

        if query_lower in self.search_cache:
            self.search_cache[query_lower]['click_positions'].append(position)

    def get_suggestions(self, partial_query: str, admin_id: str, limit: int = 10) -> List[Dict]:
        """
        Get intelligent search suggestions

        Combines:
        - Recent searches (user's own history)
        - Cached popular searches
        - Trending searches
        - AI-powered semantic suggestions
        - Context-aware file type suggestions

        Returns list of suggestions with metadata
        """
        partial_lower = partial_query.lower().strip()

        if not partial_lower:
            return self._get_default_suggestions(admin_id, limit)

        suggestions = []
        seen_queries = set()

        # 1. User's recent searches (personalized)
        recent = self._get_recent_searches(partial_lower, admin_id, limit=3)
        for suggestion in recent:
            if suggestion['query_lower'] not in seen_queries:
                suggestions.append({
                    **suggestion,
                    'source': 'recent',
                    'icon': '🕐',
                    'badge': 'Recent'
                })
                seen_queries.add(suggestion['query_lower'])

        # 2. Cached popular searches (all users)
        popular = self._get_popular_searches(partial_lower, limit=3)
        for suggestion in popular:
            if suggestion['query_lower'] not in seen_queries:
                suggestions.append({
                    **suggestion,
                    'source': 'popular',
                    'icon': '🔥',
                    'badge': f"{suggestion['hit_count']}× searched"
                })
                seen_queries.add(suggestion['query_lower'])

        # 3. Trending searches (time-based popularity)
        trending = self._get_trending_searches(partial_lower, limit=2)
        for suggestion in trending:
            if suggestion['query_lower'] not in seen_queries:
                suggestions.append({
                    **suggestion,
                    'source': 'trending',
                    'icon': '📈',
                    'badge': 'Trending'
                })
                seen_queries.add(suggestion['query_lower'])

        # 4. AI-powered semantic suggestions
        semantic = self._get_semantic_suggestions(partial_lower, admin_id, limit=3)
        for suggestion in semantic:
            if suggestion['query_lower'] not in seen_queries:
                suggestions.append({
                    **suggestion,
                    'source': 'ai',
                    'icon': '🤖',
                    'badge': 'AI Suggested'
                })
                seen_queries.add(suggestion['query_lower'])

        # 5. Context-aware file type suggestions
        context = self._get_context_suggestions(partial_lower, admin_id, limit=2)
        for suggestion in context:
            if suggestion['query_lower'] not in seen_queries:
                suggestions.append({
                    **suggestion,
                    'source': 'context',
                    'icon': '🎯',
                    'badge': 'Smart Match'
                })
                seen_queries.add(suggestion['query_lower'])

        # Sort by relevance score
        suggestions.sort(key=lambda x: x.get('score', 0), reverse=True)

        return suggestions[:limit]

    def _get_default_suggestions(self, admin_id: str, limit: int) -> List[Dict]:
        """Get suggestions when no query entered"""
        suggestions = []

        # Recent searches
        user_recent = [h for h in reversed(self.search_history[-20:])
                      if h['admin_id'] == admin_id]

        for entry in user_recent[:5]:
            suggestions.append({
                'query': entry['query'],
                'query_lower': entry['query_lower'],
                'source': 'recent',
                'icon': '🕐',
                'badge': 'Recent',
                'score': 10,
                'timestamp': entry['timestamp']
            })

        # Popular searches
        popular = sorted(self.search_cache.items(),
                        key=lambda x: x[1].get('hit_count', 0),
                        reverse=True)[:3]

        for query_lower, data in popular:
            suggestions.append({
                'query': data.get('query', query_lower),
                'query_lower': query_lower,
                'source': 'popular',
                'icon': '🔥',
                'badge': f"{data['hit_count']}× searched",
                'score': data['hit_count'],
                'hit_count': data['hit_count']
            })

        return suggestions[:limit]

    def _get_recent_searches(self, partial: str, admin_id: str, limit: int) -> List[Dict]:
        """Get user's recent searches matching partial query"""
        matches = []

        # Search recent history in reverse (most recent first)
        for entry in reversed(self.search_history[-100:]):
            if entry['admin_id'] != admin_id:
                continue

            query_lower = entry['query_lower']

            # Check if matches
            if partial in query_lower or query_lower.startswith(partial):
                score = 10

                # Boost exact prefix matches
                if query_lower.startswith(partial):
                    score += 5

                # Boost recent searches
                age_hours = (time.time() - entry['timestamp']) / 3600
                recency_score = max(0, 5 - (age_hours / 24))  # Decay over days
                score += recency_score

                matches.append({
                    'query': entry['query'],
                    'query_lower': query_lower,
                    'score': score,
                    'timestamp': entry['timestamp'],
                    'results_count': entry.get('results_count', 0)
                })

                if len(matches) >= limit:
                    break

        return sorted(matches, key=lambda x: x['score'], reverse=True)[:limit]

    def _get_popular_searches(self, partial: str, limit: int) -> List[Dict]:
        """Get popular searches across all users"""
        matches = []

        for query_lower, data in self.search_cache.items():
            # Check if matches
            if partial in query_lower or query_lower.startswith(partial):
                score = data['hit_count']

                # Boost prefix matches
                if query_lower.startswith(partial):
                    score += 10

                # Consider recency
                age_hours = (time.time() - data['last_accessed']) / 3600
                if age_hours < 24:  # Boost if used in last day
                    score += 5

                matches.append({
                    'query': data.get('query', query_lower),
                    'query_lower': query_lower,
                    'score': score,
                    'hit_count': data['hit_count'],
                    'last_accessed': data['last_accessed']
                })

        return sorted(matches, key=lambda x: x['score'], reverse=True)[:limit]

    def _get_trending_searches(self, partial: str, limit: int) -> List[Dict]:
        """Get trending searches (popular in last 24h)"""
        matches = []
        current_time = time.time()
        cutoff_time = current_time - self.trending_window

        for query_lower, data in self.trending_searches.items():
            # Only consider recent searches
            if data['last_searched'] < cutoff_time:
                continue

            # Check if matches
            if partial in query_lower or query_lower.startswith(partial):
                # Score based on count and recency
                score = data['count']

                # Boost very recent searches
                age_hours = (current_time - data['last_searched']) / 3600
                if age_hours < 1:
                    score += 10
                elif age_hours < 6:
                    score += 5

                # Boost searches by multiple users
                user_count = len(data.get('users', []))
                score += user_count * 2

                matches.append({
                    'query': data.get('query', query_lower),
                    'query_lower': query_lower,
                    'score': score,
                    'count': data['count'],
                    'last_searched': data['last_searched']
                })

        return sorted(matches, key=lambda x: x['score'], reverse=True)[:limit]

    def _get_semantic_suggestions(self, partial: str, admin_id: str, limit: int) -> List[Dict]:
        """
        AI-powered semantic suggestions

        Uses patterns and understanding to suggest related queries
        """
        suggestions = []

        # Common semantic patterns and synonyms
        semantic_patterns = {
            'photo': ['image', 'picture', 'pic', 'jpg', 'png', 'screenshot'],
            'video': ['movie', 'clip', 'recording', 'mp4', 'film'],
            'audio': ['music', 'sound', 'song', 'mp3', 'track'],
            'doc': ['document', 'file', 'text', 'pdf', 'word'],
            'code': ['script', 'program', 'source', 'py', 'js'],
            'recent': ['today', 'latest', 'new', 'current'],
            'old': ['archive', 'previous', 'past', 'backup'],
            'large': ['big', 'huge', 'size:>10mb'],
            'small': ['tiny', 'mini', 'size:<1mb'],
        }

        # Find semantic matches
        words = partial.split()
        for word in words:
            for key, synonyms in semantic_patterns.items():
                if word.lower() in synonyms or key in word.lower():
                    # Suggest related terms
                    for synonym in synonyms[:2]:
                        if synonym != word.lower():
                            suggested_query = partial.replace(word, synonym)
                            suggestions.append({
                                'query': suggested_query,
                                'query_lower': suggested_query.lower(),
                                'score': 5,
                                'semantic_relation': f'{word} → {synonym}'
                            })

        # User's frequent terms combined with current search
        user_prefs = self.user_preferences.get(admin_id, {})
        frequent_terms = user_prefs.get('frequent_terms', Counter())

        if frequent_terms:
            top_terms = [term for term, count in frequent_terms.most_common(5)]
            for term in top_terms:
                if term not in partial.lower() and len(suggestions) < limit:
                    suggested_query = f"{partial} {term}"
                    suggestions.append({
                        'query': suggested_query,
                        'query_lower': suggested_query.lower(),
                        'score': 4,
                        'personalized': True
                    })

        return suggestions[:limit]

    def _get_context_suggestions(self, partial: str, admin_id: str, limit: int) -> List[Dict]:
        """
        Context-aware suggestions based on file types and patterns
        """
        suggestions = []

        # Detect file type mentions
        file_type_queries = {
            'image': '@type:image',
            'photo': '@type:image',
            'video': '@type:video',
            'audio': '@type:audio',
            'document': '@type:document',
            'pdf': '@ext:pdf',
            'code': '@type:code',
        }

        for keyword, filter_query in file_type_queries.items():
            if keyword in partial.lower() and '@' not in partial:
                suggested_query = f"{partial} {filter_query}"
                suggestions.append({
                    'query': suggested_query,
                    'query_lower': suggested_query.lower(),
                    'score': 8,
                    'context': 'file_type_filter'
                })

        # Size-based suggestions
        size_keywords = ['large', 'big', 'small', 'tiny', 'huge']
        for keyword in size_keywords:
            if keyword in partial.lower() and '@size' not in partial:
                if keyword in ['large', 'big', 'huge']:
                    suggested_query = f"{partial} @size:>10mb"
                else:
                    suggested_query = f"{partial} @size:<1mb"

                suggestions.append({
                    'query': suggested_query,
                    'query_lower': suggested_query.lower(),
                    'score': 7,
                    'context': 'size_filter'
                })

        # Date-based suggestions
        date_keywords = ['today', 'yesterday', 'recent', 'new', 'old']
        for keyword in date_keywords:
            if keyword in partial.lower() and '@date' not in partial:
                if keyword in ['today', 'recent', 'new']:
                    suggested_query = f"{partial} @date:today"
                elif keyword == 'yesterday':
                    suggested_query = f"{partial} @date:yesterday"
                else:
                    suggested_query = f"{partial} @date:>30days"

                suggestions.append({
                    'query': suggested_query,
                    'query_lower': suggested_query.lower(),
                    'score': 6,
                    'context': 'date_filter'
                })

        return suggestions[:limit]

    def _clean_cache(self):
        """Remove old cache entries"""
        current_time = time.time()
        cutoff_time = current_time - self.cache_ttl

        # Remove old entries
        expired = [q for q, data in self.search_cache.items()
                  if data.get('last_accessed', 0) < cutoff_time]

        for query in expired:
            del self.search_cache[query]

        # Keep only top N entries if too large
        if len(self.search_cache) > self.max_cache_size:
            sorted_cache = sorted(self.search_cache.items(),
                                 key=lambda x: x[1].get('hit_count', 0),
                                 reverse=True)
            self.search_cache = dict(sorted_cache[:self.max_cache_size])

    def get_analytics(self, admin_id: str = None) -> Dict:
        """Get analytics about search patterns"""
        analytics = {
            'total_searches': len(self.search_history),
            'cached_queries': len(self.search_cache),
            'trending_queries': len(self.trending_searches),
            'top_searches': [],
            'recent_searches': [],
            'search_trends': []
        }

        # Top searches
        top_cache = sorted(self.search_cache.items(),
                          key=lambda x: x[1].get('hit_count', 0),
                          reverse=True)[:10]

        analytics['top_searches'] = [
            {
                'query': data.get('query'),
                'count': data.get('hit_count'),
                'last_used': data.get('last_accessed')
            }
            for query, data in top_cache
        ]

        # User-specific analytics
        if admin_id:
            user_searches = [h for h in self.search_history if h['admin_id'] == admin_id]
            analytics['user_total_searches'] = len(user_searches)

            recent_user = user_searches[-10:]
            analytics['recent_searches'] = [
                {'query': h['query'], 'timestamp': h['timestamp']}
                for h in recent_user
            ]

        return analytics

    def clear_user_history(self, admin_id: str):
        """Clear search history for a specific user"""
        self.search_history = [h for h in self.search_history
                              if h['admin_id'] != admin_id]

        if admin_id in self.user_preferences:
            del self.user_preferences[admin_id]

        self.save_data()
        logger.info(f"Cleared search history for user {admin_id}")


# Global instance
_suggestion_engine = None

def get_suggestion_engine(storage_path: str = None) -> IntelligentSearchSuggestions:
    """Get or create global suggestion engine instance"""
    global _suggestion_engine

    if _suggestion_engine is None:
        _suggestion_engine = IntelligentSearchSuggestions(storage_path)

    return _suggestion_engine
