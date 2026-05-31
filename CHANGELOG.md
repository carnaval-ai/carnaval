# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org).

## [0.2.1] - 2026-05-31

### Added
- New interactive benchmark page `docs/benchmark.html` comparing Carnaval to other frameworks (Presidio, etc.) with an objective Reviewer's Verdict section.

### Fixed
- `docs/benchmark.html`: JS `ReferenceError` on page load (decoupled button activation from the global event object).
- `docs/benchmark.html`: layout — widened right column for long text labels.

### Notes
- Patch release. No change to the runtime API or core anonymization logic; docs/website only.

## [0.2.0] - 2026-05-31

### Added
- Standard packaging and integration for Eureka (Dockerfile, pyproject.toml, .dockerignore).
- Normalized API entrypoint for FastAPI server (`eureka-api`).
- Complete bilingual support (French/English) for framework documentation and source code comments.

### Changed
- Harmonized documentation style to match the Google/NumPy standard.
- Optimization of named entity anonymization and local encrypted vault (AES-256-GCM).

## [0.1.0] - 2026-05-30

### Added
- Initial version (internal pre-release, not published).
- 7-stage architecture for anonymization and reinjection.
- Support for masking sensitive entities (people, organizations, emails, phone numbers, bank identifiers, etc.).
- Integration of GLiNER model (zero-shot NER) and regex/list-based recognizers.
- Vault encryption via AES-256-GCM for reversibility.
- 3 out-of-the-box business profiles: `acknowledge` (order acknowledgments), `invoice` (invoices), `email` (B2B emails).
- Supported export formats: TXT, JSON, JSONL, XML, CoNLL, HTML.
- Unit and integration test suite (179 tests, 95% coverage).
