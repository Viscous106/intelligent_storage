"""
AI-powered content analyzer using Ollama/Llama3.
Provides intelligent categorization and metadata extraction.
"""

import json
import requests
import base64
from typing import Dict, Optional, List
from pathlib import Path
from django.conf import settings
import logging

# Import smart database selector
from .smart_db_selector import smart_db_selector

logger = logging.getLogger(__name__)


class OllamaAnalyzer:
    """
    Analyzes files using Ollama's Llama3 model for intelligent categorization.
    """

    def __init__(self):
        """Initialize Ollama analyzer with configuration from settings."""
        self.host = settings.OLLAMA_SETTINGS['HOST']
        # Use gemma:2b as fallback if llama3 not available
        self.model = settings.OLLAMA_SETTINGS.get('MODEL', 'gemma:2b')
        self.generate_url = f"{self.host}/api/generate"
        self.chat_url = f"{self.host}/api/chat"
        self.available_models = self._get_available_models()

    def _get_available_models(self) -> list:
        """Get list of available Ollama models."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [m['name'] for m in models]
            return []
        except Exception as e:
            logger.warning(f"Could not fetch available models: {e}")
            return []

    def analyze_image(self, image_path: str, user_comment: str = None) -> Dict:
        """
        Analyze an image file to determine its category and generate metadata.

        Args:
            image_path: Path to the image file
            user_comment: Optional user-provided context

        Returns:
            Dict containing category, tags, and description
        """
        try:
            # Read and encode image
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Create prompt
            prompt = self._build_image_prompt(user_comment)

            # Call Ollama API with vision capabilities if available
            # Check if vision model is available, otherwise use fallback
            vision_model = 'llama3.2-vision' if 'llama3.2-vision' in self.available_models else None

            if vision_model:
                payload = {
                    "model": vision_model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False
                }

                response = requests.post(self.generate_url, json=payload, timeout=60)

                if response.status_code == 200:
                    result = response.json()
                    return self._parse_analysis_response(result.get('response', ''))
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return self._fallback_analysis()
            else:
                logger.info(f"Vision model not available. Using fallback analysis.")
                return self._fallback_analysis()

        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            return self._fallback_analysis()

    def analyze_file_content(self, file_path: str, file_type: str,
                            user_comment: str = None) -> Dict:
        """
        Analyze file content to suggest categorization.

        Args:
            file_path: Path to the file
            file_type: Detected file type category
            user_comment: Optional user-provided context

        Returns:
            Dict containing suggested category and metadata
        """
        try:
            # For text-based files, read content
            if file_type in ['documents', 'programs']:
                content = self._read_file_safely(file_path)
            else:
                content = f"File type: {file_type}"

            prompt = self._build_content_prompt(content, file_type, user_comment)

            # Use available model or fallback
            model_to_use = self.model if self.model in self.available_models else (
                self.available_models[0] if self.available_models else None
            )

            if not model_to_use:
                logger.warning("No Ollama models available. Using fallback.")
                return self._fallback_analysis()

            payload = {
                "model": model_to_use,
                "prompt": prompt,
                "stream": False
            }

            response = requests.post(self.generate_url, json=payload, timeout=60)

            if response.status_code == 200:
                result = response.json()
                return self._parse_analysis_response(result.get('response', ''))
            else:
                logger.error(f"Ollama API error: {response.status_code}")
                return self._fallback_analysis()

        except Exception as e:
            logger.error(f"Content analysis failed: {str(e)}")
            return self._fallback_analysis()

    def analyze_json_for_db_choice(self, json_data: Dict or List,
                                   user_comment: str = None,
                                   expected_read_write_ratio: float = None) -> Dict:
        """
        Analyze JSON structure to determine if SQL or NoSQL is more appropriate.
        Uses advanced pattern analysis considering read/write performance.

        Args:
            json_data: The JSON data to analyze
            user_comment: Optional user context about the data
            expected_read_write_ratio: Expected reads/writes ratio
                                      >1.0 = read-heavy → NoSQL better
                                      <1.0 = write-heavy → SQL better

        Returns:
            Dict with database recommendation and performance estimates
        """
        try:
            # Use smart database selector for comprehensive analysis
            logger.info("Using smart DB selector with read/write pattern analysis")
            result = smart_db_selector.analyze_and_select(
                data=json_data,
                user_comment=user_comment,
                expected_read_write_ratio=expected_read_write_ratio
            )

            logger.info(
                f"DB Decision: {result['database_type']} "
                f"(confidence: {result['confidence']}%, "
                f"read/write ratio: {result['usage_prediction']['read_write_ratio']:.2f})"
            )

            return result

        except Exception as e:
            logger.error(f"Smart DB selection failed: {str(e)}, falling back")
            return self._fallback_db_recommendation({})

    def _build_image_prompt(self, user_comment: str = None) -> str:
        """Build prompt for image analysis."""
        base_prompt = """Analyze this image and provide a JSON response with:
1. "category": A short descriptive category name (e.g., "nature", "people", "food", "architecture")
2. "tags": A list of 3-5 relevant tags
3. "description": A brief description

Respond ONLY with valid JSON, no additional text."""

        if user_comment:
            base_prompt += f"\n\nUser context: {user_comment}"

        return base_prompt

    def _build_content_prompt(self, content: str, file_type: str,
                             user_comment: str = None) -> str:
        """Build prompt for content analysis."""
        base_prompt = f"""Analyze this {file_type} file and suggest a subcategory.

File content preview:
{content[:1000]}

Provide a JSON response with:
1. "category": A descriptive subcategory name
2. "tags": Relevant tags
3. "description": Brief description

Respond ONLY with valid JSON."""

        if user_comment:
            base_prompt += f"\n\nUser context: {user_comment}"

        return base_prompt

    def _build_json_analysis_prompt(self, structure_info: Dict,
                                    user_comment: str = None) -> str:
        """Build prompt for JSON database analysis."""
        prompt = f"""Analyze this JSON data structure and recommend the best database type.

Structure Analysis:
- Is Array: {structure_info.get('is_array', False)}
- Nesting Depth: {structure_info.get('max_depth', 0)}
- Field Count: {structure_info.get('field_count', 0)}
- Has Nested Objects: {structure_info.get('has_nested', False)}
- Has Arrays: {structure_info.get('has_arrays', False)}
- Schema Consistency: {structure_info.get('is_consistent', True)}

Sample Structure:
{json.dumps(structure_info.get('sample_schema', {}), indent=2)[:500]}

Respond with JSON containing:
1. "database_type": "SQL" or "NoSQL"
2. "confidence": confidence score 0-100
3. "reasoning": brief explanation
4. "suggested_schema": schema structure recommendation

Respond ONLY with valid JSON."""

        if user_comment:
            prompt += f"\n\nUser context: {user_comment}"

        return prompt

    def _analyze_json_structure(self, data) -> Dict:
        """Analyze JSON structure to help determine database choice."""
        info = {
            'is_array': isinstance(data, list),
            'max_depth': self._get_max_depth(data),
            'field_count': 0,
            'has_nested': False,
            'has_arrays': False,
            'is_consistent': True,
            'sample_schema': {}
        }

        if isinstance(data, list) and len(data) > 0:
            # Analyze array consistency
            if len(data) > 1:
                info['is_consistent'] = self._check_consistency(data)
            # Use first item as sample
            sample = data[0] if data else {}
        else:
            sample = data if isinstance(data, dict) else {}

        if isinstance(sample, dict):
            info['field_count'] = len(sample)
            info['sample_schema'] = self._extract_schema(sample)
            info['has_nested'] = self._has_nested_objects(sample)
            info['has_arrays'] = self._has_arrays(sample)

        return info

    def _get_max_depth(self, obj, current_depth=0) -> int:
        """Calculate maximum nesting depth."""
        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_max_depth(v, current_depth + 1)
                      for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_max_depth(item, current_depth)
                      for item in obj)
        else:
            return current_depth

    def _check_consistency(self, arr: List) -> bool:
        """Check if array items have consistent structure."""
        if not arr or len(arr) < 2:
            return True

        first_keys = set(arr[0].keys()) if isinstance(arr[0], dict) else set()
        return all(set(item.keys()) == first_keys
                  for item in arr if isinstance(item, dict))

    def _extract_schema(self, obj: Dict) -> Dict:
        """Extract schema structure from object."""
        schema = {}
        for key, value in obj.items():
            if isinstance(value, dict):
                schema[key] = 'object'
            elif isinstance(value, list):
                schema[key] = 'array'
            elif isinstance(value, bool):
                schema[key] = 'boolean'
            elif isinstance(value, int):
                schema[key] = 'integer'
            elif isinstance(value, float):
                schema[key] = 'float'
            elif isinstance(value, str):
                schema[key] = 'string'
            else:
                schema[key] = 'unknown'
        return schema

    def _has_nested_objects(self, obj: Dict) -> bool:
        """Check if object has nested objects."""
        return any(isinstance(v, dict) for v in obj.values())

    def _has_arrays(self, obj: Dict) -> bool:
        """Check if object has array fields."""
        return any(isinstance(v, list) for v in obj.values())

    def _read_file_safely(self, file_path: str, max_size: int = 10000) -> str:
        """Safely read file content with size limit."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(max_size)
        except Exception:
            return ""

    def _parse_analysis_response(self, response: str) -> Dict:
        """Parse AI response and extract structured data."""
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception:
            pass

        # Fallback
        return self._fallback_analysis()

    def _parse_db_recommendation(self, response: str, structure_info: Dict) -> Dict:
        """Parse database recommendation response."""
        try:
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                # Ensure required fields
                if 'database_type' in result:
                    return result
        except Exception:
            pass

        # Fallback
        return self._fallback_db_recommendation(structure_info)

    def _fallback_analysis(self) -> Dict:
        """Fallback analysis when AI is unavailable."""
        return {
            'category': 'General',
            'subcategory': 'Uncategorized',
            'tags': ['unclassified', 'pending-analysis'],
            'description': 'File uploaded successfully. AI analysis pending.',
            'confidence': 1.0  # High confidence in basic categorization
        }

    def _fallback_db_recommendation(self, structure_info: Dict) -> Dict:
        """Fallback DB recommendation based on simple heuristics."""
        # Simple rule-based recommendation
        max_depth = structure_info.get('max_depth', 0)
        has_nested = structure_info.get('has_nested', False)
        is_consistent = structure_info.get('is_consistent', True)

        if max_depth > 3 or (has_nested and not is_consistent):
            db_type = "NoSQL"
            reasoning = "Deep nesting or inconsistent structure detected"
        elif is_consistent and not has_nested:
            db_type = "SQL"
            reasoning = "Flat, consistent structure suitable for relational DB"
        else:
            db_type = "NoSQL"
            reasoning = "Default to NoSQL for flexible schema"

        return {
            'database_type': db_type,
            'confidence': 60,
            'reasoning': reasoning,
            'suggested_schema': structure_info.get('sample_schema', {})
        }


# Singleton instance
ai_analyzer = OllamaAnalyzer()
