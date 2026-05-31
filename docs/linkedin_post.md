# LinkedIn Post — Carnaval Release (EN)

**Author**: Patrice AUBERT (drafted by AI, reviewed by Patrice)
**Date**: 2026-05-31
**Length**: ~2,400 characters (LinkedIn safe)

---

## Post

I just shipped a production-ready open-source Python framework on PyPI.

I didn't write a single line of code.

For the last few days, I ran an experiment: take an idea, three of today's most capable AI assistants — **Claude Code**, **Google Antigravity**, and **xAI Grok** — and orchestrate them like a small engineering team. No human coding. Just product direction, code review, and decisions.

The output: **Carnaval** — a reversible PII anonymization framework for LLM pipelines.

Mask sensitive entities (names, emails, IBANs, organizations, phone numbers) in any text document, send the masked version to a cloud LLM (Sonnet, GPT, Mistral, anything), then reinject the original values into the structured response via an encrypted vault. Local-first. AES-256-GCM. GLiNER for zero-shot NER. No Presidio, no spaCy.

What's in the box, today:

→ pip install carnaval (live on PyPI: pypi.org/project/carnaval)
→ 184 tests passing, mypy-checked, CI matrix on Python 3.11 / 3.12 / 3.13
→ Apache 2.0, bilingual (English + French) docs, landing page on GitHub Pages
→ Interactive benchmark vs Presidio: carnaval-ai.github.io/carnaval/benchmark.html
→ 9 languages of fictional sample documents shipped (FR, EN, DE, IT, ES, PT, PL, TR, JP)
→ Source: github.com/carnaval-ai/carnaval

My only contribution: the product vision, the architecture decisions, the calls on what to ship and what to throw away, and a lot of "no, do it again". I never touched a `.py` file.

Three lessons from running an AI team:

1. **Models complement each other.** Claude Code architects, Antigravity ships UI and integration at insane velocity, Grok stress-tests strategy and writes uncomfortable critique. None of them does all three well.
2. **The bottleneck is no longer code — it's clear product judgment and the discipline to say no.** AI will happily produce 1,000 lines of clever code that solves the wrong problem if you let it.
3. **"AI replaces developers" is the wrong question.** The right one is "what does a single experienced person become, with an AI team?" The answer is: a small product company.

This wasn't built to prove a point about AI. It was built to ship a real tool I needed for my day job (anonymizing supplier acknowledgments before LLM extraction in an industrial context). The fact that it took days instead of months — that's the point.

Try it. Break it. Open an issue.

→ github.com/carnaval-ai/carnaval

#OpenSource #Python #AI #LLM #PrivacyByDesign #DataAnonymization #BuildInPublic #DigitalTransformation
