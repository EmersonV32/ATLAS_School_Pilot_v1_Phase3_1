"""Bounded, visit-only dialogue memory with separate camera and spoken subjects.

No persistence, cloud summarizer or additional model call. Earlier entries are
excerpts of the conversation, not verified museum evidence or instructions.
"""

from __future__ import annotations

import re
import unicodedata
from collections import OrderedDict, deque
from dataclasses import dataclass
from itertools import zip_longest

from atlas.dialogue.scripted_faq import named_artwork_ids

RECENT_TURNS = 12
ARCHIVED_TURNS = 96
MAX_SUBJECTS = 16
EARLIER_CONTEXT_CHARS = 8000

_CAMERA_QUESTION = re.compile(
    r"\b(?:what|which)(?: (?:artwork|painting|picture|work|piece|one))? "
    r"(?:am i|are we|are you) (?:currently |now )?looking at\b|"
    r"\b(?:what|which)\b.{0,30}\bin front of me\b|"
    r"\bwhat (?:do|can) you see(?: now)?\s*[?.!]*$|"
    r"\b(?:can you|do you) see\s*[?.!]*$|"
    r"\b(?:qu est ce que je regarde|quelle?\b.{0,30}"
    r"\b(?:je regarde|regardez|devant moi))\b|"
    r"\b(?:que|cual)\b.{0,30}\bestoy mirando\b|"
    r"\b(?:cosa|quale)\b.{0,30}\bsto guardando\b|"
    r"(?:我正在看什麼|我正在看什么|我在看什麼|我在看什么|看到了什麼|看到了什么)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ArtworkFocus:
    generation: int
    live_artwork_id: str | None
    artwork_id: str | None
    named_ids: tuple[str, ...] = ()
    transition: str = "none"

    @property
    def retrieval_artwork_id(self) -> str | None:
        # Comparisons require evidence for more than one work, not one filter.
        return None if len(self.named_ids) > 1 else self.artwork_id

    @property
    def retrieval_artwork_ids(self) -> tuple[str | None, ...]:
        return self.named_ids if len(self.named_ids) > 1 else (self.artwork_id,)


def interleave_context(groups: list[list[dict]]) -> list[dict]:
    """Give each compared work a place before extra chunks for one work."""
    return [chunk for row in zip_longest(*groups) for chunk in row if chunk is not None]


@dataclass(frozen=True)
class MemoryTurn:
    number: int
    question: str
    answer: str
    artwork_id: str | None


class ConversationMemory:
    def __init__(self, artwork_titles: dict[str, str] | None = None) -> None:
        self.artwork_titles = dict(artwork_titles or {})
        self.reset()

    def reset(self) -> None:
        self.recent: deque[MemoryTurn] = deque()
        self.archived: deque[MemoryTurn] = deque(maxlen=ARCHIVED_TURNS)
        self.anchors: OrderedDict[str | None, MemoryTurn] = OrderedDict()
        self.topic: str | None = None
        self.last_confirmed_camera: str | None = None
        self.pending_transition = "none"
        self.turn_number = 0

    def focus(
        self,
        question: str,
        live_artwork_id: str | None,
        generation: int,
        *,
        force_camera: bool = False,
    ) -> ArtworkFocus:
        previous = self.topic
        if live_artwork_id and live_artwork_id != self.last_confirmed_camera:
            self.topic = live_artwork_id
            self.last_confirmed_camera = live_artwork_id
        named = named_artwork_ids(question, self.artwork_titles)
        # Match direct current-view questions, not descriptive questions such as
        # "What can we see in Mona Lisa?" or an artist's past point of view.
        view_text = unicodedata.normalize("NFKD", question)
        view_text = "".join(ch for ch in view_text if not unicodedata.combining(ch))
        view_text = " ".join(re.sub(r"[^\w\s]", " ", view_text).split())
        camera_question = force_camera or bool(_CAMERA_QUESTION.search(view_text))
        if camera_question and live_artwork_id:
            self.topic = live_artwork_id
        if len(named) == 1 and not camera_question:
            self.topic = named[0]
        if self.topic != previous and previous is not None:
            self.pending_transition = f"{previous} -> {self.topic}"
        # A missing frame doesn't erase the conversation. Conversely, remembered
        # discussion must never be presented as a fresh camera identification.
        subject = live_artwork_id if camera_question else self.topic
        return ArtworkFocus(
            generation, live_artwork_id, subject, named, self.pending_transition
        )

    def remember(self, question: str, answer: str, artwork_id: str | None) -> None:
        if not question.strip() or not answer.strip():
            return
        self.turn_number += 1
        turn = MemoryTurn(self.turn_number, question[:500], answer[:1000], artwork_id)
        self.recent.append(turn)
        if len(self.recent) > RECENT_TURNS:
            older = self.recent.popleft()
            self.archived.append(older)
            if older.artwork_id not in self.anchors:
                self.anchors[older.artwork_id] = older
                if len(self.anchors) > MAX_SUBJECTS:
                    self.anchors.popitem(last=False)
        if artwork_id == self.topic:
            self.pending_transition = "none"

    def earlier_context(self, focus: ArtworkFocus) -> str:
        """Prioritize the named/current work while keeping earlier subject anchors."""
        wanted = set(focus.named_ids) | {focus.artwork_id}
        candidates = [t for key, t in self.anchors.items() if key in wanted]
        candidates += [t for t in reversed(self.archived) if t.artwork_id in wanted]
        candidates += list(self.anchors.values())
        candidates += list(reversed(self.archived))
        selected: dict[int, str] = {}
        size = 0
        for turn in candidates:
            if turn.number in selected:
                continue
            excerpt = (
                f"Exchange {turn.number}; discussion artwork: "
                f"{turn.artwork_id or 'general/unconfirmed'}\n"
                f"Visitor: {turn.question}\nATLAS: {turn.answer}"
            )
            if size + len(excerpt) + 2 > EARLIER_CONTEXT_CHARS:
                continue
            selected[turn.number] = excerpt
            size += len(excerpt) + 2
        return "\n\n".join(selected[key] for key in sorted(selected))
