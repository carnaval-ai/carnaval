"""Tests etage 4 : Resolve."""

from __future__ import annotations

from pathlib import Path

from carnaval.core.span import Span
from carnaval.stages.documents import DetectedDocument
from carnaval.stages.s4_resolve import resolve


def _detected(text: str, spans: list[Span]) -> DetectedDocument:
    return DetectedDocument(
        source_path=Path("d.txt"), text=text, language="fr", spans=tuple(spans),
    )


class TestResolveBasic:
    def test_no_overlap_keeps_all(self):
        spans = [
            Span(start=0, end=5, entity_type="PERSON", text="Alice"),
            Span(start=10, end=15, entity_type="EMAIL", text="a@b.c"),
        ]
        out = resolve(_detected("abc", spans))
        assert len(out.spans) == 2

    def test_overlap_keeps_longest(self):
        # A: 0..20, B: 5..10 (contenu)
        outer = Span(start=0, end=20, entity_type="ORGANIZATION", text="x" * 20,
                     score=0.5)
        inner = Span(start=5, end=10, entity_type="PERSON", text="y" * 5,
                     score=0.9)
        out = resolve(_detected("x" * 20, [outer, inner]))
        assert len(out.spans) == 1
        # Le plus long gagne
        assert out.spans[0].length == 20

    def test_same_length_higher_score_wins(self):
        a = Span(start=0, end=5, entity_type="PERSON", text="Alice", score=0.5)
        b = Span(start=0, end=5, entity_type="ORGANIZATION", text="Alice",
                 score=0.9)
        out = resolve(_detected("Alice", [a, b]))
        assert len(out.spans) == 1
        assert out.spans[0].entity_type == "ORGANIZATION"

    def test_priority_tiebreak(self):
        # Meme longueur, meme score, mais recognizers differents
        a = Span(start=0, end=5, entity_type="PERSON", text="Alice",
                 score=0.9, recognizer="GLiNER")  # prio 30
        b = Span(start=0, end=5, entity_type="PERSON", text="Alice",
                 score=0.9, recognizer="NameCommaRegex")  # prio 75
        out = resolve(_detected("Alice", [a, b]))
        assert len(out.spans) == 1
        assert out.spans[0].recognizer == "NameCommaRegex"

    def test_order_preserved_by_position(self):
        spans = [
            Span(start=20, end=25, entity_type="X", text="abcde"),
            Span(start=0, end=5, entity_type="X", text="fghij"),
            Span(start=10, end=15, entity_type="X", text="klmno"),
        ]
        out = resolve(_detected("x" * 50, spans))
        positions = [s.start for s in out.spans]
        assert positions == sorted(positions)

    def test_metadata_counts(self):
        spans = [
            Span(start=0, end=5, entity_type="X", text="abcde"),
            Span(start=2, end=7, entity_type="Y", text="efghi"),  # overlap
        ]
        out = resolve(_detected("x" * 20, spans))
        assert out.metadata["raw_spans_count"] == 2
        assert out.metadata["resolved_spans_count"] == 1
