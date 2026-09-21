import pytest
from pathlib import Path
from app.services.resume_parser import ResumeParser

@pytest.fixture
def parser():
    return ResumeParser()

def test_parse_text_resume(tmp_path: Path, parser: ResumeParser):
    sample_resume = """
    Jane Doe
    Software Engineer

    EXPERIENCE
    Senior Backend Engineer at TechCorp (2022 - Present)
    - Architected distributed caching layer with Redis reducing latency by 45%
    - Built event ingestion pipeline using Apache Kafka processing 10M events/day

    PROJECTS
    Distributed Task Runner | Python, FastAPI, Docker
    - Implemented DAG execution engine for asynchronous batch workloads
    - Deployed auto-scaling worker nodes on Kubernetes with health check recovery

    EDUCATION
    B.S. in Computer Science
    """
    txt_file = tmp_path / "resume.txt"
    txt_file.write_text(sample_resume, encoding="utf-8")

    doc = parser.parse(txt_file, "resume.txt")
    assert doc.metadata.filename == "resume.txt"
    assert len(doc.blocks) > 0

    headings = [b for b in doc.blocks if b.type == "heading"]
    heading_texts = [h.text.upper() for h in headings]
    assert "EXPERIENCE" in heading_texts or "PROJECTS" in heading_texts

    bullets = [b for b in doc.blocks if b.type == "bullet"]
    assert len(bullets) >= 4
