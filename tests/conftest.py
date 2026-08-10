"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from lexi_evaluator.extractor import extract_article
from lexi_evaluator.providers.mock_provider import MockProvider

FIXTURE = Path(__file__).parent / "fixtures" / "sample_article.html"
SAMPLE_URL = "https://lexi.hr/why-writing-sounds-generic/"


@pytest.fixture(scope="session")
def sample_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_article(sample_html: str):
    return extract_article(sample_html, SAMPLE_URL)


@pytest.fixture
def mock_client() -> MockProvider:
    return MockProvider()
