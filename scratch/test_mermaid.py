import urllib.request
import base64

flowchart = """
flowchart TD
    A["User Uploads Resume\n(PDF, DOCX, or TXT)"] --> B["Resume Parser\nReads and understands document layout"]
    B --> C["Project Detector\nFinds all technical projects in resume"]
    C --> D{"Choose a Project"}

    D -->|"Select detected project"| E["User Selects Project\nFrom list of extracted projects"]
    D -->|"Project not on resume?"| F["Add External Project\nUser fills details via structured form"]

    E --> G["Adaptive Interview Begins\nAI asks 3 to 7 targeted questions"]
    F --> G

    G --> H{"Knowledge Gaps\nRemaining?"}
    H -->|"Yes"| I["Ask Next Best Question\nTargets primary missing dimension"]
    I --> J["User Answers\nIn their own words"]
    J --> K["Knowledge Tracker Updates\nFacts stored with source provenance"]
    K --> H
    H -->|"No - Coverage Sufficient"| L["Case Study Generator\nSynthesizes verified facts"]
    L --> M["Final Case Study\nDownload as PDF, Word, or Markdown"]
"""

encoded = base64.b64encode(flowchart.strip().encode('utf-8')).decode('ascii')
url = f'https://mermaid.ink/img/{encoded}?scale=2'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = resp.read()
        print('Flowchart rendered successfully! Byte length:', len(data))
        with open('scratch/flowchart.png', 'wb') as f:
            f.write(data)
except Exception as e:
    print('Failed:', e)
