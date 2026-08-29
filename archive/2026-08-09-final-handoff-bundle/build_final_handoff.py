#!/usr/bin/env python3
"""Build the self-contained ATLAS final engineering handoff PDF."""

from __future__ import annotations

import ast
import hashlib
import os
import subprocess
from pathlib import Path

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Preformatted,
    Spacer, Table, TableStyle
)
from reportlab.platypus.tableofcontents import TableOfContents

HERE = Path(__file__).resolve().parent
APP = HERE.parents[1]
REPO = APP.parent
OUT = HERE / "ATLAS_FINAL_HANDOFF.pdf"
SOURCE = HERE / "ATLAS_FINAL_HANDOFF_SOURCE.md"
DATE = "2026-08-04"
VERSION = "Final handoff v1.0"
COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()


def ascii_text(value: str) -> str:
    replacements = {"\u2192": "->", "\u2013": "-", "\u2014": "-", "\u2019": "'", "\u201c": '"', "\u201d": '"'}
    for old, new in replacements.items():
        value = value.replace(old, new)
    return value.encode("ascii", "replace").decode("ascii")


class HandoffDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(filename, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm,
                         topMargin=17*mm, bottomMargin=16*mm, title="ATLAS Final Handoff")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="body")
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=self.header_footer))

    def header_footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Body", 7)
        canvas.setFillColor(colors.HexColor("#5A6472"))
        canvas.drawString(15*mm, 9*mm, "ATLAS | Final engineering and LLM handoff")
        canvas.drawRightString(A4[0]-15*mm, 9*mm, f"Page {doc.page}")
        canvas.restoreState()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style = flowable.style.name
            if style in ("H1", "H2", "H3"):
                level = {"H1": 0, "H2": 1, "H3": 2}[style]
                text = flowable.getPlainText()
                key = f"h{level}-{self.seq.nextf('heading')}"
                self.canv.bookmarkPage(key)
                self.canv.addOutlineEntry(text, key, level=level, closed=False)
                self.notify("TOCEntry", (level, text, self.page, key))


font = "C:/Windows/Fonts/arial.ttf"
mono = "C:/Windows/Fonts/consola.ttf"
pdfmetrics.registerFont(TTFont("Body", font))
pdfmetrics.registerFont(TTFont("Mono", mono))
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Cover", fontName="Body", fontSize=27, leading=32,
                          textColor=colors.HexColor("#132238"), alignment=TA_CENTER, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSub", fontName="Body", fontSize=11, leading=16,
                          textColor=colors.HexColor("#40536B"), alignment=TA_CENTER))
styles.add(ParagraphStyle(name="H1", fontName="Body", fontSize=18, leading=22,
                          textColor=colors.HexColor("#0E5A6F"), spaceBefore=8, spaceAfter=8))
styles.add(ParagraphStyle(name="H2", fontName="Body", fontSize=13, leading=17,
                          textColor=colors.HexColor("#9A4A19"), spaceBefore=7, spaceAfter=5))
styles.add(ParagraphStyle(name="H3", fontName="Body", fontSize=10.5, leading=14,
                          textColor=colors.HexColor("#27384C"), spaceBefore=5, spaceAfter=3))
styles.add(ParagraphStyle(name="Body2", fontName="Body", fontSize=8.5, leading=12,
                          textColor=colors.HexColor("#202833"), spaceAfter=5))
styles.add(ParagraphStyle(name="Small", fontName="Body", fontSize=7, leading=9,
                          textColor=colors.HexColor("#344150"), spaceAfter=3))
styles.add(ParagraphStyle(name="Note", fontName="Body", fontSize=8, leading=11,
                          leftIndent=8, rightIndent=8, borderColor=colors.HexColor("#8DB7C2"),
                          borderWidth=.6, borderPadding=6, backColor=colors.HexColor("#EDF6F7"), spaceAfter=6))
code_style = ParagraphStyle(name="Code", fontName="Mono", fontSize=5.8, leading=7.2,
                            textColor=colors.HexColor("#17202A"), backColor=colors.HexColor("#F4F6F8"),
                            borderPadding=5, spaceAfter=6)

story = []
md = []


def h(text: str, level: int = 1):
    text = ascii_text(text)
    story.append(Paragraph(text, styles[f"H{level}"]))
    md.append("#" * level + " " + text + "\n")


def p(text: str, note: bool = False):
    text = ascii_text(text)
    story.append(Paragraph(text.replace("\n", "<br/>"), styles["Note" if note else "Body2"]))
    md.append(text + "\n")


def bullets(items):
    for item in items:
        p("- " + item)


def code(text: str, limit: int | None = None):
    text = ascii_text(text)
    if limit and len(text) > limit:
        text = text[:limit] + "\n[truncated in this excerpt; complete file is listed in repository inventory]"
    story.append(Preformatted(text, code_style, maxLineLength=120))
    md.append("```\n" + text + "\n```\n")


def section(title, paragraphs=(), points=()):
    h(title, 1)
    for text in paragraphs:
        p(text)
    bullets(points)


story += [Spacer(1, 35*mm), Paragraph("ATLAS", styles["Cover"]),
          Paragraph("FINAL ENGINEERING, RECOVERY, AND LLM HANDOFF", styles["Cover"]),
          Spacer(1, 8*mm), Paragraph("A self-contained memory transfer for continued development", styles["CoverSub"]),
          Spacer(1, 14*mm)]
cover_data = [["Version", VERSION], ["Generated", DATE], ["Repository", "EmersonV32/ATLAS_School_Pilot_v1_Phase3_1"],
              ["Commit", COMMIT], ["Team", "Team Touchdown - College Bourget - WRO 2026"]]
t = Table(cover_data, colWidths=[35*mm, 115*mm])
t.setStyle(TableStyle([("FONT", (0,0), (-1,-1), "Body", 9), ("TEXTCOLOR", (0,0), (0,-1), colors.HexColor("#0E5A6F")),
                       ("GRID", (0,0), (-1,-1), .4, colors.HexColor("#CBD5E1")), ("BACKGROUND", (0,0), (-1,-1), colors.white),
                       ("VALIGN", (0,0), (-1,-1), "TOP"), ("PADDING", (0,0), (-1,-1), 6)]))
story += [t, Spacer(1, 12*mm), Paragraph("Security boundary", styles["Body2"]),
          Paragraph("This handoff intentionally excludes API key values, Wi-Fi passwords, SSH private keys, visitor recordings, and generated runtime logs. It includes the exact restoration procedures and variable names needed to restore them privately.", styles["Note"]), PageBreak()]
md.extend(["# ATLAS FINAL ENGINEERING, RECOVERY, AND LLM HANDOFF\n", f"Version: {VERSION}  \nGenerated: {DATE}  \nCommit: {COMMIT}\n"])

h("Table of Contents")
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle(name=f"TOC{i}", fontName="Body", fontSize=9-i*.6, leading=12,
                                  leftIndent=i*12, firstLineIndent=0, textColor=colors.HexColor("#26384C")) for i in range(3)]
story += [toc, PageBreak()]

section("1. Executive Overview", [
    "ATLAS is a wearable, edge-first AI museum guide created by Team Touchdown. A visitor wears a Shokz OpenComm2 UC headset and a small camera mounted on the wearable ring. The camera stream reaches a Jetson Orin NX, identifies the centered artwork, and supplies artwork context. ATLAS listens continuously, retrieves grounded museum facts, asks Gemini to formulate a concise multilingual answer, and speaks through Cartesia or local Piper. It can also command an EV3 artwork stand so the selected artwork remains raised while the others lower.",
    "The product objective is not a generic chatbot. It is an embodied cultural mediator that follows visitor attention, answers at an appropriate educational level, supports English/French/Spanish/Italian, protects raw media, and remains responsive enough to feel conversational.",
    "Assumption - prototype completion estimate: 75% (9 of 12 acceptance gates). Operational gates are orchestration, current artwork vision, wireless camera, Shokz audio, STT, TTS, RAG/LLM, dashboard, and source recovery. Open gates are verified headset-button events, full mechanical stand acceptance on the new Jetson, and wearable battery/thermal integration. The 12-gate model is a planning convention, not a measured industry percentage.",
], [
    "Works: XIAO Wi-Fi camera, TensorRT detection for the three trained artworks, continuous Deepgram/Silero listening with Whisper fallback, Gemini/RAG answers, Cartesia/Piper speech, multilingual command handling, local admin dashboard, manual Gemini capture, and automated tests.",
    "Not fully accepted: physical Shokz multifunction click events, EV3 stand on the current NX installation, four newly documented artworks in YOLO, camera battery/heatsink integration, and production privacy/security hardening.",
    "Largest technical risk: the live Seeed image has R36.4.3 metadata but several NVIDIA L4T 36.4.7 packages after a recovered partial upgrade. It boots and is package-clean, but generic upgrades must be avoided.",
])

h("Architecture at a glance", 2)
code("""XIAO ESP32-S3 Sense camera --MJPEG/Wi-Fi--> CameraSource
                                                |
                                     YOLO/TensorRT + tracker
                                                |
Shokz microphone --> Silero VAD --> Deepgram Nova-3 --> SessionRunner
                                                |
                                      hybrid RAG + artwork context
                                                |
                                  Gemini 2.5 Flash streaming
                                                |
                         sentence segmentation --> Cartesia Sonic 3.5
                                                |
                                         Shokz headset output

Dashboard <--> FastAPI RuntimeService <--> DeviceRuntime
DeviceRuntime <--> EV3 Bluetooth mailbox / mock hardware
Manual capture: keyboard/voice/button --> center crop --> Gemini vision""")

section("2. Complete Project History", [
    "The project began as a single Jetson Orin Nano script, JRAG2.py, combining USB camera capture, YOLO artwork recognition, speech recognition, Gemini, Piper voices, simple RAG, and Bluetooth control of an EV3 display. Initial development focused on making a nationals demonstration work reliably rather than separating concerns.",
    "The original exhibit used three artworks: Mona Lisa, The Starry Night, and Tutankhamun's funerary mask. EV3 ports were ultimately mapped A=Starry Night, B=Mona Lisa, C=mask. The correct behavior was established after several reversals: all artworks begin raised; after a centered artwork is held for about two seconds, that artwork stays raised and the other two lower; after the spoken answer, all rise again.",
    "Early latency came from blocking vision, repeated TTS generation, slow startup, fixed recording windows, cloud LLM delay, and motor waits. The old script gained local phrase caches, model preloading, center-weighted selection, two-second holds, camera rotation, multilingual prompts, profile skipping, and age-based profile shortcuts. These fixes won the national competition but left a large monolithic codebase.",
    "GPIO RGB status LED experiments on the Orin Nano were abandoned. The KY-016/common-cathode module itself worked from 3.3 V, but user GPIO writes did not behave reliably on the flashed carrier configuration. Reflashing solely for Jetson-IO was rejected before competition. This is historical and not part of the current NX runtime.",
    "After nationals, the project moved to EmersonV32/ATLAS_School_Pilot_v1_Phase3_1 and a Seeed reComputer Super J401 with Jetson Orin NX 16 GB. The architecture was decomposed into typed configuration, adapters, a dependency container, RAG stores, dialogue services, hardware interfaces, a session runner, tests, and FastAPI dashboards.",
    "The J401 was flashed with the Seeed JetPack 6.2/L4T 36.4.3 image. An accidental apt upgrade partially installed NVIDIA 36.4.7 packages and failed because the Seeed board identifier was unknown to NVIDIA maintainer scripts. With explicit approval, only the failing bootloader and kernel post-install scripts were temporarily replaced by no-op scripts, dpkg was completed, critical L4T packages were held, the machine rebooted, and apt/dpkg checks passed. The clean official recovery remains a reflash.",
    "Shokz OpenComm2 UC integration initially froze desktop sound settings and appeared to trigger shutdown. Persistent device rules and controlled reconnects were used. A live microphone-to-headset loopback proved near-instant, clean full-duplex audio. Later PortAudio failures showed raw USB ALSA capture was exclusive; selection was moved to PulseAudio's virtual input and Deepgram recovery was added.",
    "The XIAO ESP32-S3 Sense camera was assembled with its Sense board, OV3660 ribbon camera, and U.FL antenna. Firmware was built for OPI PSRAM and an 8 MB maximum application partition. It advertises atlas-camera.local and streams 640x480 MJPEG. Tests measured 23.62 FPS raw, 22.75 FPS with desktop display, and about 40.6 ms median PyTorch YOLO inference at image size 416.",
    "TensorRT export changed inference from about 37.52 ms median PyTorch wall time to 14.31 ms on one live benchmark (2.62x). A three-artwork parity run reported 3.13x median speedup with the same correct detections. The FP16 engine remains generated because it is target-stack-specific.",
    "Speech was upgraded from local Whisper/Piper-only to Deepgram Nova-3 multilingual streaming, local Silero VAD, and Cartesia Sonic 3.5 streaming TTS. Whisper small CPU/int8 and Piper remain warm offline fallbacks. Gemini output is segmented at sentence boundaries so the first complete sentence can be spoken while later text is still generated.",
    "Listening was decoupled from artwork detection after dashboard trials showed ATLAS waited for an artwork before accepting questions. The runtime now reopens listening windows continuously, pauses input while speaking to avoid self-transcription, and treats artwork detection as context rather than permission to listen.",
    "French failures such as 'qui a peint la Joconde' becoming 'who is there' led to longer endpoint silence, Deepgram keyterms, multilingual intent phrases, explicit language commands, and prompt instructions that repair plausible transcription errors using museum context without confusing 'who is there' with questions about ATLAS.",
    "The dashboard evolved from a teacher page to a full-screen admin console with live camera/YOLO view, component readiness, settings and controls, and comprehensive runtime logs. Prototype mode binds only to localhost, disables admin-token enforcement, enables demo controls, and logs visitor transcripts by explicit testing permission. This must change before a public pilot.",
    "Four content-only artworks were added: Sunflowers, Liberty Leading the People, Girl with a Pearl Earring, and The Great Wave off Kanagawa. Together with the original three they produce 143 short grounded chunks and pass nine focused retrieval checks. Automatic vision for the four additions still needs labeled images and retraining.",
    "On 2026-08-04 the complete current source, firmware, EV3 code, old nationals snapshot, exact YOLO checkpoint, package lock, Jetson snapshot, prior reports, recovery scripts, and this handoff were assembled for GitHub. Secrets and non-portable generated state were deliberately excluded.",
])

section("3. Complete Hardware Documentation", points=[
    "Compute: Seeed Studio reComputer Super J401 carrier with NVIDIA Jetson Orin NX 16 GB. Current hostname super; user super-alex. NVMe root was 233 GB with 197 GB free in the captured snapshot. 15 GiB RAM and 7.6 GiB swap were present.",
    "Camera: Seeed Studio XIAO ESP32-S3 Sense, OV3660 sensor, external U.FL antenna, USB-C for flashing, 2.4 GHz Wi-Fi for MJPEG. URL http://atlas-camera.local:81/stream. The thin camera ribbon must remain fully seated and latched.",
    "Camera power: USB-C is used during development. A protected single-cell 3.7 V LiPo was proposed for BAT+/BAT-. Measure actual current before purchase. The heatsink covers BAT pads when correctly positioned, so battery leads must be attached before final heatsink installation.",
    "Audio: Shokz OpenComm2 UC with Loop120 USB dongle. PulseAudio source contains 'usb-Shokz_Loop120...mono-fallback'; sink contains 'analog-stereo'. The headset is both microphone and private speaker.",
    "Mechanical controller: LEGO EV3 running Pybricks MicroPython BluetoothMailboxServer. Mailbox name atlas. Last known MAC 2C:6B:7D:7B:AE:02, which must be reconfirmed after brick changes.",
    "Motor mapping: Port A slot_1/Starry Night, Port B slot_2/Mona Lisa, Port C slot_3/Tutankhamun mask. The current EV3 script supports raise:<slot>, all_up/lower_all compatibility, ping, status, and nonblocking target commands followed by completion waits.",
    "Power and safety: the Jetson was run in 40 W nvpmodel mode during performance work. Use a supply/power bank capable of sustained Jetson input, not only a high advertised battery watt-hour figure. Motors require separate appropriate power. Keep an emergency stop or immediate motor-disable path for public mechanisms.",
])

section("4. Complete Software Stack", points=[
    "OS: Ubuntu 22.04.5 LTS aarch64. Kernel 5.15.148-tegra. /etc/nv_tegra_release identifies R36.4.3; many installed nvidia-l4t packages are 36.4.7 after recovery.",
    "GPU stack: JetPack 6.2 family, CUDA available through system packages, TensorRT 10.3.0.30, Torch 2.8.0 and torchvision 0.23.0 from Jetson AI Lab's JP6/CUDA 12.6 index.",
    "Python: 3.10.12 in ~/atlas/venvs/atlas-school-pilot with system-site-packages. Exact captured Python packages are reproduced in requirements-jetson.lock.txt.",
    "Core framework: pydantic, PyYAML, python-dotenv, FastAPI, Uvicorn. RAG: ChromaDB, sentence-transformers all-MiniLM-L6-v2, rank-bm25, SQLite FTS5. Vision: Ultralytics, OpenCV, ONNX/TensorRT. Audio: sounddevice/PortAudio, Deepgram WebSocket, Silero ONNX, faster-whisper, Cartesia WebSocket, Piper.",
    "LLM: google-genai client with gemini-2.5-flash. Cloud calls are opt-in and require GEMINI_API_KEY. No ROS or Docker is used in the current runtime.",
    "Secrets: GEMINI_API_KEY, DEEPGRAM_API_KEY, CARTESIA_API_KEY and optional ATLAS_ADMIN_TOKEN live only in chmod-600 .env. XIAO Wi-Fi credentials live only in ignored wifi_secrets.h.",
])

section("5. Repository and Source Architecture", [
    "The Git repository contains the current application under atlas/ and an exact archived nationals snapshot under legacy/nationals_2026/. The current application follows dependency inversion: configuration creates adapters, SessionRunner owns one interaction, DeviceRuntime owns long-running camera/listening/control threads, and RuntimeService exposes state to FastAPI.",
    "Initialization order is configuration -> logging -> container/adapters -> model warm-up -> RAG ingest/load -> camera -> audio -> dialogue -> runtime threads -> dashboard readiness. Shutdown sets shared stop events, stops active audio/network work, raises all artworks, releases camera/PortAudio resources, and closes stores.",
    "Generated Chroma, SQLite, logs, ONNX, TensorRT and Silero files are ignored because they are reproducible or private runtime state. The portable YOLO .pt is committed. Removing the dependency container breaks adapter selection; removing SessionRunner breaks the interaction contract; removing DeviceRuntime breaks continuous operation and dashboard control.",
])

section("6. AI Systems", points=[
    "Vision: latest-frame MJPEG capture, 0/180 degree rotation support, YOLO confidence filtering, mask-specific confidence threshold 0.45, general threshold 0.24, center threshold 0.35, center weight 0.55, two-second hold, 0.8-second gap tolerance, and four clear frames.",
    "STT: Deepgram Nova-3 multilingual primary. Local Silero threshold 0.5, minimum speech 250 ms, minimum silence 1200 ms, 250 ms pre-roll, eight-second maximum window, Deepgram endpointing 400 ms. Whisper small CPU/int8, beam size 5 is fallback.",
    "RAG: seven artwork JSON sheets, curator-style source records and short chunks capped at 55 words. Dense and BM25 candidates are fused with reciprocal rank fusion k=60. Language fallback prefers requested language and uses English for missing Spanish/Italian content.",
    "LLM: Gemini receives transcript, current artwork, visitor/language context, and retrieved chunks. It is instructed to be a museum guide, repair plausible ASR errors using context, remain grounded, and answer in the active language. Grounding validation can regenerate once or use refusal/fallback text.",
    "TTS: Cartesia Sonic 3.5 streams 24 kHz PCM using fixed voice ID a5136bf9-224c-4d76-b823-52bd5efcffcc. Piper voices are en_US-ryan-low, fr_FR-siwis-medium, es_MX-claude-high, and it_IT-paola-medium.",
    "Manual correction: keyboard c, translated 'capture this artwork' phrases, dashboard control, or future double-click selects a 70% center crop, JPEG quality 85, and asks Gemini vision to identify it. Raw frames are not persisted.",
])

section("7. Robotics Architecture", [
    "ATLAS is an exhibit manipulator rather than a navigation robot. It has no mobile base, localization, SLAM, ROS transforms, or world-coordinate planner. Perception identifies artwork bounding boxes in camera coordinates; the center metric approximates gaze. Mechanical output is a discrete stand command, not closed-loop trajectory control.",
    "The hardware interface provides focus_artwork, all_artworks_up, LED/status, emergency stop, health, and cleanup semantics. MockHardware enables laptop tests. EV3Hardware sends mailbox commands and reconnects after link loss. Timing is event/thread based; motor completion occurs on the EV3 before acknowledgement.",
], [
    "Safety invariant: all artworks return up after an answer or aborted cycle.",
    "Input is paused while TTS speaks to prevent feedback/self-transcription.",
    "Emergency stop blocks motion until explicitly cleared.",
    "Button plan: one click cycles language, two requests manual capture, three resets session. Software is tested; physical Linux input events remain unverified.",
])

section("8. Jetson Installation and Recovery", [
    "Use docs/recovery/REBUILD_FROM_FRESH_FLASH.md and scripts/bootstrap_jetson.sh. The bootstrap intentionally runs apt update but not apt upgrade, creates the venv, installs Jetson CUDA Torch first, applies the exact Python lock, restores models, primes local caches, exports TensorRT, ingests RAG, runs tests, and installs a user service.",
    "The captured system snapshot is reproduced verbatim later in this PDF. Critical nvidia-l4t holds are bootloader, core, display-kernel, initrd, jetson-io, kernel, kernel-dtbs, kernel-headers, kernel-oot-headers, and kernel-oot-modules.",
], [
    "Never publish ~/.ssh private keys or .env.",
    "Never run sudo apt upgrade -y casually on the current Seeed image.",
    "Before package changes use apt-get install -s and inspect nvidia-l4t effects.",
    "Run python -m pip check, pytest, preflight --open-camera, one English cycle and one French cycle after recovery.",
])

section("9. Debugging History", points=[
    "EV3 SD corruption: reflashed Pybricks image; permission/not-executable failures came from script mode/shebang/upload behavior. Restored the known mailbox server.",
    "Reversed stands: clarified physical meaning of up/down and corrected ports/commands so selected remains up and others lower.",
    "Thirty-second motor delay: reduced command churn and tied reset to answer completion rather than stale detection state.",
    "Slow startup: local Piper phrase cache, model warm-up, predownloaded voices/models, preflight, and wait-ready gate.",
    "French recognition: Whisper language confusion and short endpointing produced English homophones. Upgraded to Nova-3 multi, keyterms, longer silence, prompt repair, and explicit language state.",
    "Voice changed mid-answer: sentence streaming created inconsistent provider/voice behavior. Kept one Cartesia voice/context and tested samples for consistency; continue monitoring live multilingual output.",
    "Shokz input unavailable -9985: raw ALSA endpoint was exclusive. Route through PulseAudio virtual input and recover primary Deepgram after transient failures.",
    "Artwork-trigger-only listening: listening lived inside the vision cycle. Moved it to a continuous loop and paused only during TTS.",
    "Dashboard capture caused a second beep/listen: manual capture was separated from microphone opening.",
    "Jetson apt/dpkg break: Seeed board ID rejected NVIDIA postinst. Backed up scripts, no-op completed dpkg, held packages, rebooted, verified. Reflash remains the clean remedy.",
    "Jetson GPIO LED: pin-level testing did not produce reliable software control and coincided with unstable power/reboots. Abandoned before competition instead of risking a long reflash.",
])

section("10. Engineering Decisions", points=[
    "JetPack 6.2/Seeed image over JetPack 7: board-vendor support and known compatibility outweighed novelty.",
    "Orin NX 16 GB over Nano: more inference headroom and memory for simultaneous vision/audio/RAG.",
    "Wi-Fi XIAO camera over direct CSI in the wearable: removes the backpack-to-head cable; accepts network latency and battery complexity.",
    "Shokz OpenComm2 UC over custom bone transducers: integrated microphone, private audio, Bluetooth/USB reliability, less electronics work.",
    "Deepgram/Cartesia cloud primary with local fallback: lower latency/quality while retaining demo resilience. Cloud use and costs remain explicit.",
    "TensorRT generated from .pt: best latency without making a nonportable engine the source of truth.",
    "Hybrid RAG instead of LLM memory alone: detailed artwork grounding, multilingual retrieval, testable facts, and reduced hallucination.",
    "Local-only dashboard during prototype: fast iteration without exposing unauthenticated controls to a network.",
    "EV3 retained for current stands: known working mechanism. Raspberry Pi/servo redesign remains future work, not mixed into the stable demo.",
])

section("11. Known Bugs, Risks, and Open Work", points=[
    "Critical: do not unhold/upgrade mixed L4T packages; wrong action may require reflash.",
    "High: test Shokz physical click events. Software mapping exists but no evdev event was confirmed.",
    "High: reconnect EV3 and complete repeated focus/reset/emergency-stop acceptance on the NX.",
    "High: run sustained human English and French conversations after each audio-provider change; cloud availability is external.",
    "Medium: train YOLO for Sunflowers, Liberty, Girl with a Pearl Earring, and Great Wave with approved labeled data. Current automatic model has only three classes.",
    "Medium: dashboard prototype logs full visitor transcripts for 30 days by explicit testing permission. Obtain consent, minimize/disable logging, add auth, and define retention before school use.",
    "Medium: localhost dashboard has demo controls and no required admin token. Do not bind to 0.0.0.0 in this state.",
    "Medium: finalize protected LiPo, charging, switch, measured runtime, thermal pad/heatsink placement, and strain relief for the XIAO camera.",
    "Low: Starlette warns that its current TestClient/httpx integration is deprecated. Pin/upgrade together later.",
    "Low: old recovery scripts are historical and may contain paths for the earlier repo/venv. Use the new rebuild guide first.",
])

section("12. Performance", points=[
    "XIAO MJPEG: 23.62 FPS network capture and 22.75 FPS with desktop rendering at 640x480, JPEG quality 10.",
    "PyTorch YOLO live median: 37.52 ms in one backend comparison; earlier sustained measurement 40.6 ms at imgsz 416.",
    "TensorRT FP16 live median: 14.31 ms, 2.62x speedup in one run; three-artwork parity run reported 3.13x.",
    "Vision trigger: two seconds centered hold by configuration. Prior 15-second perceived delays came from serial blocking and cloud response, not only hold duration.",
    "Last captured system idle-ish service snapshot: 2.4 GiB service memory while running, 15 GiB total RAM, 12 GiB available, 197 GB disk free. Values are point-in-time, not guarantees.",
    "Human dashboard trial observed roughly six seconds from question to answer in one cycle; other normal questions felt fast. Instrumented logs should be used for provider-by-provider latency rather than this anecdote.",
])

section("13. Future Roadmap", points=[
    "P0: merge this handoff branch, clone it on Jetson, run complete tests/preflight, and compare deployed files to Git HEAD.",
    "P0: validate always-listening, language switching, fixed Cartesia voice, Deepgram recovery, and button behavior with real users.",
    "P1: EV3 acceptance and mechanical safety; then evaluate Raspberry Pi/servo replacement separately.",
    "P1: collect balanced images for four new artworks, retrain/evaluate/export YOLO, and add class-specific thresholds only from evidence.",
    "P1: production dashboard authentication, consent, privacy controls, retention, error summaries, and role-based user/admin views.",
    "P1: camera battery/charger/thermal prototype with current measurement and two-to-three-hour real runtime test.",
    "P2: evaluate lower-latency LLMs (GPT/Kimi/local) with the same grounded contract, first-token timing, multilingual accuracy, cost, and fallback behavior.",
    "P2: offline/local LLM proof of concept on Orin NX without reducing answer quality or blocking vision/audio.",
    "P3: miniaturize the wearable ring, integrate charging/power state, add robust enclosure and strain relief, and remove remaining backpack dependence.",
])

section("14. Lessons Learned", points=[
    "Prototype latency is a pipeline property. Preload, stream, overlap, and instrument each stage before changing a single threshold.",
    "Keep hardware behavior explicit in names. 'raise' and 'lower' were ambiguous until the physical invariant was documented.",
    "Do not index audio devices numerically across reboots. Select by stable names and route shared devices through PulseAudio.",
    "A cloud primary must be allowed to recover; a one-way fallback latch makes transient errors permanent until restart.",
    "Language detection cannot depend on one short ASR result. Carry explicit language state, keyterms, and contextual repair.",
    "Never treat a TensorRT engine as the portable model. Preserve the training checkpoint, export script, parameters, and benchmark.",
    "Vendor Jetson images need vendor-aware package discipline. Generic apt advice can brick or desynchronize boot components.",
    "A working demo and a maintainable product are different milestones. The monolith won; the modular runtime makes six months of continued development possible.",
])

section("15. Restart Guide for the Next LLM", [
    "First, read this PDF, then inspect docs/recovery/REBUILD_FROM_FRESH_FLASH.md, docs/hardware_integration_status.md, config/settings.yaml, src/atlas/app/device_runtime.py, src/atlas/pipeline/session_runner.py, and the tests matching the subsystem you will change.",
    "Treat main/current handoff branch as source of truth, the live Jetson as a deployment target, and legacy/nationals_2026 as historical fallback/training evidence. Never overwrite the live .env or generated models during deployment. Back up the target, sync source with explicit exclusions, run compile/tests, restart the user service, and inspect health/logs.",
], [
    "Safe first command set: git status; git log -5; python -m pytest -q; ./scripts/preflight_device.sh --open-camera; systemctl --user status atlas.service; tail -n 200 data/logs/atlas-runtime.log.",
    "Do not run cloud calls without explicit budget/permission. Mock/fake tests cover request construction.",
    "Do not modify L4T packages, GPIO pinmux, EV3 angles, battery wiring, or public dashboard binding without physical confirmation and rollback.",
    "For every change: add a focused test, run the full suite, perform the relevant live hardware check, update hardware status/recovery docs, commit, and push.",
])

# Include authoritative recovery and operating documents verbatim.
h("16. Authoritative Recovery Records", 1)
for rel in [
    "docs/recovery/REBUILD_FROM_FRESH_FLASH.md",
    "docs/recovery/ATLAS_JETSON_NX_SETUP_LOG.md",
    "docs/recovery/jetson_snapshot_2026-08-04.txt",
    "docs/hardware_integration_status.md",
    "config/settings.yaml",
    "config/hardware.yaml",
    ".env.example",
    "requirements-jetson.lock.txt",
]:
    path = APP / rel
    h(rel, 2)
    code(path.read_text(encoding="utf-8", errors="replace"))

h("17. Complete Command Reference", 1)
commands = """# Clone and bootstrap
git clone https://github.com/EmersonV32/ATLAS_School_Pilot_v1_Phase3_1.git ~/atlas/ATLAS_School_Pilot_v1_Phase3_1
cd ~/atlas/ATLAS_School_Pilot_v1_Phase3_1/atlas
chmod +x scripts/*.sh scripts/recovery/*.sh
./scripts/bootstrap_jetson.sh
./scripts/configure_cloud_keys.sh

# Verify
python -m pip check
python -m pytest -q
./scripts/preflight_device.sh --open-camera
python scripts/evaluate_rag.py
python scripts/test_silero_vad.py
python scripts/benchmark_yolo_backends.py --frames 30 --imgsz 416

# Run and inspect
systemctl --user start atlas.service
systemctl --user restart atlas.service
systemctl --user status atlas.service --no-pager
journalctl --user -u atlas.service -n 200 --no-pager
tail -f data/logs/atlas-runtime.log
curl -fsS http://127.0.0.1:8765/health

# Models and RAG
./scripts/restore_models.sh
python scripts/export_tensorrt.py --model models/atlas_yolo.pt --imgsz 416
python -m atlas.rag.ingest --pack data/content_packs/demo_pack --mode device --reset

# Hardware discovery
pactl list short sources
pactl list short sinks
ls -l /dev/input/by-id /dev/video* 2>/dev/null
bluetoothctl
nvpmodel -q
sudo jetson_clocks

# Package safety
sudo apt-get check
sudo dpkg --audit
apt-mark showhold | grep nvidia-l4t
sudo apt-get install -s PACKAGE_NAME

# XIAO (run PowerShell on Windows)
firmware/xiao_camera/configure_wifi.ps1
firmware/xiao_camera/build_and_flash.ps1

# Git quality gate
python scripts/check_no_secrets.py
git diff --check
git status --short
git add -A
git commit -m "describe change"
git push origin main"""
code(commands)

h("18. Current Source Module Inventory", 1)
for path in sorted((APP / "src").rglob("*.py")):
    rel = path.relative_to(APP).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
        doc = ast.get_docstring(tree) or "No module docstring."
        classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
        functions = [node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    except SyntaxError as exc:
        doc, classes, functions = f"AST parse failed: {exc}", [], []
    h(rel, 2)
    p(f"Purpose/docstring: {doc}")
    p("Top-level classes: " + (", ".join(classes) or "none"))
    p("Top-level functions: " + (", ".join(functions) or "none"))

h("19. Complete Repository Map", 1)
tracked = subprocess.check_output(["git", "ls-files"], cwd=REPO, text=True).splitlines()
rows = [["Path", "Bytes", "SHA-256", "Role"]]
for rel in tracked:
    path = REPO / rel
    if not path.is_file():
        continue
    size = path.stat().st_size
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    if rel.startswith("legacy/"):
        role = "Archived nationals source/training artifact"
    elif "/tests/" in rel:
        role = "Automated regression/contract test"
    elif rel.endswith(('.yaml', '.yml', '.json', '.env.example')):
        role = "Configuration or structured content"
    elif rel.endswith(('.py', '.sh', '.ps1', '.ino', '.cpp')):
        role = "Executable source, firmware, or utility"
    elif rel.endswith('.pdf'):
        role = "Historical/reference report"
    elif rel.endswith(('.pt', '.onnx', '.engine')):
        role = "ML model artifact"
    else:
        role = "Documentation, asset, or repository support"
    rows.append([ascii_text(rel), str(size), digest, role])

table = Table(rows, repeatRows=1, colWidths=[90*mm, 18*mm, 27*mm, 45*mm])
table.setStyle(TableStyle([("FONT", (0,0), (-1,-1), "Body", 5.4),
                           ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#173B57")),
                           ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                           ("GRID", (0,0), (-1,-1), .25, colors.HexColor("#D7DEE7")),
                           ("VALIGN", (0,0), (-1,-1), "TOP"),
                           ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F7F9FB")]),
                           ("LEFTPADDING", (0,0), (-1,-1), 2), ("RIGHTPADDING", (0,0), (-1,-1), 2)]))
story.append(table)
md.append(f"Tracked files documented: {len(rows)-1}\n")

h("20. Source Appendices", 1)
p("The following text files are included verbatim so the next LLM can recover implementation details even without a checkout. Binary models, images, caches, and PDFs are represented by hashes in the repository map.", note=True)
include_roots = [APP / "src", APP / "config", APP / "scripts", APP / "ev3", APP / "firmware" / "xiao_camera", APP / "data" / "content_packs" / "demo_pack"]
for root in include_roots:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() in {".pt", ".onnx", ".engine", ".pdf", ".png", ".jpg", ".jpeg", ".pyc"}:
            continue
        rel = path.relative_to(APP).as_posix()
        h(rel, 2)
        code(path.read_text(encoding="utf-8", errors="replace"))

h("21. Historical Reports Extract", 1)
for path in sorted((APP / "docs" / "history").glob("*.pdf")):
    h(path.name, 2)
    reader = PdfReader(str(path))
    text = "\n\n".join((page.extract_text() or "") for page in reader.pages)
    code(text)

h("22. Final Self-Audit", 1)
bullets([
    f"Repository identity, version, date, and commit are recorded: {COMMIT}.",
    f"Every one of {len(rows)-1} tracked files has path, byte count, hash, and role in the repository map.",
    "Every current Python module has a purpose/docstring and top-level class/function inventory.",
    "Current source, configuration, scripts, firmware, content pack, recovery records, package lock, and prior reports are embedded or extracted.",
    "Major history, redesigns, failures, debugging, decisions, performance results, open bugs, privacy limits, and abandoned GPIO work are recorded.",
    "Fresh-flash steps, model hashes, secret restoration, service installation, tests, preflight, and acceptance gates are explicit.",
    "Uncertainties are labeled: completion percentage is an assumption; battery runtime and physical button events remain unverified; L4T mixed state is documented.",
    "The Git repository remains the binary source of truth for model/image assets; this PDF identifies them with hashes rather than embedding unsafe binary encodings.",
])

SOURCE.write_text("\n".join(md), encoding="utf-8")
doc = HandoffDoc(str(OUT))
doc.multiBuild(story)
print(OUT)
print(SOURCE)
print(f"tracked_files={len(rows)-1}")
