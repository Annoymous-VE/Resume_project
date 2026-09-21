import pytest
from app.ai.llm import MockLLMClient
from app.services.project_extractor import ProjectExtractor
from app.ai.schemas.resume import DocumentRepresentation, DocumentMetadata, DocumentBlock

@pytest.mark.asyncio
async def test_project_extraction_from_blocks():
    llm = MockLLMClient()
    extractor = ProjectExtractor(llm)

    doc = DocumentRepresentation(
        metadata=DocumentMetadata(filename="test.pdf", file_type="pdf"),
        blocks=[
            DocumentBlock(id="b_1", type="heading", text="Selected Work", order=1),
            DocumentBlock(id="b_2", type="paragraph", text="Cloud Stream Platform | Go, Kafka, Redis", order=2),
            DocumentBlock(id="b_3", type="bullet", text="Implemented high-volume telemetry ingestion pipeline", order=3),
            DocumentBlock(id="b_4", type="bullet", text="Reduced p99 query latency by 60% across 5 nodes", order=4)
        ]
    )

    projects = await extractor.extract_projects(doc)
    assert len(projects) > 0
    proj = projects[0]
    assert proj.name
    assert proj.confidence > 0.0

def test_heuristic_extraction_no_false_entities():
    llm = MockLLMClient()
    extractor = ProjectExtractor(llm)

    blocks = [
        DocumentBlock(id="b_1", type="heading", text="PROJECTS", order=1),
        DocumentBlock(id="b_2", type="paragraph", text="Legal Document analyzer 04/2026 – Present", order=2),
        DocumentBlock(id="b_3", type="paragraph", text="Developing a CRAG-based legal document analyzer with automated clause generation capabilities.", order=3),
        DocumentBlock(id="b_4", type="paragraph", text="Tools & Techniques : Python, Langchain, Corrective RAG", order=4),
        DocumentBlock(id="b_5", type="paragraph", text="Customer Churn Prediction 04/2025 – 04/2025", order=5),
        DocumentBlock(id="b_6", type="paragraph", text="implemented a Random Forest model to predict customer churn of telecom sector", order=6),
        DocumentBlock(id="b_7", type="paragraph", text="Tools & Technique : Machine Learning, FastAPI, Streamlit", order=7),
        DocumentBlock(id="b_8", type="heading", text="EDUCATION", order=8),
    ]

    projects = extractor._heuristic_extraction(blocks)
    assert len(projects) == 2

    # Check project 1
    p1 = projects[0]
    assert p1.name == "Legal Document analyzer"
    assert "CRAG-based" in p1.description
    assert any("Python" in t for t in p1.technologies)

    # Check project 2
    p2 = projects[1]
    assert p2.name == "Customer Churn Prediction"
    assert "Random Forest" in p2.description
    assert any("FastAPI" in t or "Fastapi" in t for t in p2.technologies)

    # Verify NO false entities were generated
    project_names = [p.name for p in projects]
    assert "Developing a CRAG" not in project_names
    assert "generation capabilities." not in project_names
    assert not any("Tools &" in n for n in project_names)

def test_heuristic_title_cleaning():
    llm = MockLLMClient()
    extractor = ProjectExtractor(llm)

    assert extractor._clean_project_title("Legal Document analyzer 04/2026 – Present") == "Legal Document analyzer"
    assert extractor._clean_project_title("Customer Churn Prediction 04/2025 – 04/2025") == "Customer Churn Prediction"
    assert extractor._clean_project_title("Cloud Stream Platform | Go, Kafka, Redis") == "Cloud Stream Platform"
    assert extractor._clean_project_title("AI Assistant (May 2023 - Present)") == "AI Assistant"

