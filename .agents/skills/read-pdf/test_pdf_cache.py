#!/usr/bin/env python3
"""Small dependency-free checks for pdf_cache.py's fragile parsing heuristics."""

from pdf_cache import parse_pages, quality_reasons


def main() -> None:
    assert parse_pages(None, 3) == [1, 2, 3]
    assert parse_pages("1,3-4,6-", 7) == [1, 3, 4, 6, 7]
    assert quality_reasons("A normal sentence with enough text.") == []
    assert quality_reasons("   ") == ["no_text"]
    assert "suspected_garbled_text" in quality_reasons("Readable text \ufffd" * 20)
    try:
        parse_pages("4-2", 5)
    except Exception:
        pass
    else:
        raise AssertionError("reversed ranges must fail")
    print("pdf_cache self-check passed")


if __name__ == "__main__":
    main()
