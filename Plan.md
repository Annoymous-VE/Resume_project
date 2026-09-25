Hybrid Adaptive Interview: Split-Screen Chat & Live Knowledge Ledger
Transform the current single-box form interview into a modern, high-engagement split-screen interface:

Left Panel (Chatbot Feed): A natural conversational assistant asking short, plain-English questions with quick action chips and clear context.
Right Panel (Live Knowledge Dashboard): A real-time ledger showing the 8 criteria badges and extracted facts (both from the resume and newly acquired from the conversation).
Optimized LLM Engine: Shortest possible interview flow (max 3-5 quick rounds) with multi-criteria fact extraction (a single answer can fulfill multiple criteria).
User Review Required
IMPORTANT

Multi-Criteria Fact Extraction: When you answer a question, the backend will now extract facts across all 8 dimensions at once instead of only saving to the single targeted category. For example, if you describe your architecture and also mention a 40% speedup, both Architecture and Performance will get marked as fulfilled immediately.

Simpler, Punchy Prompts: Prompts will be rewritten to be conversational, jargon-free, and max 1-2 sentences with quick reply hints, ensuring the user grasps the question on first read.

Proposed Changes
Backend: Knowledge Extraction & Interview Routes
[MODIFY] 
app/services/interview_engine.py
Refactor prompts and question generation:
System prompt tuned for a friendly, ultra-concise senior technical lead.
Questions strictly limited to 1-2 sentences in simple, everyday engineering language.
Add supportive context hints (e.g. "A couple bullet points or a quick sentence is great").
Stop condition optimized: early termination as soon as core criteria are met or after 3-4 rounds max.
[MODIFY] 
app/services/knowledge_manager.py
Implement extract_and_merge_facts:
Run an LLM extraction pass on the user's answer to classify all provided facts into their appropriate categories (architecture, challenges, performance, tradeoffs, etc.), tagging provenance (source="conversation", exchange_id).
Update compute_coverage to accurately reflect multi-source facts.
[MODIFY] 
app/api/routes/interview.py
Return knowledge and evidence in the response payloads for POST /start, POST /answer, and GET /status.
Include chat history (all previous questions and answers in conversational format).
Frontend: Split-Screen Chat & Live Knowledge Ledger
[MODIFY] 
frontend/src/App.jsx
Redesign Step 3 ("Adaptive Interview") from a single centered card into a split 2-column view:
Left Column — Interactive Chatbot Feed:
Scrollable message history with distinct AI and User bubbles.
AI message shows the question in warm, simple phrasing with target badge tag.
Typing indicator while evaluating.
Input area with Enter-to-send, plus helpful quick-action buttons:
⏭️ "Skip this topic"
💡 "I don't have exact metrics / Not sure"
🚀 "Finish & Generate Case Study"
Right Column — Live Knowledge Ledger:
Sticky sidebar with Overall Completeness / Progress Bar (e.g., "6 of 8 criteria fulfilled").
8 Criteria status badges (SUFFICIENT, PARTIAL, UNKNOWN).
Accordion or categorized cards showing:
📄 From Resume (initial extracted facts).
💬 From Conversation (facts extracted in real time during the chat).
Instant visual feedback: when user submits an answer, watching the pills turn green and new facts appear in the ledger.
[MODIFY] 
frontend/src/index.css
Add styles for:
Responsive 2-column layout (.interview-grid: chat on left, ledger on right).
Chat bubbles (.chat-bubble-ai, .chat-bubble-user, .chat-avatar, .chat-timestamp).
Live ledger cards (.ledger-panel, .ledger-card, .fact-badge, .progress-track).
Mobile responsiveness (stacks gracefully on smaller viewports).
Verification Plan
Automated / Manual Verification
Backend Route Testing:
Verify POST /api/projects/{id}/interview/start returns coverage, knowledge, evidence, and history.
Verify POST /api/projects/{id}/interview/answer correctly performs multi-criteria extraction and updates the knowledge record.
Frontend Split-Screen Verification:
Test starting an interview on an existing project.
Send a rich answer containing architecture details and metrics; verify both criteria update on the right side ledger.
Verify chat scrolling, bubble layout, and quick action chips.
Verify clicking "Finish & Generate Case Study" works cleanly at any point.