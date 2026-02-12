# T8: E2E Testing Tool Evaluation

- **Source:** ADR-006 (Testing Strategy), Phase 4 planning
- **Context:** ADR-006 Phase 4 assumes Robot Framework + Browser Library for E2E tests.
  New tools (notably Rodney) have emerged that warrant evaluation before committing to an
  implementation. This document captures the full deliberation.
- **Trigger:** Phase 4 — before implementing `lh-809.2` (Robot Framework E2E tests)
- **Outcome:** ADR-012 (E2E Testing Tool Selection), or amendment to ADR-006

## Background

The lumehaven frontend (Phase 3) will be a React SPA served by Vite on `:5173`, talking
to the FastAPI BFF on `:8000`. E2E tests need to exercise the full stack: browser →
frontend → backend → mock adapter. The testing infrastructure must work in:

1. **Local dev** — inside the devcontainer (headless Chrome, no display)
2. **CI** — GitHub Actions, running inside the devcontainer image
3. **Agent workflows** — AI agents creating and running tests as part of their work

### Existing Infrastructure

- Robot Framework is already used for **integration tests** (Phase 2) — 18 tests
  exercising the REST API and SSE streams against a mock OpenHAB backend
- The Dockerfile pre-installs browser automation system libraries (libglib, libnss,
  libatk, libgbm, etc.) in anticipation of Phase 4
- Showboat is used for agent proof-of-work — E2E tool should ideally be scriptable for
  showboat demos
- Docker Compose infrastructure for CI/E2E is planned (`lh-809.3`) but not yet built

## Options

### Option A: Robot Framework + Browser Library (Playwright-based)

**What:** [Browser Library](https://robotframework-browser.org/) provides Playwright
bindings for Robot Framework. Tests are written in RF keyword syntax (`.robot` files),
same as the existing integration tests.

**Implementation:**

```robot
*** Settings ***
Library    Browser

*** Test Cases ***
Dashboard Shows Signal Values
    New Browser    headless=true
    New Page       http://localhost:5173
    Wait For Elements State    css=.signal-card    visible
    Get Text    css=.signal-value    ==    21.5 °C
```

**Advantages:**

- Extends existing RF investment — same language, same CI infrastructure, shared keywords
- Playwright engine underneath: auto-wait, multi-browser, network interception
- Keyword-driven tests are readable by non-developers (acceptance test style)
- `rfbrowser init` installs Playwright browsers automatically
- Python-native — fits the backend ecosystem, no additional runtime needed

**Disadvantages:**

- Browser Library adds ~200 MB for Playwright browsers (Chromium, Firefox, WebKit)
- RF keyword abstraction adds indirection — debugging is harder than raw Playwright
- Slower feedback loop than standalone Playwright (RF overhead per test)
- Browser Library version lags behind Playwright releases

### Option B: Playwright (standalone, via Node.js or Python)

**What:** [Playwright](https://playwright.dev/) directly, either via the Node.js API
(`@playwright/test`) or the Python API (`playwright` package). Tests written in
TypeScript/Python, not RF keywords.

**Implementation (Python):**

```python
from playwright.sync_api import sync_playwright

def test_dashboard_shows_signals():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://localhost:5173")
        page.wait_for_selector(".signal-card")
        assert page.text_content(".signal-value") == "21.5 °C"
        browser.close()
```

**Advantages:**

- Direct API access — no abstraction layer, full Playwright power
- Excellent DX: codegen (`playwright codegen`), trace viewer, inspector
- Python binding available — can integrate with pytest (same test runner as unit tests)
- Fastest execution of all Playwright-based options
- Best documentation and community support of any browser automation tool

**Disadvantages:**

- Two testing DSLs: pytest for unit/E2E, RF for integration — conceptual split
- Doesn't leverage existing RF infrastructure and shared keywords
- Python Playwright binding is maintained but Node.js is the primary target
- Still requires ~200 MB for browser binaries

### Option C: Rodney (CLI-driven Chrome automation)

**What:** [Rodney](https://github.com/simonw/rodney) is a Go CLI tool that drives a
persistent headless Chrome via the DevTools Protocol (rod library). Each command is a
short-lived process: `rodney start`, `rodney open URL`, `rodney text "h1"`, etc.

**Implementation (shell script):**

```bash
rodney start
rodney open http://localhost:5173
rodney waitstable
rodney text ".signal-value"  # prints "21.5 °C"
rodney exists ".signal-card" # exit 0 if found
rodney ax-find --role button --json  # accessibility audit
rodney stop
```

**Advantages:**

- Shell-native — perfect for showboat demos (`showboat exec demo.md bash "rodney ..."`)
- No test framework needed — assertions via exit codes and text comparison
- Persistent Chrome process — fast for multi-step interactive scenarios
- Built-in accessibility testing (`ax-tree`, `ax-find`, `ax-node`)
- Tiny binary (~10 MB), no browser download needed (uses system Chrome/Chromium)
- Agent-friendly — every command is a single CLI invocation with clear output

**Disadvantages:**

- **Brand new** (v0.3.0, released February 2026) — no production track record
- Single browser only (Chrome/Chromium) — no Firefox or WebKit testing
- No test runner integration — assertions are manual (`if rodney exists ...`)
- No auto-wait on navigation (must explicitly `rodney waitstable`)
- No parallel test execution support
- No network interception, request mocking, or route handling
- Limited ecosystem — one maintainer (Simon Willison), no plugins
- Requires Chrome/Chromium installed in the container
- Shell-based tests are harder to maintain at scale than structured test frameworks

### Option D: Selenium (WebDriver)

**What:** [Selenium](https://www.selenium.dev/) is the original browser automation
framework, using the W3C WebDriver protocol. Tests typically written in Python with
pytest-selenium or unittest.

**Implementation:**

```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def test_dashboard_shows_signals():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver = webdriver.Chrome(options=options)
    driver.get("http://localhost:5173")
    wait = WebDriverWait(driver, 10)
    card = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".signal-card")))
    value = driver.find_element(By.CSS_SELECTOR, ".signal-value").text
    assert value == "21.5 °C"
    driver.quit()
```

**Advantages:**

- W3C standard — widest browser support (Chrome, Firefox, Safari, Edge)
- Mature ecosystem (20+ years), extensive documentation
- Python-native — integrates with pytest
- WebDriver BiDi emerging for modern protocol features

**Disadvantages:**

- Verbose API — more boilerplate than Playwright for equivalent tests
- No built-in auto-wait — must manually manage waits (common source of flaky tests)
- Requires separate ChromeDriver binary matching the Chrome version
- Slower than Playwright (HTTP-based protocol vs WebSocket)
- No built-in trace viewer, codegen, or screenshot comparison
- Generally considered legacy — most new projects choose Playwright instead

### Option E: Cypress

**What:** [Cypress](https://www.cypress.io/) is a JavaScript-native E2E testing
framework that runs tests inside the browser process itself.

**Implementation:**

```javascript
describe("Dashboard", () => {
  it("shows signal values", () => {
    cy.visit("http://localhost:5173");
    cy.get(".signal-card").should("be.visible");
    cy.get(".signal-value").should("have.text", "21.5 °C");
  });
});
```

**Advantages:**

- Excellent DX — time-travel debugger, automatic screenshots, video recording
- Built-in retry-ability — automatic waiting and retry on assertions
- Network stubbing built-in (`cy.intercept()`)
- Large ecosystem with plugins

**Disadvantages:**

- **JavaScript-only** — doesn't fit the Python backend ecosystem
- No multi-tab, multi-window, or multi-browser support
- Chromium-family + Firefox only (no WebKit)
- Requires Node.js test runner — separate from pytest/RF infrastructure
- Tests run inside the browser — different execution model, some limitations
- Commercial features (dashboard, parallelization) require paid plan

## Evaluation Criteria

| Criterion                        | Weight | A (RF+BL) | B (Playwright) | C (Rodney) | D (Selenium) | E (Cypress) |
| -------------------------------- | ------ | --------- | --------------- | ---------- | ------------- | ----------- |
| Extends existing RF infra        | High   | 5         | 2               | 1          | 2             | 1           |
| Devcontainer/CI simplicity       | High   | 4         | 4               | 5          | 3             | 3           |
| Accessibility testing            | Medium | 3         | 4               | 5          | 2             | 2           |
| Agent/showboat friendliness      | Medium | 2         | 3               | 5          | 2             | 2           |
| Maturity & ecosystem stability   | High   | 4         | 5               | 1          | 5             | 4           |
| Multi-browser support            | Low    | 5         | 5               | 1          | 5             | 3           |
| Python ecosystem fit             | Medium | 5         | 4               | 3          | 4             | 1           |
| Test maintenance at scale        | Medium | 4         | 5               | 2          | 3             | 4           |

_Scale: 1 (poor) to 5 (excellent). Weights reflect lumehaven's priorities._

## Preliminary Assessment

**Not yet decided** — this evaluation is deferred until Phase 4 begins.

Initial observations:

- **Options A and B** are the strongest candidates. A extends existing RF investment;
  B provides the best standalone DX. Both use Playwright under the hood.
- **Option C (Rodney)** is compelling for agent workflows and showboat integration but
  too immature for primary E2E testing. Could serve as a **complementary tool** for
  ad-hoc agent demos and accessibility audits, while A or B handles structured tests.
- **Option D (Selenium)** is viable but offers no advantage over Playwright for a
  greenfield project.
- **Option E (Cypress)** is a poor fit — JavaScript-only, doesn't integrate with the
  Python/RF ecosystem.

A promising hybrid: **Option A (or B) for structured E2E tests** + **Option C for agent
showboat demos** — leveraging Rodney's CLI simplicity for quick proof-of-work while
using a mature framework for the test suite itself.

## Decision

**Deferred.** To be resolved when Phase 4 (`lh-809.2`) begins. Gate task in beads
blocks E2E implementation until this evaluation is completed. Outcome should be
documented as ADR-012 or an amendment to ADR-006.
