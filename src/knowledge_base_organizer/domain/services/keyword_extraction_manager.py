"""Keyword extraction manager for configurable keyword extraction."""

import re
import shutil
from pathlib import Path
from typing import Any

import yaml


class KeywordExtractionManager:
    """Manager for configurable keyword extraction from content."""

    def __init__(self, config_dir: Path | None = None):
        """Initialize keyword extraction manager.

        Args:
            config_dir: Configuration directory path
        """
        self.config_dir = config_dir or Path.home() / ".kiro"
        self.config_dir.mkdir(exist_ok=True)

        # Load keyword extraction configuration
        self.config = self._load_keyword_config()

    def _load_keyword_config(self) -> dict[str, Any]:
        """Load keyword extraction configuration from YAML file."""
        # Try to load from user's config directory first
        user_config_file = self.config_dir / "keyword_extraction.yaml"

        if not user_config_file.exists():
            # Copy default config from package
            default_config_file = (
                Path(__file__).parent.parent.parent
                / "config"
                / "keyword_extraction.yaml"
            )

            if default_config_file.exists():
                shutil.copy2(default_config_file, user_config_file)
            else:
                # Create minimal default config if package file doesn't exist
                return self._create_default_config()

        try:
            with user_config_file.open(encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return self._create_default_config()

    def _create_default_config(self) -> dict[str, Any]:
        """Create default keyword extraction configuration."""
        return {
            "common_words": {
                "english": [
                    "the",
                    "and",
                    "for",
                    "are",
                    "but",
                    "not",
                    "you",
                    "all",
                    "can",
                    "had",
                    "her",
                    "was",
                    "one",
                    "our",
                    "out",
                    "day",
                    "get",
                    "has",
                    "him",
                    "his",
                    "how",
                    "its",
                    "may",
                    "new",
                    "now",
                    "old",
                    "see",
                    "two",
                    "who",
                    "boy",
                    "did",
                    "she",
                    "use",
                    "way",
                    "will",
                    "with",
                    "have",
                    "this",
                    "that",
                    "from",
                    "they",
                    "know",
                    "want",
                    "been",
                    "good",
                    "much",
                    "some",
                    "time",
                    "very",
                    "when",
                    "come",
                    "here",
                    "just",
                    "like",
                    "long",
                    "make",
                    "many",
                    "over",
                    "such",
                    "take",
                    "than",
                    "them",
                    "well",
                    "were",
                    "what",
                    "your",
                ],
                "japanese": [
                    "これ",
                    "それ",
                    "あれ",
                    "この",
                    "その",
                    "あの",
                    "です",
                    "である",
                    "だった",
                    "でした",
                    "します",
                    "しました",
                    "という",
                    "として",
                    "について",
                    "による",
                    "によって",
                    "において",
                ],
            },
            "important_keywords": {
                "technical_terms": {
                    "specific_terms": [
                        "API",
                        "REST",
                        "JSON",
                        "HTTP",
                        "SQL",
                        "JavaScript",
                        "Python",
                    ]
                }
            },
            "extraction_settings": {
                "min_keyword_length": 3,
                "max_keyword_length": 50,
                "exclude_numbers_only": True,
                "case_sensitive": False,
                "remove_duplicates": True,
                "max_keywords": 100,
            },
        }

    def extract_keywords(self, content: str) -> set[str]:
        """Extract meaningful keywords from content using configuration.

        Args:
            content: The content to extract keywords from

        Returns:
            Set of keywords found in the content
        """
        # Get extraction settings
        settings = self.config.get("extraction_settings", {})
        min_length = settings.get("min_keyword_length", 3)
        max_length = settings.get("max_keyword_length", 50)
        exclude_numbers = settings.get("exclude_numbers_only", True)
        case_sensitive = settings.get("case_sensitive", False)
        max_keywords = settings.get("max_keywords", 100)

        # Clean content
        cleaned_content = self._clean_content(content)

        # Extract words using multiple patterns
        keywords = set()

        # Extract English words
        english_words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_-]*\b", cleaned_content)
        keywords.update(english_words)

        # Extract Japanese words (hiragana, katakana, kanji) - longer sequences
        japanese_words = re.findall(
            r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]{2,}", cleaned_content
        )
        keywords.update(japanese_words)

        # Also extract individual kanji compounds and technical terms
        kanji_compounds = re.findall(r"[\u4E00-\u9FAF]{2,}", cleaned_content)
        keywords.update(kanji_compounds)

        # Extract katakana technical terms
        katakana_terms = re.findall(r"[\u30A0-\u30FF]{3,}", cleaned_content)
        keywords.update(katakana_terms)

        # Extract technical terms (CamelCase, snake_case, etc.)
        technical_patterns = [
            r"\b[A-Z][a-z]+[A-Z][a-zA-Z]*\b",  # CamelCase
            r"\b[a-z]+_[a-z]+\b",  # snake_case
            r"\b[a-z]+-[a-z]+\b",  # kebab-case
            r"\b[A-Z]{2,}\b",  # UPPERCASE abbreviations
        ]

        for pattern in technical_patterns:
            matches = re.findall(pattern, cleaned_content)
            keywords.update(matches)

        # Filter keywords
        filtered_keywords = self._filter_keywords(
            keywords, min_length, max_length, exclude_numbers, case_sensitive
        )

        # Apply importance weighting and limit results
        weighted_keywords = self._apply_importance_weighting(filtered_keywords)

        if max_keywords > 0:
            # Sort by importance and take top keywords
            sorted_keywords = sorted(
                weighted_keywords.items(), key=lambda x: x[1], reverse=True
            )
            return {kw for kw, _ in sorted_keywords[:max_keywords]}

        return set(weighted_keywords.keys())

    def _clean_content(self, content: str) -> str:
        """Clean content by removing markdown syntax and frontmatter."""
        # Remove frontmatter
        cleaned = re.sub(r"^---.*?---", "", content, flags=re.DOTALL)

        # Remove code blocks first (before inline code)
        cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.DOTALL)

        # Remove inline code
        cleaned = re.sub(r"`[^`]+`", " ", cleaned)

        # Remove URLs
        cleaned = re.sub(r"https?://[^\s]+", " ", cleaned)

        # Remove markdown links
        cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)

        # Remove markdown syntax
        return re.sub(r"[#*\[\](){}]", " ", cleaned)

    def _filter_keywords(
        self,
        keywords: set[str],
        min_length: int,
        max_length: int,
        exclude_numbers: bool,
        case_sensitive: bool,
    ) -> set[str]:
        """Filter keywords based on configuration settings."""
        filtered = set()

        # Get common words to exclude
        common_english = set(self.config.get("common_words", {}).get("english", []))
        common_japanese = set(self.config.get("common_words", {}).get("japanese", []))

        for keyword in keywords:
            # Length check
            if len(keyword) < min_length or len(keyword) > max_length:
                continue

            # Numbers only check
            if exclude_numbers and keyword.isdigit():
                continue

            # Common words check
            check_word = keyword if case_sensitive else keyword.lower()
            if check_word in common_english or keyword in common_japanese:
                continue

            # Special characters check (allow some technical chars)
            if re.match(
                r"^[a-zA-Z0-9_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF-]+$", keyword
            ):
                filtered.add(keyword)

        return filtered

    def _apply_importance_weighting(self, keywords: set[str]) -> dict[str, float]:
        """Apply importance weighting to keywords based on configuration."""
        weighted = {}

        # Get importance settings
        important_config = self.config.get("important_keywords", {})
        category_weights = self.config.get("category_weights", {})
        default_weight = category_weights.get("default", 1.0)

        for keyword in keywords:
            weight = default_weight

            # Check technical terms
            tech_terms = important_config.get("technical_terms", {}).get(
                "specific_terms", []
            )
            if keyword in tech_terms:
                weight = category_weights.get("technical_terms", 1.5)

            # Check Japanese terms
            japanese_config = important_config.get("japanese_terms", {})
            for _category, terms in japanese_config.items():
                if keyword in terms:
                    weight = category_weights.get("japanese_terms", 1.2)
                    break

            # Check if it's a proper noun (starts with capital)
            if keyword and keyword[0].isupper():
                weight = max(weight, category_weights.get("proper_nouns", 1.3))

            # Check if it's a compound word (contains underscore or hyphen)
            if "_" in keyword or "-" in keyword:
                weight = max(weight, category_weights.get("compound_words", 1.1))

            weighted[keyword] = weight

        return weighted

    def add_custom_keywords(
        self, keywords: list[str], category: str = "custom"
    ) -> bool:
        """Add custom keywords to the configuration.

        Args:
            keywords: List of keywords to add
            category: Category for the keywords

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load current config
            user_config_file = self.config_dir / "keyword_extraction.yaml"

            if not user_config_file.exists():
                self._load_keyword_config()  # This will create the file

            with user_config_file.open(encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}

            # Add custom keywords
            if (
                "user_defined_keywords" not in config
                or config["user_defined_keywords"] is None
            ):
                config["user_defined_keywords"] = {}

            if category not in config["user_defined_keywords"]:
                config["user_defined_keywords"][category] = []

            # Ensure the category list exists and is not None
            if config["user_defined_keywords"][category] is None:
                config["user_defined_keywords"][category] = []

            # Add new keywords (avoid duplicates)
            existing = set(config["user_defined_keywords"][category])
            for keyword in keywords:
                if keyword not in existing:
                    config["user_defined_keywords"][category].append(keyword)

            # Save updated config
            with user_config_file.open("w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            # Reload config
            self.config = config
            return True

        except Exception:
            return False

    def get_keyword_statistics(self, content: str) -> dict[str, Any]:
        """Get statistics about keyword extraction from content.

        Args:
            content: The content to analyze

        Returns:
            Dictionary with extraction statistics
        """
        keywords = self.extract_keywords(content)

        # Categorize keywords
        stats = {
            "total_keywords": len(keywords),
            "english_keywords": 0,
            "japanese_keywords": 0,
            "technical_keywords": 0,
            "compound_keywords": 0,
            "categories": {},
        }

        tech_terms = (
            self.config.get("important_keywords", {})
            .get("technical_terms", {})
            .get("specific_terms", [])
        )

        for keyword in keywords:
            # Count by type
            if re.match(r"^[a-zA-Z0-9_-]+$", keyword):
                stats["english_keywords"] += 1
            elif re.match(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]", keyword):
                stats["japanese_keywords"] += 1

            if keyword in tech_terms:
                stats["technical_keywords"] += 1

            if "_" in keyword or "-" in keyword:
                stats["compound_keywords"] += 1

        return stats
