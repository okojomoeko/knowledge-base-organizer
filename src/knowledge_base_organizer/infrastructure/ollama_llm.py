"""
Ollama LLM Service Implementation

This module provides an implementation of the LLMService interface
using Ollama's llama3.2:3b model for LLM-based reasoning and content analysis.

Supports:
- Requirement 17.1: Intelligent frontmatter auto-enhancement
- Requirement 17.2: Content summarization
- Requirement 23.1: Concept-based automatic tagging and alias generation
- Requirement 24.1: Logical relationship analysis between content
"""

import json
import logging
import re
from typing import Any

import requests

from knowledge_base_organizer.domain.services.ai_services import (
    ConceptExtractionResult,
    LLMError,
    LLMService,
    MetadataSuggestion,
    ModelNotAvailableError,
    RelationshipAnalysis,
    SimilarityResult,
)

logger = logging.getLogger(__name__)


class OllamaLLMService(LLMService):
    """
    Ollama-based LLM service using llama3.2:3b model.

    This service connects to a local Ollama instance to perform
    LLM-based reasoning, content analysis, and metadata generation.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "qwen2.5:7b",
        timeout: int = 60,
        **options,
    ):
        """
        Initialize the Ollama LLM service.

        Args:
            base_url: Base URL for Ollama API (default: http://localhost:11434)
            model_name: Name of the LLM model (default: qwen2.5:7b)
            timeout: Request timeout in seconds (default: 60)
            **options: Additional options for Ollama (temperature, top_p, etc.)
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout
        self.options = {"temperature": 0.3, "top_p": 0.9, "top_k": 40, **options}
        self._model_info: dict[str, Any] | None = None

        # Verify Ollama is available and model is accessible
        self._verify_service_availability()

    def _verify_service_availability(self) -> None:
        """
        Verify that Ollama service is running and the model is available.

        Raises:
            ModelNotAvailableError: If Ollama service or model is not available
        """
        try:
            # Check if Ollama service is running
            response = requests.get(f"{self.base_url}/api/tags", timeout=self.timeout)
            response.raise_for_status()

            # Check if the LLM model is available
            models_data = response.json()
            available_models = [
                model["name"] for model in models_data.get("models", [])
            ]

            if self.model_name not in available_models:
                logger.warning(
                    f"Model {self.model_name} not found in available models: "
                    f"{available_models}"
                )
                # Try to pull the model
                self._pull_model()

        except requests.exceptions.RequestException as e:
            raise ModelNotAvailableError(
                f"Ollama service not available at {self.base_url}: {e}"
            ) from e

    def _pull_model(self) -> None:
        """
        Attempt to pull the LLM model if it's not available.

        Raises:
            ModelNotAvailableError: If model cannot be pulled
        """
        try:
            logger.info(f"Attempting to pull model: {self.model_name}")
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model_name},
                timeout=600,  # Longer timeout for model pulling (10 minutes)
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled model: {self.model_name}")

        except requests.exceptions.RequestException as e:
            raise ModelNotAvailableError(
                f"Failed to pull model {self.model_name}: {e}"
            ) from e

    def _generate_completion(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        """
        Generate a completion using the Ollama generate API.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context

        Returns:
            Generated text response

        Raises:
            LLMError: If generation fails
        """
        try:
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": self.options,
            }

            if system_prompt:
                request_data["system"] = system_prompt

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_data,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()
            generated_text = data.get("response", "").strip()

            if not generated_text:
                raise LLMError("No response generated from Ollama")

            return generated_text

        except requests.exceptions.RequestException as e:
            raise LLMError(f"Failed to generate completion: {e}") from e
        except (KeyError, json.JSONDecodeError) as e:
            raise LLMError(f"Invalid response from Ollama: {e}") from e

    def extract_concepts(self, content: str) -> ConceptExtractionResult:
        """
        Extract core concepts from content for tagging and categorization.

        Supports Requirement 23.1: Concept-based automatic tagging.

        Args:
            content: Text content to analyze

        Returns:
            ConceptExtractionResult with extracted concepts and confidence scores
        """
        if not content.strip():
            return ConceptExtractionResult(
                concepts=[],
                confidence_scores=[],
                context="Empty content provided",
            )

        system_prompt = (
            "You are an expert at extracting key concepts from text content "
            "for knowledge management. Extract 3-5 core concepts that would be "
            "useful as tags or categories. Focus on main topics and themes, "
            "technical terms and concepts, domain-specific terminology, "
            "important entities or subjects. Return only the concepts as a "
            "comma-separated list, nothing else."
        )

        prompt = (
            f"Extract the core concepts from this content:\n\n"
            f"{content[:2000]}\n\nConcepts:"
        )

        try:
            response = self._generate_completion(prompt, system_prompt)

            # Parse the response to extract concepts
            concepts = [
                concept.strip() for concept in response.split(",") if concept.strip()
            ]

            # Limit to 5 concepts maximum
            concepts = concepts[:5]

            # Generate confidence scores based on concept clarity and relevance
            confidence_scores = [
                self._calculate_concept_confidence(concept, content)
                for concept in concepts
            ]

            return ConceptExtractionResult(
                concepts=concepts,
                confidence_scores=confidence_scores,
                context=content[:500],  # Store first 500 chars as context
            )

        except LLMError:
            # Re-raise LLM errors
            raise
        except Exception as e:
            raise LLMError(f"Failed to extract concepts: {e}") from e

    def suggest_metadata(
        self, content: str, existing_metadata: dict[str, Any] | None = None
    ) -> MetadataSuggestion:
        """
        Generate intelligent metadata suggestions for frontmatter enhancement.

        Supports Requirement 17.1: Intelligent frontmatter auto-enhancement.

        Args:
            content: Note content to analyze
            existing_metadata: Current frontmatter metadata

        Returns:
            MetadataSuggestion with tags, aliases, and description
        """
        if not content.strip():
            return MetadataSuggestion(
                suggested_tags=[],
                suggested_aliases=[],
                suggested_description=None,
                confidence_scores={},
            )

        existing_metadata = existing_metadata or {}

        system_prompt = (
            "You are an expert at analyzing content and suggesting metadata "
            "for knowledge management. Analyze the content and suggest: "
            "1. Relevant tags (3-5 keywords/topics), "
            "2. Alternative names/aliases (2-3 variations), "
            "3. A concise description (1-2 sentences). "
            "Consider the existing metadata to avoid duplicates. "
            "Return your suggestions in this format: "
            "TAGS: tag1, tag2, tag3 "
            "ALIASES: alias1, alias2, alias3 "
            "DESCRIPTION: A concise description of the content."
        )

        existing_info = ""
        if existing_metadata:
            existing_info = (
                f"\nExisting metadata: {json.dumps(existing_metadata, indent=2)}"
            )

        prompt = (
            f"Analyze this content and suggest metadata:{existing_info}\n\n"
            f"Content:\n{content[:2000]}\n\nSuggestions:"
        )

        try:
            response = self._generate_completion(prompt, system_prompt)

            # Parse the structured response
            suggested_tags = self._extract_section(response, "TAGS")
            suggested_aliases = self._extract_section(response, "ALIASES")
            suggested_description = self._extract_section(
                response, "DESCRIPTION", single_value=True
            )

            # Calculate confidence scores
            confidence_scores = {
                "tags": 0.8,  # Generally reliable for tag suggestions
                "aliases": 0.7,  # Moderate confidence for aliases
                "description": 0.9 if suggested_description else 0.0,
            }

            return MetadataSuggestion(
                suggested_tags=suggested_tags,
                suggested_aliases=suggested_aliases,
                suggested_description=suggested_description,
                confidence_scores=confidence_scores,
            )

        except LLMError:
            # Re-raise LLM errors
            raise
        except Exception as e:
            raise LLMError(f"Failed to suggest metadata: {e}") from e

    def summarize_content(self, content: str, max_length: int = 100) -> str:
        """
        Generate a concise summary of the content.

        Args:
            content: Text content to summarize
            max_length: Maximum length of summary in characters

        Returns:
            Generated summary text
        """
        if not content.strip():
            return ""

        system_prompt = (
            f"You are an expert at creating concise summaries. "
            f"Create a summary that captures the main points and key information. "
            f"Keep the summary under {max_length} characters. "
            f"Focus on the most important concepts and conclusions."
        )

        prompt = f"Summarize this content concisely:\n\n{content[:3000]}\n\nSummary:"

        try:
            response = self._generate_completion(prompt, system_prompt)

            # Truncate if necessary while preserving sentence boundaries
            if len(response) > max_length:
                # Find the last complete sentence within the limit
                truncated = response[:max_length]
                last_period = truncated.rfind(".")
                if (
                    last_period > max_length // 2
                ):  # Only truncate if we keep at least half
                    response = truncated[: last_period + 1]
                else:
                    response = truncated + "..."

            return response

        except LLMError:
            # Re-raise LLM errors
            raise
        except Exception as e:
            raise LLMError(f"Failed to summarize content: {e}") from e

    def analyze_relationship(
        self, content_a: str, content_b: str
    ) -> RelationshipAnalysis:
        """
        Analyze logical relationships between two pieces of content.

        Supports Requirement 24: Logical relationship identification.

        Args:
            content_a: First content for comparison
            content_b: Second content for comparison

        Returns:
            RelationshipAnalysis with relationship type and confidence
        """
        if not content_a.strip() or not content_b.strip():
            return RelationshipAnalysis(
                relationship_type="UNRELATED",
                confidence=0.0,
                explanation="One or both contents are empty",
                bidirectional=False,
            )

        system_prompt = (
            "You are an expert at analyzing logical relationships between content. "
            "Identify the relationship type between two pieces of content. "
            "Possible types: PREMISE, EXAMPLE, CONTRADICTION, DETAIL, "
            "ELABORATION, PARALLEL, UNRELATED. "
            "Return format: RELATIONSHIP: [type] CONFIDENCE: [0.0-1.0] "
            "BIDIRECTIONAL: [true/false] EXPLANATION: [brief explanation]"
        )

        prompt = (
            f"Analyze the logical relationship between these contents:\n\n"
            f"Content A:\n{content_a[:1500]}\n\n"
            f"Content B:\n{content_b[:1500]}\n\nAnalysis:"
        )

        try:
            response = self._generate_completion(prompt, system_prompt)

            # Parse the structured response
            relationship_type = (
                self._extract_section(response, "RELATIONSHIP", single_value=True)
                or "UNRELATED"
            )
            confidence_str = (
                self._extract_section(response, "CONFIDENCE", single_value=True)
                or "0.0"
            )
            bidirectional_str = (
                self._extract_section(response, "BIDIRECTIONAL", single_value=True)
                or "false"
            )
            explanation = (
                self._extract_section(response, "EXPLANATION", single_value=True)
                or "No explanation provided"
            )

            # Parse confidence as float
            try:
                confidence = float(confidence_str)
                confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
            except ValueError:
                confidence = 0.5  # Default confidence

            # Parse bidirectional as boolean
            bidirectional = bidirectional_str.lower() in ("true", "yes", "1")

            return RelationshipAnalysis(
                relationship_type=relationship_type.upper(),
                confidence=confidence,
                explanation=explanation,
                bidirectional=bidirectional,
            )

        except LLMError:
            # Re-raise LLM errors
            raise
        except Exception as e:
            raise LLMError(f"Failed to analyze relationship: {e}") from e

    def evaluate_context_match(
        self, candidate_text: str, source_context: str, target_content: str
    ) -> SimilarityResult:
        """
        Evaluate if a link candidate matches the context appropriately.

        Supports Requirement 13.1, 13.2: Context-aware linking.

        Args:
            candidate_text: Text that could become a link
            source_context: Surrounding context in source document
            target_content: Content of potential target document

        Returns:
            SimilarityResult indicating context match quality
        """
        if not all(
            [
                candidate_text.strip(),
                source_context.strip(),
                target_content.strip(),
            ]
        ):
            return SimilarityResult(
                score=0.0,
                confidence=0.0,
                context_match=False,
            )

        system_prompt = (
            "You are an expert at evaluating text references in context. "
            "Analyze if the candidate text would appropriately link to the target. "
            "Consider semantic relevance, contextual appropriateness, "
            "domain alignment. "
            "Return format: SCORE: [0.0-1.0] CONFIDENCE: [0.0-1.0] "
            "MATCH: [true/false] REASONING: [brief explanation]"
        )

        prompt = (
            f"Evaluate this potential link:\n\n"
            f'Candidate text: "{candidate_text}"\n\n'
            f"Source context:\n{source_context[:800]}\n\n"
            f"Target content:\n{target_content[:800]}\n\nEvaluation:"
        )

        try:
            response = self._generate_completion(prompt, system_prompt)

            # Parse the structured response
            score_str = (
                self._extract_section(response, "SCORE", single_value=True) or "0.0"
            )
            confidence_str = (
                self._extract_section(response, "CONFIDENCE", single_value=True)
                or "0.0"
            )
            match_str = (
                self._extract_section(response, "MATCH", single_value=True) or "false"
            )

            # Parse values
            try:
                score = float(score_str)
                score = max(0.0, min(1.0, score))
            except ValueError:
                score = 0.0

            try:
                confidence = float(confidence_str)
                confidence = max(0.0, min(1.0, confidence))
            except ValueError:
                confidence = 0.0

            context_match = match_str.lower() in ("true", "yes", "1")

            return SimilarityResult(
                score=score,
                confidence=confidence,
                context_match=context_match,
            )

        except LLMError:
            # Re-raise LLM errors
            raise
        except Exception as e:
            raise LLMError(f"Failed to evaluate context match: {e}") from e

    def disambiguate_targets(
        self,
        candidate_text: str,
        source_context: str,
        target_options: list[tuple[str, str]],
    ) -> list[tuple[str, float]]:
        """
        Rank multiple potential link targets by contextual relevance.

        Supports Requirement 14: Link disambiguation.

        Args:
            candidate_text: Text that could become a link
            source_context: Context around the candidate text
            target_options: List of (target_id, target_content) tuples

        Returns:
            List of (target_id, confidence_score) tuples, ranked by relevance
        """
        if (
            not target_options
            or not candidate_text.strip()
            or not source_context.strip()
        ):
            return []

        system_prompt = (
            "You are an expert at disambiguating link targets based on context. "
            "Rank the potential targets by relevance. "
            "For each target, provide a relevance score from 0.0 to 1.0. "
            "Consider semantic similarity, domain alignment, "
            "contextual appropriateness. "
            "Return format: TARGET_1: [score] TARGET_2: [score] etc."
        )

        # Prepare target descriptions
        target_descriptions = []
        for i, (target_id, target_content) in enumerate(target_options):
            target_descriptions.append(
                f"TARGET_{i + 1} ({target_id}): {target_content[:500]}"
            )

        targets_text = "\n\n".join(target_descriptions)

        prompt = (
            f"Rank these targets for the candidate text:\n\n"
            f'Candidate text: "{candidate_text}"\n\n'
            f"Source context:\n{source_context[:800]}\n\n"
            f"Potential targets:\n{targets_text}\n\nRankings:"
        )

        try:
            response = self._generate_completion(prompt, system_prompt)

            # Parse rankings
            rankings = []
            for i, (target_id, _) in enumerate(target_options):
                target_key = f"TARGET_{i + 1}"
                score_str = self._extract_section(
                    response, target_key, single_value=True
                )

                try:
                    score = float(score_str) if score_str else 0.0
                    score = max(0.0, min(1.0, score))
                except ValueError:
                    score = 0.0

                rankings.append((target_id, score))

            # Sort by score (descending)
            rankings.sort(key=lambda x: x[1], reverse=True)

            return rankings

        except LLMError:
            # Re-raise LLM errors
            raise
        except Exception as e:
            raise LLMError(f"Failed to disambiguate targets: {e}") from e

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the LLM model.

        Returns:
            Dictionary with model name, capabilities, and configuration
        """
        if self._model_info is None:
            try:
                # Get model information from Ollama
                response = requests.post(
                    f"{self.base_url}/api/show",
                    json={"name": self.model_name},
                    timeout=self.timeout,
                )
                response.raise_for_status()

                model_data = response.json()

                self._model_info = {
                    "model_name": self.model_name,
                    "base_url": self.base_url,
                    "capabilities": [
                        "concept_extraction",
                        "metadata_suggestion",
                        "content_summarization",
                        "relationship_analysis",
                        "context_evaluation",
                        "target_disambiguation",
                    ],
                    "model_details": model_data.get("details", {}),
                    "parameters": model_data.get("parameters", {}),
                    "timeout": self.timeout,
                }

            except requests.exceptions.RequestException as e:
                logger.warning(f"Could not retrieve model info: {e}")
                self._model_info = {
                    "model_name": self.model_name,
                    "base_url": self.base_url,
                    "capabilities": ["basic_generation"],
                    "error": str(e),
                }

        return self._model_info.copy()

    def _extract_section(
        self, text: str, section_name: str, single_value: bool = False
    ) -> list[str] | str | None:
        """
        Extract a section from structured LLM response.

        Args:
            text: Response text to parse
            section_name: Name of the section to extract
            single_value: If True, return single string; if False, return list

        Returns:
            Extracted section content as list or string
        """
        pattern = rf"{section_name}:\s*(.+?)(?=\n[A-Z_]+:|$)"
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if not match:
            return None if single_value else []

        content = match.group(1).strip()

        if single_value:
            return content

        # Split by comma and clean up
        return [item.strip() for item in content.split(",") if item.strip()]

    def _calculate_concept_confidence(self, concept: str, content: str) -> float:
        """
        Calculate confidence score for an extracted concept.

        Args:
            concept: The extracted concept
            content: Original content

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence
        confidence = 0.5

        # Boost if concept appears in content
        if concept.lower() in content.lower():
            confidence += 0.3

        # Boost for longer, more specific concepts
        if len(concept) > 10:
            confidence += 0.1

        # Boost for technical-looking terms
        if any(char.isupper() for char in concept) or "_" in concept or "-" in concept:
            confidence += 0.1

        return min(1.0, confidence)
