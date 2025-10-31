"""
OpenAI-Compatible LLM Service Implementation

This module provides an implementation of the LLMService interface
using OpenAI-compatible APIs (like LM Studio, LocalAI, etc.).

Supports the same features as OllamaLLMService but uses OpenAI API format.
"""

import json
import logging
import re
from typing import Any

import requests
from requests.exceptions import RequestException

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


class OpenAICompatibleLLMService(LLMService):
    """
    OpenAI-compatible LLM service for LM Studio, LocalAI, and similar providers.

    This service connects to OpenAI-compatible APIs to perform
    LLM-based reasoning, content analysis, and metadata generation.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:1234",
        model_name: str = "local-model",
        api_key: str | None = None,
        timeout: int = 60,
        **options,
    ):
        """
        Initialize the OpenAI-compatible LLM service.

        Args:
            base_url: Base URL for the API (default: http://localhost:1234 for LM Studio)
            model_name: Name of the LLM model (default: local-model)
            api_key: API key if required (optional for local services)
            timeout: Request timeout in seconds (default: 60)
            **options: Additional options (temperature, max_tokens, etc.)
        """
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.api_key = api_key
        self.timeout = timeout
        self.options = {"temperature": 0.3, "max_tokens": 2048, "top_p": 0.9, **options}
        self._model_info: dict[str, Any] | None = None

        # Verify service availability
        self._verify_service_availability()

    def _verify_service_availability(self) -> None:
        """
        Verify that the OpenAI-compatible service is running and accessible.

        Raises:
            ModelNotAvailableError: If service is not available
        """
        try:
            # Try to get models list
            headers = self._get_headers()
            response = requests.get(
                f"{self.base_url}/v1/models", headers=headers, timeout=self.timeout
            )
            response.raise_for_status()

            # Check if our model is available
            models_data = response.json()
            available_models = [model["id"] for model in models_data.get("data", [])]

            if available_models and self.model_name not in available_models:
                logger.warning(
                    f"Model {self.model_name} not found in available models: "
                    f"{available_models}. Using first available model."
                )
                # Use the first available model if specified model not found
                if available_models:
                    self.model_name = available_models[0]

        except RequestException as e:
            raise ModelNotAvailableError(
                f"OpenAI-compatible service not available at {self.base_url}: {e}"
            ) from e

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return headers

    def _generate_completion(
        self, prompt: str, system_prompt: str | None = None
    ) -> str:
        """
        Generate a completion using the OpenAI-compatible chat API.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt for context

        Returns:
            Generated text response

        Raises:
            LLMError: If generation fails
        """
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            request_data = {
                "model": self.model_name,
                "messages": messages,
                **self.options,
            }

            headers = self._get_headers()
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=request_data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            data = response.json()

            if "choices" not in data or not data["choices"]:
                raise LLMError("No response choices returned from API")

            generated_text = data["choices"][0]["message"]["content"].strip()

            if not generated_text:
                raise LLMError("Empty response generated from API")

            return generated_text

        except RequestException as e:
            raise LLMError(f"Failed to generate completion: {e}") from e
        except (KeyError, json.JSONDecodeError) as e:
            raise LLMError(f"Invalid response from API: {e}") from e

    def extract_concepts(self, content: str) -> ConceptExtractionResult:
        """
        Extract core concepts from content for tagging and categorization.

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
            relationship_type_raw = (
                self._extract_section(response, "RELATIONSHIP", single_value=True)
                or "UNRELATED"
            )
            # Extract just the relationship type (first word)
            relationship_type = (
                relationship_type_raw.split()[0]
                if relationship_type_raw
                else "UNRELATED"
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

            # Parse rankings using regex to extract scores
            rankings = []
            for i, (target_id, _) in enumerate(target_options):
                target_key = f"TARGET_{i + 1}"
                # Look for pattern like "TARGET_1: 0.9"
                pattern = rf"{target_key}:\s*([0-9.]+)"
                match = re.search(pattern, response)

                if match:
                    try:
                        score = float(match.group(1))
                        score = max(0.0, min(1.0, score))
                    except ValueError:
                        score = 0.0
                else:
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
                # Get model information from API
                headers = self._get_headers()
                response = requests.get(
                    f"{self.base_url}/v1/models",
                    headers=headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()

                models_data = response.json()
                model_details = {}

                # Find our specific model
                for model in models_data.get("data", []):
                    if model["id"] == self.model_name:
                        model_details = model
                        break

                self._model_info = {
                    "model_name": self.model_name,
                    "base_url": self.base_url,
                    "api_format": "openai",
                    "capabilities": [
                        "concept_extraction",
                        "metadata_suggestion",
                        "content_summarization",
                        "relationship_analysis",
                        "context_evaluation",
                        "target_disambiguation",
                    ],
                    "model_details": model_details,
                    "options": self.options,
                    "timeout": self.timeout,
                }

            except RequestException as e:
                logger.warning(f"Could not retrieve model info: {e}")
                self._model_info = {
                    "model_name": self.model_name,
                    "base_url": self.base_url,
                    "api_format": "openai",
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
        # Look for the section with proper boundary detection
        pattern = rf"{section_name}:\s*([^A-Z_\n]+?)(?=\s+[A-Z_]+\s*:|$)"
        match = re.search(pattern, text, re.IGNORECASE)

        # If not found, try simpler pattern
        if not match:
            pattern = rf"{section_name}:\s*(.+?)(?=\s+[A-Z_]+:|$)"
            match = re.search(pattern, text, re.IGNORECASE)

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
            confidence += 0.1

        # Boost for longer, more specific concepts
        if len(concept) > 10:
            confidence += 0.1

        # Boost for technical-looking terms
        if any(char.isupper() for char in concept) or "_" in concept or "-" in concept:
            confidence += 0.1

        return min(1.0, confidence)
