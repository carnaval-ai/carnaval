# Carnaval Visibility & Developer Adoption Strategy
*Author: Antigravity*

To drive adoption of **Carnaval** among developers and enterprise architects, the project needs to build **trust**, **discoverability**, and **frictionless evaluation**.

Here is a structured, 4-step action plan to maximize the visibility of the project.

---

## Phase 1: Zero-Friction Evaluation (Immediate Impact)
Developers decide within 30 seconds whether to try a library. We must make evaluation instant.

1. **Google Colab Interactive Demo**:
   * Create a simple Jupyter notebook showing:
     * `pip install carnaval`
     * Running the pipeline on a dummy invoice text.
     * Viewing the masked result and retrieving the original text via the vault.
   * **Action**: Add an `[Open in Colab]` badge at the very top of `README.md`.
2. **Visual Output Previews**:
   * Add a screenshot or an interactive SVG of the HTML output format directly in the `README.md` to show how the original vs. masked text looks side-by-side. 
   * Visual proof of "how it works" builds instant trust.

---

## Phase 2: Professional Distribution (Publish to PyPI)
Cloning a repository to use a library is a high barrier to entry. Carnaval must be installable via standard Python tools.

1. **PyPI Publication**:
   * Since we successfully configured `pyproject.toml`, Carnaval is 100% package-ready.
   * **Action**: Run the following commands to build and publish to PyPI:
     ```bash
     pip install build twine
     python -m build
     python -m twine upload dist/*
     ```
   * Developers will now be able to simply run:
     ```bash
     pip install carnaval
     ```

---

## Phase 3: Documentation Landing Page (GitHub Pages)
A repository is great for code, but a dedicated documentation website is the gold standard for mature projects.

1. **Enable GitHub Pages**:
   * Go to the repository settings on GitHub $\rightarrow$ **Pages**.
   * Configure it to serve from the `/docs` folder of the `master`/`main` branch.
   * This will immediately host the existing `docs/index.html` as a clean web page at `https://carnaval-ai.github.io/carnaval/`.

---

## Phase 4: Community Outreach & Content Marketing (Traffic Drivers)
Organic discovery is driven by sharing the unique architectural value of Carnaval.

1. **Technical Blog Post (The "Reversible Anonymization" Pattern)**:
   * Publish an article on **Medium**, **Dev.to**, or **Hacker News** titled:
     * *"How to securely send B2B documents to OpenAI/Claude without leaking PII (Reversible Anonymization with AES-256-GCM and GLiNER)"*
   * Focus on the architectural solution (local zero-shot NER + deterministic fallback + secure key derivation) which solves a massive compliance headache for enterprises integrating LLMs.
2. **Community Integration**:
   * **GLiNER Community**: Share Carnaval in the GLiNER GitHub discussions or Discord server. As Carnaval is one of the few real-world B2B security tools using GLiNER, the creators will likely feature it.
   * **Awesome Lists**: Submit pull requests to add Carnaval to curated lists on GitHub, such as:
     * `Awesome-LLM-Security`
     * `Awesome-Privacy`
     * `Awesome-Python`
