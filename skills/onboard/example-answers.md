# Scripted onboarding answers: Northline Calibration Lab (fictional)

Input for the onboarding proof. Every name, number and record below is invented. A fresh agent runs `/onboard` from `skills/onboard/SKILL.md` alone and answers each question with the text under the matching step. Create the two seed notes before step 5 so the queries have something to find.

## Step 1: requirements check

No answers; the agent runs the four commands and records exit codes.

## Step 2: private folder and sources

- Root folder: the folder the operator names for this run (a proof run passes it in); the notes subfolder is `notes`.
- Other sources:
  1. `Quality manual` | `shared drive, folder QMS/current` | `the lab's accreditation procedures and calibration method sheets`
  2. `Job ticket sheet` | `spreadsheet jobs-2026.xlsx on the lab PC` | `every calibration job, its certificate number, due date and technician`
  3. `Distributor price book` | `PDF sent quarterly by the two distributors` | `contract prices and renewal terms per distributor`

## Step 3: identity

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

- Project name: `Contract renewals 2027`
- Purpose: `know which contracts expire in the next 60 days and what to quote`
- Authoritative source 1: `Renewal register` | `notes/contracts/renewal-register.md` | `decides which customer is due and when`
  - Which task does this source answer: `list the contracts that expire in the next 60 days`
  - What evidence does it hold and as of when: `certificate number and expiry date per customer, as of the register's last edit`
- Authoritative source 2: `Pricing sheet 2027` | `notes/contracts/pricing-2027.md` | `decides the price to quote per instrument class`
  - Which task does this source answer: `quote the renewal price for an instrument class`
  - What evidence does it hold and as of when: `list and contract prices per instrument class, as of the 2027 sheet`
- Results destination: `notes/contracts/results/` as a dated file
- Known gap: `distributor stock levels are not visible to the lab`

## Seed notes (create under the root before step 5)

`notes/contracts/renewal-register.md`:

```markdown
# Renewal register 2027

| Customer | Instrument | Certificate | Expires |
|---|---|---|---|
| Harbor Machine Works | torque wrench set | CAL-7731 | 2027-03-14 |
| Delta Fabrication | pressure gauge bank | CAL-7740 | 2027-04-02 |

Harbor Machine Works needs its torque wrenches recalibrated before the end of the first quarter; the certificate CAL-7731 expires in March.
```

`notes/contracts/pricing-2027.md`:

```markdown
# Pricing sheet 2027

Torque wrench recalibration: 85 per instrument, 70 under an annual contract.
Pressure gauge bank: 240 per bank, 200 under an annual contract.
```

## Step 5: retrieval

- Exact identifier: `CAL-7731`
- Semantic question: `Which customer must have its torque wrenches recalibrated before the end of the first quarter?`
- Expected: the exact search returns `notes/contracts/renewal-register.md`; the semantic search returns only the user's own files, with the register among its results (ranking is not asserted); `read` of the exact search's top result shows its content.

## Step 6: first capture and health

- Capture text: `Delta Fabrication asked for a Tuesday delivery slot for all pressure gauge pickups; confirmed by their shop manager on the phone.`
- Approval: `yes`
- Expected: the capture lands at `notes/inbox/<date>-delta-fabrication-tuesday-slot.md`, `index` runs again, `status` reports `"fresh": true`, and an exact search for `Tuesday` returns that file.

## Re-run check (proof 2)

After the six steps, hash every file under `identity/`, the cabinet folder and `retrieval.config.json`; re-run step 3 alone with the same answers; hash again. Only `identity/business.md`, `identity/goals.md`, `identity/agent-voice.md` and `identity/onboard-log.md` may change.
