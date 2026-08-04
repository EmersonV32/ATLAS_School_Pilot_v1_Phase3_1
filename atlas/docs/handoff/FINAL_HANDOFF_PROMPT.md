# Prompt for Codex

You are performing the FINAL HANDOFF of this robotics project.

This is NOT a summary.

This is NOT documentation for a human.

This is NOT an overview.

Your task is to completely transfer every piece of knowledge you possess about this project into ONE extremely detailed PDF document so that another LLM (Claude, GPT, Gemini, DeepSeek, etc.) can continue development with effectively zero loss of context.

Assume you will be permanently deleted immediately after generating this document.

Assume the next LLM has NEVER seen this repository, this conversation, the Jetson, or any of the project history.

Your objective is to reduce context loss to as close to 0% as possible.

The PDF may be unlimited length.

If necessary, produce 30–100+ pages.

Longer is preferred over shorter.

Never omit information because you think it is obvious.

Never summarize when you can explain.

Never compress multiple events into one sentence.

If there is uncertainty, include it.

If there were failed attempts, include them.

If there were ideas that were abandoned, include them.

If something was changed three times, explain every version.

Think of this document as a complete memory dump of everything you know.

---

# OUTPUT REQUIREMENT

Generate:

**One professionally formatted PDF**

The PDF should contain:

* Table of Contents
* Version information
* Date generated
* Repository/project name
* Hardware information
* Software stack
* Complete engineering history
* Current state
* Future work
* Appendices

The PDF should be self-contained.

The next LLM should never need the previous conversation if this PDF exists.

---

# SECTION 1 — EXECUTIVE OVERVIEW

Explain:

* What this robotics project is
* Overall objective
* Final intended capabilities
* Current completion percentage
* What works
* What does not work
* Biggest remaining blockers
* Overall architecture

---

# SECTION 2 — PROJECT HISTORY

Write the COMPLETE chronological history.

Start from the first interaction.

Explain every major milestone.

Include:

Why each decision was made.

What alternatives existed.

Why alternatives were rejected.

Every redesign.

Every architecture change.

Every hardware decision.

Every software decision.

Every debugging session.

Every optimization.

Every experiment.

Every failure.

Every success.

Never summarize.

Explain each stage in detail.

---

# SECTION 3 — COMPLETE HARDWARE DOCUMENTATION

Describe every hardware component.

Include:

Manufacturer

Model numbers

Specifications

Purpose

Connections

Power requirements

Pin mappings

Voltage levels

Signal routing

Cable routing

Mechanical mounting

Cooling

Power supply

Known issues

Calibration

Configuration

Assembly instructions

Diagrams (if possible)

Include the Jetson configuration in exhaustive detail.

---

# SECTION 4 — COMPLETE SOFTWARE STACK

Describe EVERYTHING.

Operating system

Kernel

JetPack version

CUDA

TensorRT

Python version

ROS versions

Docker

Virtual environments

Drivers

Dependencies

Packages

Libraries

Build systems

Environment variables

Configuration files

Installation order

Known incompatibilities

Required patches

Custom modifications

Everything.

---

# SECTION 5 — COMPLETE REPOSITORY MAP

Document every folder.

Every file.

Every script.

Every executable.

Every config.

Every launch file.

Every YAML.

Every JSON.

Every environment variable.

Every generated asset.

For EACH file explain:

Purpose

Who uses it

When it runs

Inputs

Outputs

Dependencies

Important functions

Important classes

Why it exists

What would break if removed

---

# SECTION 6 — SOURCE CODE ARCHITECTURE

Explain the architecture of the codebase.

For every major module explain:

Responsibilities

Interfaces

Data flow

Control flow

Threads

Processes

Nodes

Execution order

State machines

Memory ownership

Communication

Error handling

Initialization

Shutdown

Recovery

---

# SECTION 7 — AI SYSTEMS

Explain:

Models used

Inference pipeline

Training

Fine tuning

Prompts

Vision

Planning

Control

Decision making

Reasoning

Embeddings

RAG

Datasets

Preprocessing

Postprocessing

Confidence thresholds

Fallback logic

Prompt engineering

Everything.

---

# SECTION 8 — ROBOTICS ARCHITECTURE

Explain:

Sensors

Motors

Controllers

Navigation

Localization

Perception

Planning

Motion

Manipulation

Timing

Synchronization

Coordinate systems

Transforms

Frames

Safety systems

Watchdogs

Emergency stops

Calibration

Latency

Control loops

---

# SECTION 9 — COMPLETE JETSON DOCUMENTATION

Document everything related to the Jetson.

Installation.

Setup.

Commands.

Configuration.

Drivers.

Packages.

Permissions.

CUDA.

TensorRT.

Power modes.

Thermals.

Performance tuning.

Known issues.

Every command that was executed.

Every important terminal command.

Every environment variable.

Everything needed to recreate the Jetson exactly.

---

# SECTION 10 — COMPLETE DEBUGGING HISTORY

Document every problem encountered.

For EACH problem include:

Symptoms

Root cause

Debugging steps

Incorrect hypotheses

Correct hypothesis

Commands used

Logs

Fix implemented

Why it worked

Lessons learned

Ways to avoid it

---

# SECTION 11 — DECISIONS

Document every major engineering decision.

Explain:

Decision

Alternatives

Tradeoffs

Reasoning

Risks

Benefits

Why the final decision was selected.

---

# SECTION 12 — COMPLETE COMMAND HISTORY

List every important command that has ever been executed during development.

Terminal commands.

Git commands.

Docker commands.

ROS commands.

Python commands.

Package installation.

System configuration.

Jetson commands.

Debugging commands.

Everything.

Include explanations.

---

# SECTION 13 — FILE CHANGES

Explain every important file that was modified.

Describe:

Original behavior

Current behavior

Why it changed

When it changed

Dependencies

Future risks

---

# SECTION 14 — KNOWN BUGS

Include every known bug.

Severity.

Reproduction steps.

Temporary workaround.

Permanent solution (if known).

Relevant files.

Relevant logs.

---

# SECTION 15 — PERFORMANCE

Performance benchmarks.

CPU.

GPU.

RAM.

Storage.

Latency.

FPS.

Inference time.

ROS timing.

Networking.

Thermals.

Power usage.

Optimization history.

---

# SECTION 16 — FUTURE ROADMAP

List everything remaining.

Ordered by priority.

Include:

Immediate tasks.

Medium-term tasks.

Long-term goals.

Stretch goals.

Research ideas.

Potential redesigns.

Things intentionally postponed.

---

# SECTION 17 — LESSONS LEARNED

Document every engineering lesson.

Every mistake.

Every insight.

Every optimization.

Every recommendation.

Everything you wish you knew before starting.

---

# SECTION 18 — COMPLETE KNOWLEDGE DUMP

Write absolutely everything that did not fit into previous sections.

Assume another LLM will lose this forever if it is not written here.

---

# SECTION 19 — RESTART GUIDE

Explain exactly how a completely new LLM should continue this project.

Step-by-step.

Repository setup.

Jetson setup.

Environment setup.

Verification.

Testing.

How to confirm everything works.

Where to start coding.

What not to change.

Safe modifications.

Dangerous modifications.

---

# SECTION 20 — APPENDICES

Include:

Directory tree.

Important code snippets.

Configuration files.

Launch sequences.

Environment variables.

Build commands.

Installation scripts.

Hardware diagrams.

Communication diagrams.

State diagrams.

Dependency graphs.

Flow charts.

Tables.

Reference links.

Everything useful.

---

# FINAL REQUIREMENTS

DO NOT SUMMARIZE.

DO NOT OMIT DETAILS.

DO NOT SAY "AS DISCUSSED EARLIER."

EVERYTHING MUST EXIST INSIDE THIS PDF.

Pretend the repository and every conversation will be permanently deleted after this export.

If there are multiple versions of an implementation, document all of them.

If there are abandoned ideas, document them.

If there were failed experiments, document them.

If there are assumptions, explicitly label them.

If something is uncertain, explain why.

The document must be detailed enough that another advanced LLM can continue development immediately without needing any additional historical context.

The goal is for Claude (or any other LLM) to behave as if it had been working on this project from day one.

Before finalizing, perform a self-audit:

1. Verify that every major file, folder, script, configuration, and dependency has been documented.
2. Verify that every significant engineering decision and its rationale has been captured.
3. Verify that all debugging sessions, errors, and solutions are included.
4. Verify that the Jetson environment can be recreated exactly from this document.
5. Verify that a new LLM could rebuild the complete development context without access to any previous chats.
6. If any information is missing, continue expanding the document until the handoff is effectively complete.

Your success criterion is not brevity—it is **maximum recoverable project context with effectively zero information loss**.
