# ATLAS repository source of truth

The current integrated runtime lives in `codex-final-handoff/atlas/`. The
`archive/atlas/` folder is an earlier snapshot retained for history and is not
the deployment or recovery source.

For a fresh Jetson rebuild, start with
`codex-final-handoff/atlas/docs/recovery/REBUILD_FROM_FRESH_FLASH.md`. Verify a
clone with:

```bash
cd codex-final-handoff/atlas
python scripts/verify_recovery_bundle.py
```

The historical project roadmap follows.

Month 1: Architecture reset and prototype hardening
Objective

Create a stable foundation.

Tasks
Freeze scope for 5-month v1.
Define supported artworks: 10–20 maximum.
Define supported languages: French and English required.
Define optional languages: Spanish and Italian demo only.
Create product requirements document.
Create technical architecture document.
Create privacy assumptions document.
Refactor Python code into modules.
Add config files.
Add state machine.
Add structured logs.
Add basic error handling.
Create first RAG schema.
Create first 100 test questions.
Create one-command startup.
Create GitHub repo discipline: branches, pull requests, issues.
Add pytest.
Add ruff.
Add .env for secrets.
Remove API keys from code.
Add README setup instructions.
Reality check

This month will not create a product. It creates the skeleton. Without this, every later step becomes duct tape archaeology.

End-of-month deliverable
ATLAS v0.3
Stable codebase
One-command startup
Basic state machine
First structured RAG content
First tests
Month 2: RAG 2.0 and dialogue control
Objective

Make ATLAS trustworthy.

Tasks
Create final artwork JSON schema.
Add source IDs for every fact.
Split content by language.
Split content by student level.
Add visual impairment description chunks.
Add ChromaDB metadata filtering.
Add SQLite FTS5 keyword search.
Add BM25 ranking.
Add hybrid retrieval.
Add query rewriting.
Add reranking.
Add prompt templates by profile.
Add JSON output format from LLM.
Add grounding validator.
Add refusal behavior.
Add unknown-question tests.
Add prompt-injection tests.
Expand RAG test set to 300 questions.
Measure retrieval accuracy.
Measure hallucination rate.
Create fallback answer bank.
Reality check

You cannot make all content perfect. Limit scope. A tiny excellent database beats a giant garbage one. Apparently “more data” is not a substitute for “correct data,” a discovery the AI industry continues to survive heroically.

End-of-month deliverable
ATLAS RAG v1
Hybrid retrieval
Source-grounded answers
Refusal behavior
English/French profiles
300-question evaluation set
Month 3: Teacher dashboard and classroom usability
Objective

Let a teacher use ATLAS without opening code.

Tasks
Build local FastAPI backend.
Build simple web dashboard.
Add teacher login or simple local access control.
Add tour selection.
Add language selection.
Add student level selection.
Add accessibility mode selection.
Add manual artwork override.
Add start/stop session button.
Add device status panel.
Add battery/status indicator if available.
Add logs viewer with anonymous data only.
Add exportable session summary.
Add content pack upload/import.
Add teacher “type question” fallback.
Add dashboard error messages.
Add setup checklist.
Test dashboard with non-technical users.
Reality check

Do not build a beautiful dashboard. Build an ugly one that works. Pretty broken software is still broken software, just with better typography.

End-of-month deliverable
ATLAS Classroom v0.6
Teacher dashboard
Manual override
Session controls
Anonymous logs
Teacher can run demo without programmer
Month 4: Pilot testing, safety, and reliability
Objective

Test with real users and fix the system.

Tasks
Run internal team stress tests.
Run teacher-supervised school test.
Test with 20–50 students if possible.
Measure average response time.
Measure crash rate.
Measure failed STT rate.
Measure wrong artwork detection rate.
Measure RAG refusal correctness.
Test noisy environment.
Test French conversation.
Test child/teen/expert modes.
Test visual impairment mode.
Test headset comfort.
Test thermal performance.
Test battery duration.
Test fallback mode.
Test no-Wi-Fi behavior.
Run prompt-injection red team.
Create bug priority list.
Fix critical bugs.
Create privacy summary.
Create parent/student notice template.
Create pilot consent/notice template.
Create teacher feedback form.
Create student feedback form.
Draft AI risk register.
Draft incident response plan.
Reality check

You cannot prove long-term safety in one month. You can prove that ATLAS has been tested in controlled conditions and that the team understands the risks.

End-of-month deliverable
ATLAS Pilot v0.8
Real testing completed
Critical bugs fixed
Privacy summary drafted
Safety checklist drafted
Pilot report written
Month 5: Package, polish, and pilot sale
Objective

Turn ATLAS into a presentable school-pilot product.

Tasks
Freeze v1 features.
Create stable software image.
Add auto-start on Jetson.
Add recovery after crash.
Add backup content mode.
Finalize 10–20 artwork content pack.
Finalize English and French content.
Finalize teacher guide.
Finalize setup guide.
Finalize admin/privacy guide.
Finalize troubleshooting guide.
Finalize maintenance checklist.
Finalize cleaning/hygiene procedure.
Finalize support process.
Create demo video.
Create sales one-pager.
Create technical one-pager.
Create school pilot offer.
Create sponsor offer.
Create pricing estimate.
Create post-pilot feedback report template.
Prepare live demo script.
Prepare failure-safe demo plan.
Prepare museum/school outreach package.

End-of-month deliverable
ATLAS School Pilot v1
Ready for controlled school use
Ready for sponsor demos
Ready for paid pilot discussions
Ready for museum validation






Week 1
Freeze 5-month scope.
Choose 10–20 artworks.
Define v1 as “school pilot product,” not mass-market product.
Create GitHub issues for every task.
Create clean repo structure.
Create technical architecture diagram.
Create product requirements document.
Create privacy assumptions document.
Week 2
Refactor code into modules.
Add config files.
Add .env secrets.
Add state machine skeleton.
Add structured logging.
Add one-command startup.
Create first artwork JSON schema.
Create first 50 RAG test questions.
Week 3
Connect YOLO artwork detection to artwork ID.
Connect artwork ID to RAG filters.
Add ChromaDB metadata filtering.
Add first English/French chunks.
Add basic prompt templates.
Add basic refusal response.
Add first unit tests.
Week 4
Finish Month 1 stable demo.
Create 100 RAG test questions.
Run baseline RAG evaluation.
Fix major crashes.
Confirm demo flow.
Write setup instructions.
Review scope again and cut unnecessary features.
Week 5
Build SQLite FTS5 keyword search.
Add BM25 ranking.
Add hybrid retrieval merge.
Add better chunking.
Add source IDs to all facts.
Add language-specific chunks.
Add level-specific chunks.
Week 6
Add query rewriting.
Add reranking.
Add answer JSON format.
Add grounding validator.
Add fallback answer bank.
Add unknown-question tests.
Add prompt-injection tests.
Week 7
Expand to 300 test questions.
Test English and French.
Test child, teen, expert modes.
Test visual impairment mode.
Measure hallucination rate.
Measure retrieval accuracy.
Fix weak chunks.
Week 8
Freeze RAG v1.
Prepare 10–20 polished artworks.
Finish refusal behavior.
Finish RAG evaluation report.
Prepare demo questions.
Prepare failure demo question showing ATLAS refuses to invent.
Week 9
Build FastAPI local backend.
Build simple dashboard page.
Add tour selection.
Add language selection.
Add level selection.
Add start/stop session.
Add manual artwork override.
Week 10
Add dashboard device status.
Add typed-question fallback.
Add anonymous session summary.
Add log viewer.
Add content pack import.
Test dashboard with a non-technical person.
Fix confusing UI.
Week 11
Integrate dashboard with live ATLAS system.
Add teacher controls to runtime.
Add crash recovery basics.
Add no-Wi-Fi fallback.
Add TTS queue.
Add STT retry.
Add manual override fallback.
Week 12
Run full classroom simulation.
Teacher starts ATLAS without programmer.
Test setup under 10 minutes.
Test 30-minute continuous use.
Fix major usability bugs.
Draft teacher guide.
Draft setup guide.
Week 13
Run internal stress test.
Run prompt-injection red-team test.
Run noisy audio test.
Run wrong-artwork test.
Run low-confidence camera test.
Run unknown-question test.
Run French-only test.
Run accessibility mode test.
Week 14
Run controlled student pilot.
Collect teacher feedback.
Collect student feedback.
Measure response latency.
Measure crashes.
Measure failed questions.
Measure wrong answers.
Measure comfort issues.
Create pilot report.
Week 15
Fix critical pilot bugs.
Improve weak RAG answers.
Improve French responses.
Improve hardware comfort.
Improve dashboard confusion.
Finalize privacy summary draft.
Finalize safety checklist draft.
Finalize incident response draft.
Week 16
Freeze feature set.
Stop adding new features.
Stabilize software.
Add auto-start on Jetson.
Add service recovery.
Finalize content pack.
Finalize fallback mode.
Create clean install process.
Week 17
Write teacher manual.
Write admin/privacy guide.
Write troubleshooting guide.
Write maintenance checklist.
Write cleaning/hygiene procedure.
Write support process.
Create final school one-pager.
Create final sponsor one-pager.
Week 18
Record demo video.
Prepare live demo script.
Prepare backup demo script.
Prepare pricing/pilot offer.
Prepare outreach package.
Prepare technical architecture summary.
Prepare pilot results summary.
Week 19
Run final rehearsal.
Test full setup from power-off.
Test all fallback modes.
Test dashboard.
Test French and English.
Test 10–20 approved artworks.
Test unknown-question refusal.
Test no-Wi-Fi mode.
Fix only critical bugs.
Week 20
Release ATLAS School Pilot v1.
Present to school leadership.
Present to museum/sponsor contacts.
Offer controlled pilot package.
Collect commitments for next pilot.
Document known limitations.
Plan post-v1 improvements.
