# Homelab Atlas roadmap

Status: public candidate approved for publication on 2026-09-04.

Change class: Standard. This repository contains offline documentation tooling and synthetic fixtures. Any future live integration remains read-only.

## Phase 1: public safety contract

Outcome: define the public behavior, privacy boundary, contribution rules, and reproducible gate.

Exit criteria: repository contracts name synthetic-only inputs, read-only commands, owned outputs, and the publication approval gate.

Validation: review `AGENTS.md`, `SPEC.md`, `SECURITY.md`, and `CONTRIBUTING.md` against implementation.

## Phase 2: synthetic working demo

Outcome: a small topology demonstrates authored Mermaid, sidecars, drift checking, and safe rendering.

Exit criteria: fixture verification passes; mutations fail; rendering is idempotent; safety tests cover destructive commands, injection, and traversal.

Validation: `PATH="$PWD/.venv/bin:$PATH" bin/validate`.

## Phase 3: public repository controls

Outcome: CI, CodeQL, Gitleaks, Dependabot, license, and synthetic screenshots match the published reference standard.

Exit criteria: workflow syntax passes local checks where tooling is available; action references use immutable SHAs; documentation names every check accurately.

Validation: local YAML parse, Gitleaks if installed, and independent review.

## Phase 4: publication candidate

Outcome: a privacy-clean candidate is ready for owner inspection.

Exit criteria: complete diff reread, secret and identity scan, fresh multi-model review, browser screenshot check, and clean validation on the final revision.

Publication requires separate explicit owner approval. Creating a GitHub repository, pushing, tagging, and releasing are outside this phase.
