# Obsidian and Wiki onboarding validation

Date: 2026-11-09. Scope: guided onboarding documentation and first-party text scaffold. Runtime remains v0.3.0; no automatic installer, new dependency, app binary or v0.4.0 runtime change is included.

## Full onboarding acceptance — 2026-11-09

Passed against source commit `1a7d3b07c2eea2d2a12f8294f2ed8860440ec709`, runtime v0.3.0, in one clean fictional Windows vault with separate runtime state. This used installed Obsidian, the locked Python 3.12 environment and a reused public model cache. It was not a fresh-machine installation test.

| Component | Verified result |
|---|---|
| Requirements | `uv sync --frozen --python 3.12`, exit 0; 161 packages checked |
| Folders and identity | All seven folders, proposal/handoff directories, fictional identity and first project cabinet created; 21 relative links resolved |
| Obsidian 1.15.0 | Vault root and folders observed in an isolated desktop profile; a new note was created in Raw; Wiki index and archive citation links opened their intended files; no account or community plugins required |
| Reviewed capture | Proposed fictional source promoted into a linked Wiki note; original archived byte-for-byte; separate unapproved captures remained in Raw |
| Retrieval | Final `index` and `status` exited 0; fresh and complete, with two curated documents |
| Codex CLI 0.167.0 | Exit 0; eight actual MCP calls verified status, scoped list, exact and semantic search, original/hash readback, empty Raw-marker searches and direct Raw-read denial |
| Claude Code 2.1.318 | Exit 0; ten actual MCP calls verified the same checks plus Archive and Identity read denials |
| Preservation | Indexing/retrieval left source hashes unchanged; scaffold rerun preserved every existing vault file and Obsidian settings; saved client connections remained unchanged |
| Privacy and secrets | Fictional content only; no private knowledge copied; local pattern-based secrets scans exited 0 with zero findings |

The desktop test exposed a normal file change: Obsidian converted one note from CRLF to LF without changing its text. Semantic retrieval correctly refused stale state. Reindexing after the desktop edits restored fresh/complete status and both clients passed. A separate client-authentication failure was resolved before Claude acceptance; credentials and local authentication records are not part of this package.

Limits: these results cover the tested clean vault and client versions, not every existing-vault layout, another machine, or a newly installed application. Agent checks used isolated, test-only MCP connections and do not certify persistent user registrations or other chat surfaces. Runtime remains v0.3.0; no installed/global skill mirrors changed. Raw logs, local paths, account identifiers, credentials and state are excluded from this public summary.

## Initial documentation and runtime checks — historical

The following earlier checks ran on Windows with the locked Python 3.12 environment. All content was fictional, in a temporary vault and separate runtime folder outside the clone. No private vault or real client configuration was changed in that initial exercise.

| Check | Observed result |
|---|---|
| Skill frontmatter validation | `quick_validate.py skills/onboard`, exit 0, valid |
| Existing regression suite | `python -m unittest discover`, exit 0; 61 tests, one skipped |
| Guided scaffold exercise | Seven folders, root rules, generated identity, cabinet and source/knowledge links created in isolation |
| Reruns | Create-missing scaffold and step-3 identity rerun preserved existing bytes, including edited root rules and synthetic `.obsidian` settings |
| Real backend | `index` and `status` with external config both exited 0, fresh and complete |
| Direct MCP stdio | Exactly four tools; scoped list, exact search, semantic paraphrase and original/hash readback passed |
| Scope boundary | Raw, Identity and Archive markers absent from exact search; direct reads rejected |
| Capture and source integrity | Approved source moved byte-for-byte to a new archive path; indexing and reads left all source hashes unchanged |
| Stale state | A disposable note edit caused semantic refusal; restoring/reindexing recovered fresh state |
| Existing custom scope | Separate disposable `Knowledge` folder with `Home.md` index passed real-backend exact/semantic/list/read checks; Raw stayed excluded, source hashes stayed unchanged, and no competing `01_Wiki` was created. Follow-up forward review used custom `Inbox`/`Sources` capture/archive locations. |
| Local references | 45 relative file links resolved across onboarding, scaffold and related guides |
| Local secrets | `rafter secrets . --engine patterns --json`, exit 0, zero findings; secrets-only, not SAST/SCA |
| Private-content sweep | 62 distributable files checked for known private identifiers, account strings and machine/vault paths; zero matches |
| Independent read-only review | Fresh/existing-vault scenarios reviewed; scope, trust, rerun and pending-verification clarifications applied. Automated review found a hardcoded new-vault promotion path; existing-vault promotion and index selection now follow the recorded curated folder. |

Security surface review: documentation, first-party agent guidance and static text templates only; no runtime implementation, dependency, permissions or network endpoint changed. Review covered untrusted-source instructions, explicit write authorization, private-output placement, literal/contained paths, non-overwriting archival moves and narrow retrieval scope. Under the docs-only quota rule, no remote Rafter scan was run.

Limits of the initial exercise: Obsidian desktop opening, clicking the archive link inside Obsidian, and model-mediated retrieval through a chosen agent client had not yet been exercised. The follow-up acceptance above closes those gaps for its tested setup. Direct stdio checks alone establish runtime behavior only. Existing-vault adoption was reviewed procedurally; synthetic rerun checks do not cover every custom layout. Each installation still needs its own dated receipt. No installed/global skill mirrors were changed.

Obsidian is separately installed under its [own license](https://obsidian.md/license). The base app is free for personal and commercial use; account-based services and community plugins are unnecessary. OX BrainWiki OS does not redistribute Obsidian or imply endorsement. Its package dependencies remain listed in [Third-party notices](THIRD_PARTY_NOTICES.md).
