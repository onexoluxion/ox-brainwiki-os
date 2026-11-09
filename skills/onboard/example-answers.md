# Scripted onboarding answers: Northline Calibration Lab (fictional)

Input for an isolated onboarding exercise, not content to seed into a real user's vault. Every name, number and record below is invented. Follow [the current guide](SKILL.md). Select a new vault and separate private runtime folder outside the clone, then use these fictional answers. Capture/promotion/archive are explicitly approved only for this disposable exercise.

## Step 1: requirements check

Check the runtime prerequisites and Obsidian separately. If desktop UI or the chosen client's MCP connection is unavailable, leave that verification pending; do not report full onboarding.

## Step 2: private folder and sources

- New vault root and runtime folder: separate locations supplied by the operator for this exercise. Curated scope: `01_Wiki`.
- Create the seven-folder scaffold. Obsidian opens the vault root, not just `01_Wiki`. Preserve generated `.obsidian` settings on reruns.
- Other sources:
  1. `Quality manual` | `shared drive, folder QMS/current` | `the lab's accreditation procedures and calibration method sheets`
  2. `Job ticket sheet` | `spreadsheet jobs-2026.xlsx on the lab PC` | `every calibration job, its certificate number, due date and technician`
  3. `Distributor price book` | `PDF sent quarterly by the two distributors` | `contract prices and renewal terms per distributor`

## Step 3: Obsidian and identity

- Business name: `Northline Calibration Lab`
- What it sells and where: `Calibration of torque wrenches, pressure gauges and thermometers for machine shops, sold as annual service contracts through our own website and through two regional distributors`
- Goals for the year (`2027`):
  1. `Renew 90 percent of the 140 service contracts before each one expires`
  2. `Cut the time from job received to certificate sent to five working days`
  3. `Add a second distributor region without hiring`
- Operator role and hours: `Co-owner and lead technician; 45 hours a week, 10 of them for admin`
- Agent name: `Gauge`
- Register: `plain words`
- Answer shape: `answer first, then at most three points`
- Banned words: `leverage, synergy`
- Decision filters: `declined`

## Step 4: first cabinet

- Project name: `Contract renewals 2027`; cabinet: `Projects/contract-renewals-2027/`.
- Purpose: `know which contracts expire in the next 60 days and what to quote`
- Authoritative source 1: `Renewal register` | `01_Wiki/contracts/renewal-register.md` | `decides which customer is due and when`
  - Which task does this source answer: `list the contracts that expire in the next 60 days`
  - What evidence does it hold and as of when: `certificate number and expiry date per customer, as of the register's last edit`
- Authoritative source 2: `Pricing sheet 2027` | `01_Wiki/contracts/pricing-2027.md` | `decides the price to quote per instrument class`
  - Which task does this source answer: `quote the renewal price for an instrument class`
  - What evidence does it hold and as of when: `list and contract prices per instrument class, as of the 2027 sheet`
- Results destination: `01_Wiki/contracts/results/` as a dated file
- Known gap: `distributor stock levels are not visible to the lab`

## Disposable fixture preparation before step 5

For this disposable exercise, capture the following invented source text under `00_Raw/`, approve the two curated notes and Wiki index links, then preserve the original source bytes at a new path under `02_Archive/`. Cite that archived source from each note. Both note content and provenance are fictional. At step 5, select the existing approved renewal-register note for retrieval acceptance; the additional capture exercise below tests a new promotion. A normal empty production vault starts with operator-supplied knowledge, not these fixtures.

`01_Wiki/contracts/renewal-register.md`:

```markdown
# Renewal register 2027

| Customer | Instrument | Certificate | Expires |
|---|---|---|---|
| Harbor Machine Works | torque wrench set | CAL-7731 | 2027-03-14 |
| Delta Fabrication | pressure gauge bank | CAL-7740 | 2027-04-02 |

Harbor Machine Works needs its torque wrenches recalibrated before the end of the first quarter; the certificate CAL-7731 expires in March.
```

`01_Wiki/contracts/pricing-2027.md`:

```markdown
# Pricing sheet 2027

Torque wrench recalibration: 85 per instrument, 70 under an annual contract.
Pressure gauge bank: 240 per bank, 200 under an annual contract.
```

## Step 6: retrieval and acceptance

Configure `<runtime>/retrieval.config.json` with the selected absolute root/state and `allow: ["01_Wiki"]`. Record source hashes, index, verify complete/fresh status, then use the actual chosen client (or report client verification pending). Pass `scope="01_Wiki"` to each search and `path="01_Wiki"` to list.

- Exact identifier: `CAL-7731`
- Semantic question: `Which customer must have its torque wrenches recalibrated before the end of the first quarter?`
- Expected: the exact search returns `01_Wiki/contracts/renewal-register.md`; the semantic search returns only the user's own files, with the register among its results (ranking is not asserted); `read` of the exact search's top result shows its content.

## Additional reviewed-capture exercise

- Capture text: `Delta Fabrication asked for a Tuesday delivery slot for all pressure gauge pickups; confirmed by their shop manager on the phone.`
- Approval: `yes`
- Expected: source captured under `00_Raw/`, approved note at `01_Wiki/contracts/<date>-delta-fabrication-tuesday-slot.md`, linked from the Wiki index and citing its unchanged source under `02_Archive/`. Reindex with the external config; status is fresh/complete and an exact scoped search for `Tuesday` returns the curated note.
- Negative control: a separate unapproved Raw capture containing `RAW-ONLY-SYN-992` is not returned by exact search/list; direct connector read is rejected. Archive and identity remain outside retrieval.
- Compare original/hash readback with the file opened in Obsidian when that UI is available. Direct stdio proof does not establish the agent client's connection.

## Re-run check (proof 2)

After the six steps, hash all vault files, external configuration and repository templates. Re-run step 3 alone with the same answers; only the three generated identity files under `<vault>/05_Identity/`, the external onboarding log and explicitly requested app settings may change. Preserve sources, cabinets, captures, config and all repository templates. Rerun scaffold creation separately and verify existing user-edited files, including `.obsidian` settings, stay unchanged.

For an existing-vault exercise, use a custom curated folder and edited root instructions. Reuse the actual scope, present any rule changes as a diff, and preserve the layout. Test stale-state/refusal and reindex recovery only in this disposable exercise, never by changing live notes.
