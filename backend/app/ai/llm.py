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

        if schema_name == "ExtractedAnswerFacts":
            from app.ai.schemas.knowledge import ExtractedAnswerFacts, ExtractedFactItem
            facts = []
            lower_prompt = prompt.lower()
            # Extract target area or any detected topics
            lines = [line.strip("- *• \t\r\n") for line in prompt.split("\n") if len(line.strip()) > 5]
            ans_text = ""
            if '"""' in prompt:
                parts = prompt.split('"""')
                if len(parts) >= 2:
                    ans_text = parts[1].strip()
            if not ans_text:
                ans_text = lines[-1] if lines else "Provided project details."

            # Do not extract facts if the user is asking a question or requesting clarification / verifying understanding
            from app.services.interview_engine import InterviewEngine
            ans_clean = ans_text.lower().strip()
            is_question_or_clarification = (
                InterviewEngine.is_clarification_intent(ans_text)
                or "?" in ans_clean
                or any(phrase in ans_clean for phrase in [
                    "what do you mean", "can you explain", "could you explain", "don't understand",
                    "dont understand", "i'm confused", "im confused", "what does", "give me an example",
                    "what should i", "how should i", "what part", "help me", "rephrase", "simplify",
                    "do you mean", "are you asking", "is this about", "does this refer"
                ])
            )
            if is_question_or_clarification:
                return schema(facts=[], obstacle_mitigations=[])

            obstacle_mitigations = []
            from app.services.interview_engine import InterviewEngine
            is_dismissive = InterviewEngine.is_dismissive_reply(ans_text)

            # Categorize heuristically for mock
            if any(w in ans_text.lower() for w in ["latency", "speed", "ms", "sec", "%", "throughput", "rpm", "qps", "faster"]):
                facts.append(ExtractedFactItem(category="performance", fact=ans_text))
            if not is_dismissive and any(w in ans_text.lower() for w in ["bug", "issue", "bottleneck", "fail", "timeout", "challenge", "hard", "error", "obstacle", "deadlock", "rate limit", "slow query"]):
                facts.append(ExtractedFactItem(category="challenges", fact=ans_text))
                from app.ai.schemas.knowledge import ObstacleMitigationPair
                measures = None
                if any(w in ans_text.lower() for w in ["resolved", "fixed", "optimized", "implemented", "mitigated", "refactored", "solution", "reduced", "switched", "added", "decouple"]):
                    measures = "Implemented architectural mitigations, caching, and query optimization."
                obstacle_mitigations.append(ObstacleMitigationPair(
                    obstacle=ans_text,
                    root_cause="High contention and unindexed queries under peak traffic.",
                    measures_taken=measures,
                    outcome="Eliminated database deadlocks and restored sub-50ms latency."
                ))
            if any(w in ans_text.lower() for w in ["decided", "chose", "selected", "instead of", "tradeoff", "versus", "vs"]):
                facts.append(ExtractedFactItem(category="technical_decisions", fact=ans_text))
            if any(w in ans_text.lower() for w in ["flow", "queue", "api", "database", "redis", "fastapi", "service", "pipeline", "component"]):
                facts.append(ExtractedFactItem(category="architecture", fact=ans_text))
            
            if not facts and not obstacle_mitigations:
                # Default to architecture or problem
                facts.append(ExtractedFactItem(category="architecture", fact=ans_text))
            return schema(facts=facts, obstacle_mitigations=obstacle_mitigations)

        if schema_name == "InitialQuestionsResult":
            from app.ai.schemas.question import InitialQuestionsResult, GeneratedQuestion
            return schema(
                questions=[
                    GeneratedQuestion(
                        id="q_prob_1",
                        target_area="problem",
                        question="In a nutshell, what real-world problem or pain point was this built to solve?",
                        rationale="Clarifies the core motivation and problem statement in plain terms."
                    ),
                    GeneratedQuestion(
                        id="q_arch_1",
                        target_area="architecture",
                        question="How does data move through the system from start to finish? (A quick high-level summary is great!)",
                        rationale="Uncovers component flow and service interactions simply."
                    ),
                    GeneratedQuestion(
                        id="q_dec_1",
                        target_area="technical_decisions",
                        question="What was the main reason you picked this specific tech stack over other alternatives?",
                        rationale="Highlights key technical decision-making criteria."
                    )
                ]
            )

        if schema_name == "FollowUpQuestionResult":
            from app.ai.schemas.question import FollowUpQuestionResult, GeneratedQuestion
            from app.ai.schemas.knowledge import CoverageLevel
            import re

            # Extract target area from prompt if present
            target = "challenges"
            match = re.search(r"(?:Primary Missing Area to Target|Primary Topic to Explore|Target Topic to Explore|Target the missing area|Focus Area):\s*(\w+)", prompt, re.IGNORECASE)
            if not match:
                match = re.search(r"target_area:\s*(\w+)", prompt, re.IGNORECASE)
            if match:
                target = match.group(1).strip()

            if target == "challenges":
                ans_match = re.search(r"Candidate's Latest Answer:\s*([^\n\r]+)", prompt, re.IGNORECASE)
                cand_ans = ans_match.group(1).strip() if ans_match else ""
                from app.services.interview_engine import InterviewEngine
                if cand_ans and InterviewEngine.is_dismissive_reply(cand_ans):
                    q_text = (
                        "Even well-designed architectures face constraints like API rate limits, "
                        "database locks, slow queries, or third-party integration bugs. Which of these did you experience?"
                    )
                else:
                    q_text = "That makes sense. When building this out, what was the trickiest technical hurdle or bottleneck you ran into?"
            elif target == "solutions":
                q_text = "Got it. How did you end up solving or working around that hurdle?"
            elif target == "technical_decisions":
                q_text = "Makes sense. What was the main reason you chose this tech stack over other alternatives?"
            elif target == "architecture":
                q_text = "Understood. At a high level, how does data flow end-to-end between your core components?"
            elif target == "tradeoffs":
                q_text = "Got it. Were there any technical downsides or compromises with this setup that you had to accept?"
            elif target == "performance":
                q_text = "That's clear. Did you measure or notice any specific latency or throughput numbers, even rough ballpark figures?"
            elif target == "impact":
                q_text = "Makes sense. Once this was deployed, what was the most meaningful impact or outcome it delivered?"
            elif target == "problem":
                q_text = "To start with, what was the core user problem or bottleneck this project was created to solve?"
            else:
                q_text = f"Could you share a bit more detail about how you handled {target}?"

            return schema(
                has_next_question=True,
                question=GeneratedQuestion(
                    id=f"q_{target}_1",
                    target_area=target,
                    question=q_text,
                    rationale=f"Captures high-value technical depth for {target}."
                ),
                coverage_update={
                    target: CoverageLevel.PARTIAL
                }
            )

        if schema_name == "GeneratedClientBrochure":
            from app.ai.schemas.case_study import GeneratedClientBrochure, CaseStudySection, ClientBrochureMetric
            return schema(
                project_id="proj_brochure",
                title="Enterprise Distributed Cache & Performance Acceleration Suite",
                tagline="Accelerating enterprise data throughput by 10x with zero downtime.",
                executive_summary="An enterprise-grade caching solution designed to eliminate database bottlenecks and streamline operations under peak demand.",
                target_audience="High-volume enterprise applications and data teams",
                key_metrics=[
                    ClientBrochureMetric(label="Throughput", value="100,000 req/sec", description="High-capacity event processing capacity"),
                    ClientBrochureMetric(label="Latency Reduction", value="98% Faster", description="Sub-2ms response times under heavy load")
                ],
                sections=[
                    CaseStudySection(
                        title="Executive Summary & Value Proposition",
                        format_type="paragraph",
                        content="Engineered to tackle critical latency constraints and deliver continuous operational resilience.",
                        order=1
                    ),
                    CaseStudySection(
                        title="The Business Challenge & Client Pain Points",
                        format_type="hybrid",
                        content="Operational bottlenecks were impeding response times and increasing infrastructure overhead.\n- **Bottleneck Risk**: High database lock contention during traffic spikes.\n- **Scalability Constraint**: Legacy systems could not scale linearly without ballooning hardware costs.",
                        order=2
                    ),
                    CaseStudySection(
                        title="Delivered Solution & Core Capabilities",
                        format_type="hybrid",
                        content="A unified acceleration layer providing seamless throughput.\n- **Real-Time Data Ingestion**: Non-blocking connection management.\n- **Operational Resilience**: Zero downtime failover protection.",
                        order=3
                    ),
                    CaseStudySection(
                        title="Business Impact & Measured ROI",
                        format_type="bullets",
                        content="- **Operational Throughput**: **100k requests/second** sustained with sub-millisecond overhead.\n- **Hardware Efficiency**: **45% reduction** in required backend compute instances.",
                        order=4
                    )
                ],
                markdown_content="# Enterprise Distributed Cache & Performance Acceleration Suite\n\n*Accelerating enterprise data throughput by 10x with zero downtime.*\n\n## Executive Summary & Value Proposition\nEngineered to tackle critical latency constraints and deliver continuous operational resilience.\n\n## The Business Challenge & Client Pain Points\nOperational bottlenecks were impeding response times and increasing infrastructure overhead.\n- **Bottleneck Risk**: High database lock contention during traffic spikes.\n- **Scalability Constraint**: Legacy systems could not scale linearly without ballooning hardware costs.\n\n## Delivered Solution & Core Capabilities\nA unified acceleration layer providing seamless throughput.\n- **Real-Time Data Ingestion**: Non-blocking connection management.\n- **Operational Resilience**: Zero downtime failover protection.\n\n## Business Impact & Measured ROI\n- **Operational Throughput**: **100k requests/second** sustained with sub-millisecond overhead.\n- **Hardware Efficiency**: **45% reduction** in required backend compute instances."
            )

        # Generic default
        return schema()

    async def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if (system_prompt and "clarification" in system_prompt.lower()) or "clarification" in prompt.lower() or "developer asked for clarification" in prompt.lower():
            if "do you mean" in prompt.lower() or "redis" in prompt.lower():
                return "Yes, exactly! I'm curious what caching setup you chose and what motivated that decision. Feel free to explain whenever you're ready!"
            return "Happy to clarify! What I mean is simply what real-world issue your project solved and why existing tools weren't enough. Feel free to explain in your own words whenever you're ready!"
        return "# Technical Case Study\n\n## Overview\nGenerated technical case study analysis."

def _clean_schema_dict(d: Any) -> Any:
    """Recursively remove 'additionalProperties' and disallowed fields from schema dict for Gemini Developer API."""
    if isinstance(d, dict):
        d.pop("additionalProperties", None)
        for k, v in list(d.items()):
            _clean_schema_dict(v)
    elif isinstance(d, list):
        for item in d:
            _clean_schema_dict(item)
    return d

class GeminiLLMClient(BaseLLMClient):
    DEFAULT_FALLBACK_MODELS = [
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite"
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
            cleaned_schema = _clean_schema_dict(schema.model_json_schema())
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=cleaned_schema,
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
