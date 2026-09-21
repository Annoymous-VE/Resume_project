import abc
import json
import logging
import re
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class BaseLLMClient(abc.ABC):
    @abc.abstractmethod
    async def generate_structured(self, prompt: str, schema: Type[T], system_prompt: Optional[str] = None) -> T:
        """Generate structured output adhering to a Pydantic schema."""
        pass

    @abc.abstractmethod
    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate freeform text."""
        pass

class MockLLMClient(BaseLLMClient):
    """Deterministic fallback and mock client for offline running and automated tests."""

    async def generate_structured(self, prompt: str, schema: Type[T], system_prompt: Optional[str] = None) -> T:
        schema_name = schema.__name__

        if schema_name == "ProjectExtractionResult":
            # Extract basic project entities from text if present
            from app.ai.schemas.project import ProjectExtractionResult, ExtractedProject
            return schema(
                projects=[
                    ExtractedProject(
                        id="proj_1",
                        name="Distributed Task Orchestrator",
                        description="High-throughput distributed workflow engine for asynchronous event dispatching.",
                        technologies=["Python", "Redis", "FastAPI", "Docker"],
                        contributions=["Designed DAG execution scheduler", "Implemented worker failure recovery"],
                        outcomes=["Processed 25,000 tasks/min with sub-second latency"],
                        links=["https://github.com/example/orchestrator"],
                        source_blocks=["block_1", "block_2"],
                        confidence=0.95
                    ),
                    ExtractedProject(
                        id="proj_2",
                        name="Real-Time Analytics Pipeline",
                        description="Streaming telemetry processing platform with anomaly detection.",
                        technologies=["Go", "Kafka", "PostgreSQL", "Prometheus"],
                        contributions=["Built consumer group processing cluster", "Optimized windowing aggregations"],
                        outcomes=["Reduced alert latency from 30s to 800ms"],
                        links=[],
                        source_blocks=["block_3"],
                        confidence=0.90
                    )
                ],
                extraction_summary="Extracted 2 technical projects from resume document blocks."
            )

        if schema_name == "InitialQuestionsResult":
            from app.ai.schemas.question import InitialQuestionsResult, GeneratedQuestion
            return schema(
                questions=[
                    GeneratedQuestion(
                        id="q_prob_1",
                        target_area="problem",
                        question="What specific operational bottlenecks or business problem motivated building this architecture?",
                        rationale="Establishes real-world context and core engineering motivation."
                    ),
                    GeneratedQuestion(
                        id="q_arch_1",
                        target_area="architecture",
                        question="Could you detail the internal component architecture and how data flows across the system?",
                        rationale="Uncovers component boundaries, communication protocols, and message patterns."
                    ),
                    GeneratedQuestion(
                        id="q_dec_1",
                        target_area="technical_decisions",
                        question="What key tradeoffs led to selecting this particular tech stack over alternatives?",
                        rationale="Surfaces architectural justification and decision-making rigor."
                    )
                ]
            )

        if schema_name == "FollowUpQuestionResult":
            from app.ai.schemas.question import FollowUpQuestionResult, GeneratedQuestion
            from app.ai.schemas.knowledge import CoverageLevel

            # Check if answer mentions challenges or performance
            return schema(
                has_next_question=True,
                question=GeneratedQuestion(
                    id="q_chal_1",
                    target_area="challenges",
                    question="What was the most unexpected technical failure or scale barrier encountered in production, and how did you resolve it?",
                    rationale="Deep-dives into problem solving and resilience engineering."
                ),
                coverage_update={
                    "problem": CoverageLevel.SUFFICIENT,
                    "architecture": CoverageLevel.PARTIAL
                }
            )

        # Generic default
        return schema()

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return "# Technical Case Study\n\n## Overview\nGenerated technical case study analysis."

class GeminiLLMClient(BaseLLMClient):
    DEFAULT_FALLBACK_MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.6-flash",
        "gemini-flash-latest"
    ]

    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash-lite"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        # Build prioritized models list without duplicates
        models = [model_name] + [m for m in self.DEFAULT_FALLBACK_MODELS if m != model_name]
        self.candidate_models = models

    async def generate_structured(self, prompt: str, schema: Type[T], system_prompt: Optional[str] = None) -> T:
        import asyncio
        import time
        from google.genai import types
        loop = asyncio.get_running_loop()

        def _call():
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            )
            if system_prompt:
                config.system_instruction = system_prompt

            last_error: Optional[Exception] = None
            for model_id in self.candidate_models:
                for attempt in range(2):
                    try:
                        response = self.client.models.generate_content(
                            model=model_id,
                            contents=prompt,
                            config=config
                        )
                        raw_text = response.text or ""
                        # Strip markdown JSON fences if present
                        cleaned_text = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.I)
                        cleaned_text = re.sub(r"\s*```$", "", cleaned_text).strip()
                        return schema.model_validate_json(cleaned_text)
                    except Exception as e:
                        last_error = e
                        err_str = str(e)
                        is_transient = any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])
                        if is_transient and attempt == 0:
                            logger.warning("Gemini model %s transient error: %s. Retrying in 2s...", model_id, err_str[:150])
                            time.sleep(2)
                            continue
                        logger.warning("Gemini model %s failed: %s. Trying next candidate model...", model_id, err_str[:150])
                        break  # Move to next fallback model

            if last_error:
                raise last_error
            raise RuntimeError("All Gemini candidate models failed to generate structured output.")

        return await loop.run_in_executor(None, _call)

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        import asyncio
        import time
        from google.genai import types
        loop = asyncio.get_running_loop()

        def _call():
            config = types.GenerateContentConfig()
            if system_prompt:
                config.system_instruction = system_prompt

            last_error: Optional[Exception] = None
            for model_id in self.candidate_models:
                for attempt in range(2):
                    try:
                        response = self.client.models.generate_content(
                            model=model_id,
                            contents=prompt,
                            config=config
                        )
                        return response.text or ""
                    except Exception as e:
                        last_error = e
                        err_str = str(e)
                        is_transient = any(code in err_str for code in ["503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED"])
                        if is_transient and attempt == 0:
                            time.sleep(2)
                            continue
                        logger.warning("Gemini model %s text generation failed: %s. Trying fallback...", model_id, err_str[:150])
                        break

            if last_error:
                raise last_error
            return ""

        return await loop.run_in_executor(None, _call)

class OpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, base_url: Optional[str] = None, model_name: str = "gpt-4o"):
        from openai import AsyncOpenAI
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = AsyncOpenAI(**kwargs)
        self.model_name = model_name

    async def generate_structured(self, prompt: str, schema: Type[T], system_prompt: Optional[str] = None) -> T:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.beta.chat.completions.parse(
            model=self.model_name,
            messages=messages,
            response_format=schema,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("Failed to parse structured output from OpenAI model.")
        return parsed

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )
        return response.choices[0].message.content or ""

def get_llm_client() -> BaseLLMClient:
    """Factory to retrieve the configured LLM client."""
    provider = settings.LLM_PROVIDER.lower()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        return GeminiLLMClient(api_key=settings.GEMINI_API_KEY, model_name=settings.LLM_MODEL or "gemini-3.5-flash-lite")
    elif provider == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMClient(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_BASE_URL or None, model_name=settings.LLM_MODEL or "gpt-4o")
    else:
        logger.info("Using MockLLMClient (no API keys provided or LLM_PROVIDER=mock)")
        return MockLLMClient()
