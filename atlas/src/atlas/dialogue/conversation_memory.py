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
    r"\b(?:que regardons nous|qu est ce qu on regarde|que vois tu|"
    r"que voyez vous|tu vois quoi|vous voyez quoi)\s*$|"
    r"\b(?:que|cual)\b.{0,30}\bestoy mirando\b|"
    r"\b(?:cosa|quale)\b.{0,30}\bsto guardando\b|"
    r"(?:我正在看什麼|我正在看什么|我在看什麼|我在看什么|看到了什麼|看到了什么)",
    re.IGNORECASE,
)


def _recommendation_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).casefold().replace("œ", "oe")
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^\w\s]", " ", normalized).split())


def _asks_recommendation(question: str) -> bool:
    text = _recommendation_text(question)
    return bool(
        re.search(
            r"\b(?:recommend\w*|suggest\w*|recommand\w*|conseill\w*|"
            r"recomiend\w*|sugier\w*|consigli\w*|raccomand\w*)\b|"
            r"\b(?:another artwork|more artworks|autre oeuvre|autres oeuvres|"
            r"otra obra|otras obras|altra opera|altre opere)\b|推荐|推薦|其他作品",
            text,
        )
    )


def _accepts_recommendation(question: str) -> bool:
    text = _recommendation_text(question)
    return text in {
        "yes",
        "yes please",
        "yes tell me more",
        "yes please tell me more",
        "tell me more",
        "tell me more about it",
        "yes tell me more about it",
        "i would like to know more",
        "oui",
        "oui s il vous plait",
        "oui raconte",
        "oui dites m en plus",
        "dites m en plus",
        "parle m en",
        "oui parle m en",
        "oui je veux en savoir plus",
        "si",
        "si por favor",
        "si cuentame mas",
        "cuentame mas",
        "si grazie",
        "certo",
        "dimmi di piu",
        "si dimmi di piu",
        "好",
        "好的",
        "是",
        "想",
        "可以",
        "请介绍",
        "請介紹",
        "我想了解更多",
        "我想知道更多",
    }


_CLOSING_QUESTION = re.compile(r"([^.!?。！？؟]*[?？؟])\s*[\"'»”’]*$")
_LEARN_MORE_OFFER = re.compile(
    r"\b(?:would you like|do you want|shall we|want to|interested in|"
    r"voulez vous|voudriez vous|aimeriez vous|veux tu|voudrais tu|aimerais tu|"
    r"tu veux|souhaitez vous|ca vous interesserait|ca t interesserait|"
    r"quieres|te gustaria|deseas|vuoi|vorresti|ti interessa|ti piacerebbe)\b|"
    r"(?:想.*(?:了解|知道|聽|听)|要不要|有興趣|有兴趣)"
)
_PROPOSES_ARTWORK = re.compile(
    r"\b(?:je (?:vous |te )?propose|you (?:might|may) (?:also )?(?:like|enjoy)|"
    r"you could (?:also )?(?:explore|discover)|"
    r"vous pourriez (?:aussi )?(?:explorer|decouvrir)|"
    r"tu pourrais (?:aussi )?(?:explorer|decouvrir))\b"
)


def _offered_artwork(question, answer, artwork_id, artwork_titles):
    """Keep one known offer, not incidental names in an explanation/comparison."""

    def other_works(text):
        return tuple(
            item
            for item in named_artwork_ids(text, artwork_titles)
            if item != artwork_id
        )

    # Avoid scanning a long declarative answer for a question it cannot end in.
    closing = (
        _CLOSING_QUESTION.search(answer)
        if answer.rstrip(" \t\r\n\"'»”’").endswith(("?", "？", "؟"))
        else None
    )
    if closing and (
        len(named_artwork_ids(closing[1], artwork_titles)) > 1
        or re.search(
            r"\bcompar\w*\b|比較|比较|對比|对比", _recommendation_text(closing[1])
        )
    ):
        return None
    if _asks_recommendation(question):
        candidates = other_works(answer)
        return candidates[0] if len(candidates) == 1 else None
    if closing is None or not _LEARN_MORE_OFFER.search(
        _recommendation_text(closing[1])
    ):
        return None
    candidates = other_works(closing[1])
    if len(candidates) == 1:
        return candidates[0]
    # A named recommendation followed by "Would you like to know more?".
    if not candidates and (
        _asks_recommendation(answer)
        or _PROPOSES_ARTWORK.search(_recommendation_text(answer))
    ):
        candidates = other_works(answer)
        return candidates[0] if len(candidates) == 1 else None
    return None


@dataclass(frozen=True)
class ArtworkFocus:
    generation: int
    live_artwork_id: str | None
    artwork_id: str | None
    named_ids: tuple[str, ...] = ()
    transition: str = "none"
    accepted_recommendation: bool = False

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
        self.topic_locked = False
        self.pending_recommendation: str | None = None
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
        recommendation = self.pending_recommendation
        self.pending_recommendation = None
        if live_artwork_id and live_artwork_id != self.last_confirmed_camera:
            if not self.topic_locked:
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
            self.topic_locked = False
        accepted = False
        if len(named) == 1 and not camera_question:
            self.topic = named[0]
            self.topic_locked = True
        elif (
            recommendation is not None
            and not named
            and not camera_question
            and _accepts_recommendation(question)
        ):
            self.topic = recommendation
            self.topic_locked = True
            accepted = True
        if self.topic != previous and previous is not None:
            self.pending_transition = f"{previous} -> {self.topic}"
        # A missing frame doesn't erase the conversation. Conversely, remembered
        # discussion must never be presented as a fresh camera identification.
        subject = live_artwork_id if camera_question else self.topic
        return ArtworkFocus(
            generation,
            live_artwork_id,
            subject,
            named,
            self.pending_transition,
            accepted,
        )

    def remember(self, question: str, answer: str, artwork_id: str | None) -> None:
        if not question.strip() or not answer.strip():
            return
        self.pending_recommendation = _offered_artwork(
            question, answer, artwork_id, self.artwork_titles
        )
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
