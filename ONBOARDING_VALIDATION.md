# Obsidian and Wiki onboarding validation

Date: 2026-11-09. Scope: guided onboarding documentation and first-party text scaffold. Runtime remains v0.3.0; no automatic installer, new dependency, app binary or v0.4.0 runtime change is included.

The following checks ran on Windows with the locked Python 3.12 environment. All content was fictional, in a temporary vault and separate runtime folder outside the clone. No private vault or real client configuration was changed.

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

Limits: Obsidian desktop opening, clicking the archive link inside Obsidian, and model-mediated retrieval through a chosen agent client were not exercised by this update. Direct stdio checks establish runtime behavior only. Existing-vault adoption was reviewed procedurally; the synthetic rerun checks do not cover every custom layout. Full onboarding on an actual installation still requires those desktop/client checks and its own dated receipt. No installed/global skill mirrors were changed.

Obsidian is separately installed under its [own license](https://obsidian.md/license). The base app is free for personal and commercial use; account-based services and community plugins are unnecessary. OX BrainWiki OS does not redistribute Obsidian or imply endorsement. Its package dependencies remain listed in [Third-party notices](THIRD_PARTY_NOTICES.md).
