# Contributing to Signal Scout

First of all, thank you for your interest in contributing to **Signal Scout**. We genuinely appreciate your time, expertise, and care.

Whether you are fixing a typo, improving documentation, adding tests, or shipping a new feature, your contribution helps make this project more useful and more sustainable for everyone.

---

## Project Overview

Signal Scout is an open-source intelligence platform with:

- A **Python/FastAPI backend**
- A **Vanilla JavaScript frontend**
- A modular, Domain-Driven Design structure (`app/`, `static/js/modules/`)

We value:

- Inclusivity and respectful collaboration
- Clear, maintainable code
- Rigorous testing and safe changes

---

## Getting Started

### 1) Fork and clone

1. Fork this repository to your GitHub account.
2. Clone your fork locally:

```bash
git clone https://github.com/<your-username>/nesta-signal-scout.git
cd nesta-signal-scout
```

### 2) Create and activate a virtual environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Configure environment variables

Create a `.env` file in the repository root. At minimum, most development flows need:

- `OPENAI_API_KEY`
- `GOOGLE_SEARCH_API_KEY`
- `GOOGLE_SEARCH_CX`
- `GOOGLE_CREDENTIALS`
- `SHEET_ID`

Optional values such as `CRUNCHBASE_API_KEY` may be required for specific features.

### 5) Run the application

```bash
uvicorn app.main:app --reload
```

---

## Development Workflow

### Branch naming

Please create focused branches using one of these prefixes:

- `feat/<short-description>` for features
- `fix/<short-description>` for bug fixes
- `docs/<short-description>` for documentation updates
- `chore/<short-description>` for maintenance tasks

Examples:

- `feat/add-policy-filtering`
- `fix/radar-streaming-timeout`
- `docs/update-readme-setup`

### Understand the module boundaries

Please keep changes aligned with the project structure:

- `app/api/` → API routes and dependency wiring
- `app/services/` → backend business logic
- `app/domain/` → models and taxonomy
- `app/core/` → configuration, logging, security, prompts
- `static/js/modules/` → frontend API, state, UI, visualisation helpers

As a rule, avoid creating new “god objects” or mixing unrelated responsibilities in a single module.

---

## Testing Standards

Before opening a pull request, run the full test suite:

```bash
pytest
```

Contribution expectations:

- All existing tests must pass.
- New features should include new tests.
- Bug fixes should include regression tests where practical.
- If a change cannot be tested automatically, include a clear manual test plan in the PR description.

---

## Pull Request Process

1. Keep PRs **small and focused** (one logical change per PR).
2. Use the repository PR template and complete all relevant sections.
3. Ensure tests pass locally before requesting review.
4. Write clear commit messages and a concise PR summary.
5. Confirm documentation is updated when behaviour changes.

### Review checklist

Please verify your PR:

- [ ] Builds and runs locally
- [ ] Passes `pytest`
- [ ] Includes tests for new behaviour
- [ ] Preserves existing behaviour unless intentionally changed
- [ ] Uses British English spelling in docs/comments/user-facing strings

---

## Style Guide

### Python

- Follow **PEP 8**
- Use **Python 3.10+ type hints** for function signatures
- Prefer dependency injection and small single-responsibility functions/classes

### JavaScript

- Use **ES6 modules**
- Avoid global mutable state where possible
- Keep API concerns separate from UI rendering logic

### Comments and documentation

- Use British English spelling (e.g., *behaviour*, *optimise*, *visualise*)
- Prefer comments that explain **why**, not **what**
- Remove dead or commented-out code

---

## Community Expectations

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

By participating in this project, you agree to contribute in a respectful, constructive, and inclusive way.

---

## Need Help?

If you are unsure where to start, open a discussion or issue and label it clearly (for example, `question` or `good first issue`).

We are glad you are here, and we are happy to help.
