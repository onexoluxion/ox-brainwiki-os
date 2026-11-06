# Sources

Filled by `/onboard` step 2 on {{FILLED_DATE}}. Pointers only: nothing listed here is copied, ingested or indexed by onboarding. Only the notes folder under the root is indexed by the retrieval connector.

## Root folder

{{ROOT_FOLDER}}

Why this field exists: the connector reads from one root and nowhere else; naming it here makes the boundary visible to the operator and the agent.

## Notes folder (under the root)

{{NOTES_FOLDER}}

Why this field exists: an existing notes folder is kept as-is; this line records which subfolder the connector is allowed to index.

## Other sources (pointers)

| Source | Where it lives | What it holds |
|---|---|---|
| {{SOURCE_1_NAME}} | {{SOURCE_1_LOCATION}} | {{SOURCE_1_HOLDS}} |
| {{SOURCE_2_NAME}} | {{SOURCE_2_LOCATION}} | {{SOURCE_2_HOLDS}} |
| {{SOURCE_3_NAME}} | {{SOURCE_3_LOCATION}} | {{SOURCE_3_HOLDS}} |

Why this field exists: the cabinet routes tasks to the authoritative source, and most authoritative sources are not Markdown notes; a pointer tells the agent where to send the operator without pretending to hold the data.
