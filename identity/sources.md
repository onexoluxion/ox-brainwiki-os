# Sources

Rendered into the private vault's `05_Identity/sources.md` by onboarding step 2 on {{FILLED_DATE}}. Keep this source template unchanged in the clone. Other sources are pointers only; naming them does not authorize copying or ingestion. Retrieval indexes only the selected curated folder.

## Root folder

{{ROOT_FOLDER}}

Why this field exists: the connector reads from one root and nowhere else; naming it here makes the boundary visible to the operator and the agent.

## Curated notes folder (under the root)

{{NOTES_FOLDER}}

Why this field exists: new vaults use `01_Wiki`; existing vaults keep their selected curated folder. This line records the relative subfolder the connector is allowed to index. Raw, Archive, Identity and app settings stay outside the default scope.

## Other sources (pointers)

Required data, scope and history — {{REQUIRED_DATA}}

Operator-confirmed selection and coverage by source — {{SELECTED_SOURCES}}

| Source | Where it lives | Verified coverage | Checked on and data as of | Allowed lag | Gaps |
|---|---|---|---|---|---|
| {{SOURCE_NAME}} | {{SOURCE_LOCATION}} | {{SOURCE_COVERAGE}} | {{SOURCE_EVIDENCE}} | {{SOURCE_ALLOWED_LAG}} | {{SOURCE_GAPS}} |

Separate private repository — {{PRIVATE_REPOSITORY_CHOICE}}
