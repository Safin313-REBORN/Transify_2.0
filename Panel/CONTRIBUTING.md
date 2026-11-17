# Transify — Contributing Guidelines & Code of Conduct

> **Document:** Developer Guidelines & Open-Source Protocol  
> **Repository:** [https://github.com/Abrarafick/transify](https://github.com/Abrarafick/transify)  

---

## 1. Welcome & Code of Conduct

Thank you for your interest in contributing to **Transify**! We are committed to fostering an inclusive, welcoming, and harassment-free community. All contributors, maintainers, and reviewers are expected to uphold the Contributor Covenant standards.

---

## 2. Core Development Rules & Quality Constraints

### ⚠️ Rule 1: Zero Foreign / Non-ASCII Characters in `src/`
All code, HTML templates, CSS styles, JavaScript files, and inline comments residing in `src/` must remain strictly **100% English**.
- Translations or multilingual dictionaries must be maintained as external UTF-8 localization assets, never hardcoded into template logic.
- Before committing, run the regex audit:
  ```bash
  python -c "import os, re; p=re.compile(r'[\u0980-\u09FF]'); any(p.search(open(os.path.join(r, f), encoding='utf-8').read()) for r, _, fs in os.walk('src') for f in fs if f.endswith(('.py','.html','.js'))) and print('ERROR: Non-ASCII found') or print('OK')"
  ```

### 🧪 Rule 2: 100% Test Passing Mandate
Any pull request or modification must pass all automated test cases without regression:
```bash
python -m unittest tests/test_full_system.py
```
*(All 34 tests must report green `OK` status).*

### ♿ Rule 3: WCAG 2.1 AAA Accessibility Compliance
All newly created UI components must support:
- Keyboard navigation (`tabindex`, focus management, `Escape` key listeners).
- Proper semantic HTML5 tags and descriptive `aria-label` / `aria-live` attributes.
- High-contrast visual styling compatible with Light, Dark, and Contrast themes.

---

## 3. Git Workflow & Branching Strategy

1. **Fork or Branch:** Create a feature branch off `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Commit Conventions:** Write clear, concise, descriptive commit messages:
   - `feat: add HaGRID two-handed gesture support`
   - `fix: resolve Laplacian variance threshold boundary in IQA`
   - `docs: update API documentation for speech endpoints`
3. **Pull Request Protocol:** Ensure all tests pass locally before pushing and submitting a PR against `origin/main`.
