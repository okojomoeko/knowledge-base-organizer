"""Tag pattern management system for intelligent tag suggestions."""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class TagPattern(BaseModel):
    """Individual tag pattern definition."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    tag_name: str
    keywords: list[str]
    confidence_weight: float = Field(default=1.0, ge=0.0, le=2.0)
    category: str
    subcategory: str | None = None
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    usage_count: int = Field(default=0, ge=0)


class TagPatternCategory(BaseModel):
    """Category of tag patterns."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    name: str
    description: str
    patterns: dict[str, TagPattern] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=1, le=10)


class VaultTagAnalysis(BaseModel):
    """Analysis of existing tags in the vault."""

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    total_files: int
    total_tags: int
    unique_tags: int
    tag_frequency: dict[str, int] = Field(default_factory=dict)
    tag_cooccurrence: dict[str, dict[str, int]] = Field(default_factory=dict)
    tag_relationships: dict[str, dict[str, float]] = Field(default_factory=dict)
    most_common_tags: list[tuple[str, int]] = Field(default_factory=list)
    orphaned_tags: list[str] = Field(default_factory=list)  # Tags used only once
    analyzed_at: datetime = Field(default_factory=datetime.now)


class TagPatternManager:
    """Manager for tag patterns and vault tag analysis."""

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize tag pattern manager."""
        self.config_dir = config_dir or Path.cwd() / ".kiro" / "tag_patterns"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.patterns_file = self.config_dir / "tag_patterns.json"
        self.analysis_file = self.config_dir / "vault_tag_analysis.json"

        self.categories: dict[str, TagPatternCategory] = {}
        self.vault_analysis: VaultTagAnalysis | None = None

        # Initialize Japanese variation patterns from external file
        self.japanese_variations = self._load_japanese_variation_patterns()
        self.japanese_variations_file = self.config_dir / "japanese_variations.yaml"

        # Load existing patterns and analysis
        self._load_patterns()
        self._load_vault_analysis()

    def _load_japanese_variation_patterns(self) -> dict[str, Any]:
        """Load Japanese katakana variation patterns from external YAML file."""
        # Try to load from user's config directory first
        user_variations_file = self.config_dir / "japanese_variations.yaml"

        # If user file doesn't exist, copy from default and load
        if not user_variations_file.exists():
            self._create_default_japanese_variations_file(user_variations_file)

        try:
            with user_variations_file.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Convert YAML structure to internal format for backward compatibility
            return self._convert_yaml_to_internal_format(data)

        except Exception as e:
            print(
                f"Warning: Failed to load Japanese variations from "
                f"{user_variations_file}: {e}"
            )
            # Fallback to minimal hardcoded patterns
            return self._get_fallback_patterns()

    def _create_default_japanese_variations_file(self, target_path: Path) -> None:
        """Create default Japanese variations file from bundled template."""
        # Get the default file from the package
        default_file = (
            Path(__file__).parent.parent.parent / "config" / "japanese_variations.yaml"
        )

        if default_file.exists():
            shutil.copy2(default_file, target_path)
            print(f"Created default Japanese variations file at: {target_path}")
        else:
            # Create minimal file if template is missing
            minimal_data = {
                "metadata": {
                    "version": "1.0.0",
                    "description": "Japanese variation patterns",
                    "last_updated": datetime.now().isoformat(),
                },
                "long_vowel_patterns": {"ー": ["", "ウ", "ー"], "ウ": ["ー", "", "ウ"]},
                "consonant_patterns": {"ヴ": ["ブ", "バ"], "ティ": ["テ"]},
                "english_japanese_pairs": {
                    "API": {"japanese": ["エーピーアイ"], "aliases": ["api"]}
                },
            }

            with target_path.open("w", encoding="utf-8") as f:
                yaml.dump(minimal_data, f, allow_unicode=True, default_flow_style=False)

    def _convert_yaml_to_internal_format(
        self, yaml_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Convert YAML structure to internal format for backward compatibility."""
        result = {
            "long_vowel_patterns": yaml_data.get("long_vowel_patterns", {}),
            "consonant_patterns": yaml_data.get("consonant_patterns", {}),
            "english_japanese_pairs": {},
        }

        # Convert english_japanese_pairs format
        for english, data in yaml_data.get("english_japanese_pairs", {}).items():
            if isinstance(data, dict):
                japanese_terms = data.get("japanese", [])
                aliases = data.get("aliases", [])
                result["english_japanese_pairs"][english] = japanese_terms + aliases
            else:
                # Fallback for old format
                result["english_japanese_pairs"][english] = data

        return result

    def _get_fallback_patterns(self) -> dict[str, Any]:
        """Get minimal fallback patterns if YAML loading fails."""
        return {
            "long_vowel_patterns": {
                "ー": ["", "ウ", "ー"],
                "ウ": ["ー", "", "ウ"],
            },
            "consonant_patterns": {
                "ヴ": ["ブ", "バ"],
                "ティ": ["テ"],
            },
            "english_japanese_pairs": {
                "API": ["エーピーアイ", "api"],
                "DB": ["データベース", "db"],
            },
        }

    def find_japanese_variations(self, text: str) -> list[str]:
        """Find Japanese katakana variations of the given text."""
        variations = [text]

        # Apply long vowel variations
        for original, replacements in self.japanese_variations[
            "long_vowel_patterns"
        ].items():
            for replacement in replacements:
                if original in text:
                    variation = text.replace(original, replacement)
                    if variation != text and variation not in variations:
                        variations.append(variation)

        # Apply consonant variations
        for original, replacements in self.japanese_variations[
            "consonant_patterns"
        ].items():
            for replacement in replacements:
                if original in text:
                    variation = text.replace(original, replacement)
                    if variation != text and variation not in variations:
                        variations.append(variation)

        # Check for English-Japanese pairs
        text_upper = text.upper()
        if text_upper in self.japanese_variations["english_japanese_pairs"]:
            variations.extend(
                self.japanese_variations["english_japanese_pairs"][text_upper]
            )

        # Reverse lookup for Japanese to English
        for english, japanese_list in self.japanese_variations[
            "english_japanese_pairs"
        ].items():
            if text in japanese_list:
                variations.append(english.lower())
                variations.append(english.upper())

        return list(set(variations))  # Remove duplicates

    def _load_patterns(self) -> None:
        """Load tag patterns from file."""
        if self.patterns_file.exists():
            try:
                with Path(self.patterns_file).open(encoding="utf-8") as f:
                    data = json.load(f)

                for category_name, category_data in data.items():
                    category = TagPatternCategory(
                        name=category_name,
                        description=category_data.get("description", ""),
                        priority=category_data.get("priority", 1),
                    )

                    for pattern_name, pattern_data in category_data.get(
                        "patterns", {}
                    ).items():
                        pattern = TagPattern(**pattern_data)
                        category.patterns[pattern_name] = pattern

                    self.categories[category_name] = category
            except Exception as e:
                print(f"Warning: Failed to load tag patterns: {e}")
        else:
            # Initialize with default patterns
            self._create_default_patterns()

    def _load_vault_analysis(self) -> None:
        """Load vault tag analysis from file."""
        if self.analysis_file.exists():
            try:
                with Path(self.analysis_file).open(encoding="utf-8") as f:
                    data = json.load(f)
                self.vault_analysis = VaultTagAnalysis(**data)
            except Exception as e:
                print(f"Warning: Failed to load vault analysis: {e}")

    def save_patterns(self) -> None:
        """Save tag patterns to file."""
        data = {}
        for category_name, category in self.categories.items():
            data[category_name] = {
                "description": category.description,
                "priority": category.priority,
                "patterns": {
                    name: pattern.model_dump()
                    for name, pattern in category.patterns.items()
                },
            }

        with Path(self.patterns_file).open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)

    def save_vault_analysis(self) -> None:
        """Save vault tag analysis to file."""
        if self.vault_analysis:
            with Path(self.analysis_file).open("w", encoding="utf-8") as f:
                json.dump(
                    self.vault_analysis.model_dump(),
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

    def _create_default_patterns(self) -> None:
        """Create default tag patterns."""
        # Programming Languages
        programming_category = TagPatternCategory(
            name="programming_languages",
            description="Programming languages and frameworks",
            priority=8,
        )

        programming_patterns = {
            "python": TagPattern(
                tag_name="python",
                keywords=[
                    "python",
                    "py",
                    "django",
                    "flask",
                    "pandas",
                    "numpy",
                    "fastapi",
                ],
                category="programming_languages",
                description="Python programming language",
                confidence_weight=1.2,
            ),
            "javascript": TagPattern(
                tag_name="javascript",
                keywords=["javascript", "js", "node", "react", "vue", "angular", "npm"],
                category="programming_languages",
                description="JavaScript programming language",
                confidence_weight=1.2,
            ),
            "typescript": TagPattern(
                tag_name="typescript",
                keywords=["typescript", "ts", "angular", "nest", "deno"],
                category="programming_languages",
                description="TypeScript programming language",
                confidence_weight=1.1,
            ),
            "rust": TagPattern(
                tag_name="rust",
                keywords=["rust", "cargo", "tokio", "serde", "actix"],
                category="programming_languages",
                description="Rust programming language",
                confidence_weight=1.1,
            ),
            "go": TagPattern(
                tag_name="go",
                keywords=["golang", "go", "gin", "echo", "goroutine"],
                category="programming_languages",
                description="Go programming language",
                confidence_weight=1.1,
            ),
        }

        for name, pattern in programming_patterns.items():
            programming_category.patterns[name] = pattern

        self.categories["programming_languages"] = programming_category

        # Technologies
        tech_category = TagPatternCategory(
            name="technologies",
            description="Technologies, tools, and platforms",
            priority=7,
        )

        tech_patterns = {
            "database": TagPattern(
                tag_name="database",
                keywords=["sql", "mysql", "postgresql", "mongodb", "redis", "sqlite"],
                category="technologies",
                subcategory="database",
                description="Database technologies",
                confidence_weight=1.0,
            ),
            "cloud": TagPattern(
                tag_name="cloud",
                keywords=["aws", "azure", "gcp", "docker", "kubernetes", "serverless"],
                category="technologies",
                subcategory="cloud",
                description="Cloud technologies",
                confidence_weight=1.0,
            ),
            "frontend": TagPattern(
                tag_name="frontend",
                keywords=["html", "css", "sass", "webpack", "vite", "tailwind"],
                category="technologies",
                subcategory="frontend",
                description="Frontend technologies",
                confidence_weight=1.0,
            ),
            "backend": TagPattern(
                tag_name="backend",
                keywords=["api", "rest", "graphql", "microservice", "server"],
                category="technologies",
                subcategory="backend",
                description="Backend technologies",
                confidence_weight=1.0,
            ),
        }

        for name, pattern in tech_patterns.items():
            tech_category.patterns[name] = pattern

        self.categories["technologies"] = tech_category

        # Concepts
        concepts_category = TagPatternCategory(
            name="concepts",
            description="Programming concepts and methodologies",
            priority=6,
        )

        concept_patterns = {
            "architecture": TagPattern(
                tag_name="architecture",
                keywords=[
                    "design pattern",
                    "architecture",
                    "microservice",
                    "monolith",
                    "mvc",
                ],
                category="concepts",
                description="Software architecture concepts",
                confidence_weight=0.9,
            ),
            "algorithms": TagPattern(
                tag_name="algorithms",
                keywords=[
                    "algorithm",
                    "data structure",
                    "complexity",
                    "optimization",
                    "sorting",
                ],
                category="concepts",
                description="Algorithms and data structures",
                confidence_weight=0.9,
            ),
            "testing": TagPattern(
                tag_name="testing",
                keywords=[
                    "test",
                    "unit test",
                    "integration test",
                    "tdd",
                    "bdd",
                    "pytest",
                ],
                category="concepts",
                description="Software testing concepts",
                confidence_weight=0.8,
            ),
        }

        for name, pattern in concept_patterns.items():
            concepts_category.patterns[name] = pattern

        self.categories["concepts"] = concepts_category

        # Japanese Content
        japanese_category = TagPatternCategory(
            name="japanese_content",
            description="Japanese language and culture content",
            priority=5,
        )

        japanese_patterns = {
            "japanese": TagPattern(
                tag_name="japanese",
                keywords=[
                    "日本語",
                    "japanese",
                    "nihongo",
                    "katakana",
                    "hiragana",
                    "kanji",
                ],
                category="japanese_content",
                description="Japanese language content",
                confidence_weight=1.3,
            ),
            "culture": TagPattern(
                tag_name="culture",
                keywords=[
                    "文化",
                    "culture",
                    "tradition",
                    "festival",
                    "ceremony",
                    "習慣",
                ],
                category="japanese_content",
                description="Japanese culture content",
                confidence_weight=1.0,
            ),
            "api": TagPattern(
                tag_name="api",
                keywords=[
                    "api",
                    "エーピーアイ",
                    "インターフェース",
                    "インターフェイス",
                    "interface",
                ],
                category="japanese_content",
                description="API and interface related content",
                confidence_weight=1.2,
            ),
            "database": TagPattern(
                tag_name="database",
                keywords=[
                    "データベース",
                    "db",
                    "database",
                    "ディービー",
                ],
                category="japanese_content",
                description="Database related content",
                confidence_weight=1.2,
            ),
            "service": TagPattern(
                tag_name="service",
                keywords=[
                    "サービス",
                    "サーヴィス",
                    "service",
                ],
                category="japanese_content",
                description="Service related content",
                confidence_weight=1.1,
            ),
        }

        for name, pattern in japanese_patterns.items():
            japanese_category.patterns[name] = pattern

        self.categories["japanese_content"] = japanese_category

        # Save default patterns
        self.save_patterns()

    def reload_japanese_variations(self) -> bool:
        """Reload Japanese variation patterns from file."""
        try:
            self.japanese_variations = self._load_japanese_variation_patterns()
            return True
        except Exception as e:
            print(f"Failed to reload Japanese variations: {e}")
            return False

    def add_japanese_variation(
        self, category: str, original: str, variations: list[str]
    ) -> bool:
        """Add a new Japanese variation pattern."""
        user_variations_file = self.config_dir / "japanese_variations.yaml"

        try:
            # Load current data
            if user_variations_file.exists():
                with user_variations_file.open(encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
            else:
                data = {"metadata": {"version": "1.0.0"}}

            # Add new pattern
            if category not in data:
                data[category] = {}

            data[category][original] = variations
            data["metadata"]["last_updated"] = datetime.now().isoformat()

            # Save updated data
            with user_variations_file.open("w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

            # Reload patterns
            self.reload_japanese_variations()
            return True

        except Exception as e:
            print(f"Failed to add Japanese variation: {e}")
            return False

    def export_japanese_variations(self, export_path: Path) -> bool:
        """Export current Japanese variations to a file."""
        try:
            user_variations_file = self.config_dir / "japanese_variations.yaml"
            if user_variations_file.exists():
                shutil.copy2(user_variations_file, export_path)
                return True
            return False
        except Exception as e:
            print(f"Failed to export Japanese variations: {e}")
            return False

    def import_japanese_variations(self, import_path: Path) -> bool:
        """Import Japanese variations from a file."""
        try:
            if not import_path.exists():
                return False

            # Validate the imported file
            with import_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Basic validation
            if not isinstance(data, dict):
                return False

            # Copy to user config
            user_variations_file = self.config_dir / "japanese_variations.yaml"
            shutil.copy2(import_path, user_variations_file)

            # Reload patterns
            self.reload_japanese_variations()
            return True

        except Exception as e:
            print(f"Failed to import Japanese variations: {e}")
            return False

    def add_pattern(
        self,
        category_name: str,
        pattern_name: str,
        tag_name: str,
        keywords: list[str],
        description: str | None = None,
        confidence_weight: float = 1.0,
        subcategory: str | None = None,
    ) -> None:
        """Add a new tag pattern."""
        if category_name not in self.categories:
            self.categories[category_name] = TagPatternCategory(
                name=category_name,
                description=f"Category: {category_name}",
            )

        pattern = TagPattern(
            tag_name=tag_name,
            keywords=keywords,
            category=category_name,
            subcategory=subcategory,
            description=description,
            confidence_weight=confidence_weight,
        )

        self.categories[category_name].patterns[pattern_name] = pattern
        self.save_patterns()

    def update_pattern(
        self,
        category_name: str,
        pattern_name: str,
        **updates: Any,
    ) -> bool:
        """Update an existing tag pattern."""
        if (
            category_name in self.categories
            and pattern_name in self.categories[category_name].patterns
        ):
            pattern = self.categories[category_name].patterns[pattern_name]

            for field, value in updates.items():
                if hasattr(pattern, field):
                    setattr(pattern, field, value)

            pattern.updated_at = datetime.now()
            self.save_patterns()
            return True

        return False

    def remove_pattern(self, category_name: str, pattern_name: str) -> bool:
        """Remove a tag pattern."""
        if (
            category_name in self.categories
            and pattern_name in self.categories[category_name].patterns
        ):
            del self.categories[category_name].patterns[pattern_name]
            self.save_patterns()
            return True

        return False

    def get_all_patterns(self) -> dict[str, TagPatternCategory]:
        """Get all tag patterns organized by category."""
        return self.categories

    def search_patterns(self, query: str) -> list[TagPattern]:
        """Search for patterns by keyword or tag name."""
        results = []
        query_lower = query.lower()

        for category in self.categories.values():
            for pattern in category.patterns.values():
                # Search in tag name
                if query_lower in pattern.tag_name.lower():
                    results.append(pattern)
                    continue

                # Search in keywords
                if any(query_lower in keyword.lower() for keyword in pattern.keywords):
                    results.append(pattern)
                    continue

                # Search in description
                if pattern.description and query_lower in pattern.description.lower():
                    results.append(pattern)

        return results

    def suggest_tags_for_content(self, content: str) -> list[tuple[str, float]]:
        """Suggest tags for content with Japanese variation support."""
        content_lower = content.lower()
        suggestions = []

        for category in sorted(
            self.categories.values(), key=lambda c: c.priority, reverse=True
        ):
            for pattern in category.patterns.values():
                keyword_matches = 0

                # Check direct keyword matches
                for keyword in pattern.keywords:
                    if keyword in content_lower:
                        keyword_matches += 1
                    else:
                        # Check Japanese variations
                        variations = self.find_japanese_variations(keyword)
                        for variation in variations:
                            if variation.lower() in content_lower:
                                keyword_matches += 1
                                break  # Count each keyword only once

                if keyword_matches > 0:
                    # Calculate confidence score
                    confidence = min(
                        0.95, (keyword_matches * 0.2 * pattern.confidence_weight)
                    )

                    if confidence > 0.3:  # Minimum confidence threshold
                        suggestions.append((pattern.tag_name, confidence))

                        # Update usage count
                        pattern.usage_count += 1

        # Sort by confidence score
        suggestions.sort(key=lambda x: x[1], reverse=True)
        return suggestions

    def analyze_vault_tags(self, files: list[Any]) -> VaultTagAnalysis:
        """Analyze existing tags in the vault."""
        # Import here to avoid circular imports
        from ..models import MarkdownFile

        tag_frequency = {}
        tag_cooccurrence = {}
        total_files = len(files)
        total_tags = 0

        # Count tag occurrences and co-occurrences
        for file in files:
            if isinstance(file, MarkdownFile) and file.frontmatter.tags:
                file_tags = set(file.frontmatter.tags)
                total_tags += len(file_tags)

                for tag in file_tags:
                    tag_frequency[tag] = tag_frequency.get(tag, 0) + 1

                    if tag not in tag_cooccurrence:
                        tag_cooccurrence[tag] = {}

                    # Count co-occurrences
                    for other_tag in file_tags:
                        if other_tag != tag:
                            tag_cooccurrence[tag][other_tag] = (
                                tag_cooccurrence[tag].get(other_tag, 0) + 1
                            )

        # Calculate relationships
        tag_relationships = {}
        for tag, cooccurrences in tag_cooccurrence.items():
            tag_relationships[tag] = {}
            tag_frequency_val = tag_frequency[tag]

            for related_tag, count in cooccurrences.items():
                strength = count / tag_frequency_val
                tag_relationships[tag][related_tag] = strength

        # Find most common tags and orphaned tags
        most_common_tags = sorted(
            tag_frequency.items(), key=lambda x: x[1], reverse=True
        )
        orphaned_tags = [tag for tag, count in tag_frequency.items() if count == 1]

        analysis = VaultTagAnalysis(
            total_files=total_files,
            total_tags=total_tags,
            unique_tags=len(tag_frequency),
            tag_frequency=tag_frequency,
            tag_cooccurrence=tag_cooccurrence,
            tag_relationships=tag_relationships,
            most_common_tags=most_common_tags[:50],  # Top 50
            orphaned_tags=orphaned_tags,
        )

        self.vault_analysis = analysis
        self.save_vault_analysis()
        return analysis

    def get_related_tags(
        self, tag: str, min_strength: float = 0.3
    ) -> list[tuple[str, float]]:
        """Get tags related to the given tag."""
        if not self.vault_analysis or tag not in self.vault_analysis.tag_relationships:
            return []

        relationships = self.vault_analysis.tag_relationships[tag]
        related = [
            (related_tag, strength)
            for related_tag, strength in relationships.items()
            if strength >= min_strength
        ]

        return sorted(related, key=lambda x: x[1], reverse=True)

    def export_patterns_for_llm(self) -> dict[str, Any]:
        """Export patterns in a format suitable for LLM training/prompting."""
        export_data = {
            "metadata": {
                "total_categories": len(self.categories),
                "total_patterns": sum(
                    len(cat.patterns) for cat in self.categories.values()
                ),
                "exported_at": datetime.now().isoformat(),
            },
            "categories": {},
            "vault_analysis": self.vault_analysis.model_dump()
            if self.vault_analysis
            else None,
        }

        for category_name, category in self.categories.items():
            export_data["categories"][category_name] = {
                "description": category.description,
                "priority": category.priority,
                "patterns": [
                    {
                        "tag": pattern.tag_name,
                        "keywords": pattern.keywords,
                        "confidence_weight": pattern.confidence_weight,
                        "usage_count": pattern.usage_count,
                        "description": pattern.description,
                    }
                    for pattern in category.patterns.values()
                ],
            }

        return export_data

    def import_patterns_from_analysis(self, analysis_data: dict[str, Any]) -> None:
        """Import patterns from external analysis (e.g., LLM suggestions)."""
        for category_name, category_data in analysis_data.get("categories", {}).items():
            if category_name not in self.categories:
                self.categories[category_name] = TagPatternCategory(
                    name=category_name,
                    description=category_data.get("description", ""),
                    priority=category_data.get("priority", 5),
                )

            for pattern_data in category_data.get("patterns", []):
                pattern_name = pattern_data["tag"]
                pattern = TagPattern(
                    tag_name=pattern_data["tag"],
                    keywords=pattern_data["keywords"],
                    category=category_name,
                    description=pattern_data.get("description"),
                    confidence_weight=pattern_data.get("confidence_weight", 1.0),
                )

                self.categories[category_name].patterns[pattern_name] = pattern

        self.save_patterns()
