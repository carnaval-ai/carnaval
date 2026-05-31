# Contributing to carnaval

Thank you for your interest in **carnaval**! We greatly appreciate any contributions to improve this anonymization framework.

## GDPR / Privacy & Security

**VERY IMPORTANT**: No real personal data (PII) or customer data must ever be included in the source code, test files, commits, fixtures, examples, or documentation. Use only fictional entities (e.g., Acme, Globex, Initech, John Doe, etc.).

## Contribution Process

The standard contribution lifecycle follows these steps:
1. **Branching**: Create a dedicated branch from `main` (e.g., `feature/feature-name` or `fix/bug-name`).
2. **Development & Commit**: Write your code, adhere to standards, and commit your changes locally while signing your commits.
3. **Push**: Push your branch to your remote repository.
4. **Pull Request**: Open a Pull Request (PR) to the `main` branch of this repository.
5. **Review**: Wait for feedback and approval from the maintainers before merging.

## Code Style & Quality

To maintain a clean and consistent codebase, please adhere to the following guidelines:
- **Code Style**: Adhere to PEP 8 standards.
- **Formatting & Imports**: Use `black` for code formatting and `isort` for import sorting and organization.
- **Typing**: Python Type Hints are highly recommended for all new functions and classes.
- **Docstrings**: Document your changes using the Google/NumPy docstring style for modules, classes, and functions.
- **Testing**: Ensure all existing tests pass using `pytest`. Write new unit or integration tests to cover your changes.

## Commit Signing (DCO / Sign-off)

To ensure supply chain security and legal traceability:
- All commits must be cryptographically signed (`git commit -S`).
- Each commit must include a Developer Certificate of Origin (DCO) sign-off line: `Signed-off-by: Your Name <your.email@example.com>`. This can be done automatically using git's `-s` flag (`git commit -s`).
- Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org) convention.
