"""
Learning Engine - Stores patterns and learns from user corrections.
Improves mappings over time.
"""
import json
import hashlib
from typing import Dict, List, Any, Optional
from pathlib import Path


class LearningEngine:
    """
    Learns from user corrections and improves mappings.
    Builds a knowledge base over time.
    """
    
    def __init__(self, knowledge_base_path: str = "knowledge_base"):
        """
        Initialize learning engine.
        
        Args:
            knowledge_base_path: Path to knowledge base directory
        """
        self.kb_path = Path(knowledge_base_path)
        self.kb_path.mkdir(parents=True, exist_ok=True)
        
        self.mapping_cache_path = self.kb_path / "mapping_cache.json"
        self.corrections_path = self.kb_path / "user_corrections.json"
        self.template_profiles_path = self.kb_path / "template_profiles"
        self.template_profiles_path.mkdir(exist_ok=True)
        
        self.mapping_cache = self._load_cache()
        self.corrections = self._load_corrections()
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load mapping cache."""
        if self.mapping_cache_path.exists():
            try:
                with open(self.mapping_cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _load_corrections(self) -> List[Dict[str, Any]]:
        """Load user corrections."""
        if self.corrections_path.exists():
            try:
                with open(self.corrections_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def _save_cache(self):
        """Save mapping cache."""
        try:
            with open(self.mapping_cache_path, 'w', encoding='utf-8') as f:
                json.dump(self.mapping_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Failed to save mapping cache: {e}")
    
    def _save_corrections(self):
        """Save user corrections."""
        try:
            with open(self.corrections_path, 'w', encoding='utf-8') as f:
                json.dump(self.corrections, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Failed to save corrections: {e}")
    
    def learn_from_correction(
        self,
        template_id: str,
        column: str,
        original_mapping: str,
        corrected_mapping: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Learn from user correction.
        
        Args:
            template_id: Template identifier
            column: Column name that was corrected
            original_mapping: Original mapping path
            corrected_mapping: Corrected mapping path
            context: Optional context (canonical data, etc.)
        """
        correction = {
            "template_id": template_id,
            "column": column,
            "original_mapping": original_mapping,
            "corrected_mapping": corrected_mapping,
            "context": context or {},
            "timestamp": str(Path(__file__).stat().st_mtime)  # Simple timestamp
        }
        
        self.corrections.append(correction)
        self._save_corrections()
        
        # Update cache
        cache_key = self._get_cache_key(template_id, column)
        self.mapping_cache[cache_key] = {
            "mapping": corrected_mapping,
            "confidence": 1.0,
            "source": "user_correction"
        }
        self._save_cache()
    
    def get_suggested_mapping(
        self,
        template_id: str,
        column: str,
        available_data: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Get mapping suggestion from learned patterns.
        
        Args:
            template_id: Template identifier
            column: Column name
            available_data: Optional available data for context
        
        Returns:
            Suggested canonical path or None
        """
        # Check cache first
        cache_key = self._get_cache_key(template_id, column)
        if cache_key in self.mapping_cache:
            return self.mapping_cache[cache_key].get("mapping")
        
        # Check corrections for similar columns
        for correction in reversed(self.corrections):
            if correction["template_id"] == template_id:
                if correction["column"].lower() == column.lower():
                    return correction["corrected_mapping"]
        
        return None
    
    def build_template_profile(
        self,
        template_schema: Dict[str, Any],
        sample_mappings: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Build a profile for this template type.
        
        Args:
            template_schema: Template schema
            sample_mappings: Sample column mappings
        
        Returns:
            Template profile
        """
        template_id = self._get_template_id(template_schema)
        
        profile = {
            "template_id": template_id,
            "schema": template_schema,
            "mappings": sample_mappings,
            "usage_count": 1
        }
        
        # Load existing profile if exists
        profile_path = self.template_profiles_path / f"{template_id}.json"
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    profile["usage_count"] = existing.get("usage_count", 0) + 1
                    # Merge mappings
                    existing_mappings = existing.get("mappings", [])
                    profile["mappings"] = existing_mappings + sample_mappings
            except Exception:
                pass
        
        # Save profile
        try:
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️  Failed to save template profile: {e}")
        
        return profile
    
    def get_template_profile(self, template_schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get existing template profile."""
        template_id = self._get_template_id(template_schema)
        profile_path = self.template_profiles_path / f"{template_id}.json"
        
        if profile_path.exists():
            try:
                with open(profile_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return None
    
    def _get_template_id(self, template_schema: Dict[str, Any]) -> str:
        """Generate template ID from schema."""
        columns = template_schema.get('columns', [])
        column_names = [col.get('header', '') for col in columns]
        schema_str = json.dumps(sorted(column_names), sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()[:16]
    
    def _get_cache_key(self, template_id: str, column: str) -> str:
        """Generate cache key."""
        return f"{template_id}:{column.lower()}"
