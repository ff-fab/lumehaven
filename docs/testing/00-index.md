# Test Strategy

> **Scope:** This document defines _how_ we test lumehaven. For the _what_ and _why_ of
> our testing decisions, see
> [ADR-006: Testing Strategy](../adr/ADR-006-testing-strategy.md).
>
> **Relationship to ADR-006:** The ADR defines the architectural decision (pytest +
> Robot Framework hybrid). This strategy expands on _how_ to implement that decision
> with specific techniques, targets, and tooling.

## TL;DR

| Aspect                  | Decision                                                                  |
| ----------------------- | ------------------------------------------------------------------------- |
| **Design techniques**   | EP (implicit via parametrization), BVA, state transition, decision tables |
| **Unit test isolation** | Sociable units—real store, mock external I/O                              |
| **Integration scope**   | Full vertical slice with mock OpenHAB server                              |
| **Line coverage**       | ≥80% minimum, risk-based targets up to 90%                                |
| **Branch coverage**     | ≥70-85% depending on component risk                                       |
| **Complexity**          | Enforced: radon/xenon (CC), flake8-cognitive-complexity                   |
| **Enforcement**         | From day one—coverage gates are blocking in CI                            |
| **Quality platform**    | SonarQube planned for later                                               |

## Chapters

1. [Test Design Techniques](01-test-design-techniques.md) — ISTQB black-box and
   white-box techniques applied to our components
2. [Test Levels](02-test-levels.md) — Unit, integration, E2E boundaries and
   responsibilities
3. [Coverage Strategy](03-coverage-strategy.md) — Metrics, targets, risk-based
   prioritization
4. [Test Organization](04-test-organization.md) — File structure, naming, fixtures,
   markers
5. [Tooling & Configuration](05-tooling-configuration.md) — pytest, Robot Framework, CI
   setup

## Current State

**Known Issues:**

- [ ] Failing unit test (to be documented and fixed after strategy completion)
- [ ] Missing test fixtures for OpenHAB mock data
- [ ] No coverage configuration

**Coverage Gaps (High Priority):**

| Component                     | Lines | Test Status |
| ----------------------------- | ----- | ----------- |
| `adapters/openhab/adapter.py` | 466   | ❌ Untested |
| `adapters/manager.py`         | 216   | ❌ Untested |
| `config.py`                   | 253   | ❌ Untested |

See [Coverage Strategy](03-coverage-strategy.md) for the full risk-based prioritization.

## References

- [ADR-006: Testing Strategy](../adr/ADR-006-testing-strategy.md) — Architectural
  decision
- [pytest documentation](https://docs.pytest.org/)
- [Robot Framework User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- [ISTQB Foundation Syllabus](https://www.istqb.org/)
