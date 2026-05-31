"""Tests unitaires du type Span."""

from __future__ import annotations

import pytest

from carnaval.core.span import Span


class TestSpanConstruction:
    def test_basic(self):
        s = Span(start=0, end=5, entity_type="PERSON", text="Alice")
        assert s.start == 0
        assert s.end == 5
        assert s.length == 5
        assert s.score == 1.0  # defaut
        assert s.recognizer == ""
        assert s.metadata == {}

    def test_with_metadata(self):
        s = Span(
            start=10, end=20, entity_type="EMAIL", text="x@y.com",
            score=0.9, recognizer="EmailRegex", metadata={"lang": "fr"},
        )
        assert s.score == 0.9
        assert s.recognizer == "EmailRegex"
        assert s.metadata == {"lang": "fr"}

    def test_negative_start_rejected(self):
        with pytest.raises(ValueError, match="start negatif"):
            Span(start=-1, end=5, entity_type="X", text="x")

    def test_end_before_start_rejected(self):
        with pytest.raises(ValueError, match="end .* <= start"):
            Span(start=5, end=5, entity_type="X", text="x")
        with pytest.raises(ValueError, match="end .* <= start"):
            Span(start=10, end=5, entity_type="X", text="x")

    def test_score_out_of_range(self):
        with pytest.raises(ValueError, match="score hors"):
            Span(start=0, end=1, entity_type="X", text="x", score=1.5)
        with pytest.raises(ValueError, match="score hors"):
            Span(start=0, end=1, entity_type="X", text="x", score=-0.1)

    def test_empty_entity_type_rejected(self):
        with pytest.raises(ValueError, match="entity_type vide"):
            Span(start=0, end=1, entity_type="", text="x")


class TestSpanOverlap:
    def test_overlap_disjoint(self):
        a = Span(start=0, end=5, entity_type="X", text="abc")
        b = Span(start=10, end=15, entity_type="Y", text="def")
        assert not a.overlaps(b)
        assert not b.overlaps(a)

    def test_overlap_adjacent_not_overlap(self):
        a = Span(start=0, end=5, entity_type="X", text="abc")
        b = Span(start=5, end=10, entity_type="Y", text="def")
        assert not a.overlaps(b)
        assert not b.overlaps(a)

    def test_overlap_partial(self):
        a = Span(start=0, end=8, entity_type="X", text="aaaaaaaa")
        b = Span(start=5, end=12, entity_type="Y", text="bbbbbbb")
        assert a.overlaps(b)
        assert b.overlaps(a)

    def test_overlap_contained(self):
        outer = Span(start=0, end=20, entity_type="X", text="x" * 20)
        inner = Span(start=5, end=10, entity_type="Y", text="y" * 5)
        assert outer.overlaps(inner)
        assert inner.overlaps(outer)
        assert outer.contains(inner)
        assert not inner.contains(outer)


class TestSpanShift:
    def test_shift_positive(self):
        s = Span(start=10, end=15, entity_type="X", text="hello")
        s2 = s.shift(5)
        assert s2.start == 15
        assert s2.end == 20
        assert s2.entity_type == "X"
        assert s2.text == "hello"
        # Original inchange
        assert s.start == 10

    def test_shift_zero(self):
        s = Span(start=10, end=15, entity_type="X", text="hello")
        s2 = s.shift(0)
        assert s2.start == 10


class TestSpanSerialization:
    def test_to_dict(self):
        s = Span(start=0, end=5, entity_type="PERSON", text="Alice",
                 score=0.9, recognizer="GLiNER")
        d = s.to_dict()
        assert d["start"] == 0
        assert d["end"] == 5
        assert d["entity_type"] == "PERSON"
        assert d["text"] == "Alice"
        assert d["score"] == 0.9
        assert d["recognizer"] == "GLiNER"

    def test_to_dict_safe_omits_text(self):
        s = Span(start=0, end=5, entity_type="PERSON", text="Alice")
        d = s.to_dict_safe()
        assert "text" not in d
        assert d["length"] == 5
        assert d["entity_type"] == "PERSON"


class TestSpanHashable:
    def test_can_be_in_set(self):
        s1 = Span(start=0, end=5, entity_type="X", text="abc")
        s2 = Span(start=0, end=5, entity_type="X", text="abc")
        s3 = Span(start=10, end=15, entity_type="Y", text="def")
        assert s1 == s2
        assert {s1, s2, s3} == {s1, s3}
