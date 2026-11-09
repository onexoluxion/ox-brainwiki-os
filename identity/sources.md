# Sources

Rendered into the private vault's `05_Identity/sources.md` by onboarding step 2 on {{FILLED_DATE}}. Keep this source template unchanged in the clone. Other sources are pointers only; naming them does not authorize copying or ingestion. Retrieval indexes only the selected curated folder.

## Root folder

{{ROOT_FOLDER}}

Why this field exists: the connector reads from one root and nowhere else; naming it here makes the boundary visible to the operator and the agent.

## Curated notes folder (under the root)

{{NOTES_FOLDER}}

Why this field exists: new vaults use `01_Wiki`; existing vaults keep their selected curated folder. This line records the relative subfolder the connector is allowed to index. Raw, Archive, Identity and app settings stay outside the default scope.

## Other sources (pointers)

| Source | Where it lives | What it holds |
|---|---|---|
| {{SOURCE_1_NAME}} | {{SOURCE_1_LOCATION}} | {{SOURCE_1_HOLDS}} |
| {{SOURCE_2_NAME}} | {{SOURCE_2_LOCATION}} | {{SOURCE_2_HOLDS}} |
| {{SOURCE_3_NAME}} | {{SOURCE_3_LOCATION}} | {{SOURCE_3_HOLDS}} |

Why this field exists: the cabinet routes tasks to the authoritative source, and most authoritative sources are not Markdown notes; a pointer tells the agent where to send the operator without pretending to hold the data.
