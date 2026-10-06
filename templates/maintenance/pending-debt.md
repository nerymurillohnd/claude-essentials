<!--
  Reusable pending technical debt ledger.

  Copy this file to the repository's maintenance documentation area. Replace
  every {{placeholder}}, remove unused optional fields, and duplicate the entry
  block for each unresolved item.
-->

# 🧾 Pending Debt

> [!NOTE]
> A living record of unresolved technical or maintenance conditions that need follow-up, reassessment, or verified remediation.

## 🎯 Entry criteria

Add an item only when **all** of these hold:

- ✅ A specific unresolved condition is observable or supported by traceable evidence, not speculation.
- ✅ It has a meaningful operational, security, reliability, compatibility, or maintainability impact.
- ✅ There is a concrete next action, or a concrete condition that would trigger reassessment.
- ✅ No other active record tracks it (an open issue, another ADR's follow-up), unless this ledger is the designated place.

> [!WARNING]
> Do not add general improvement ideas, unverified speculation, or a copy of every backlog task.

## 🔄 Record maintenance

| Action         | When                                            | Rule                                                                    |
| -------------- | ----------------------------------------------- | ----------------------------------------------------------------------- |
| ➕ **Append**  | A new condition appears                         | Check for an existing entry on the same condition first.                |
| ✏️ **Update**  | Evidence, impact, owner, or next action changes | Revise in place. Keep confirmed facts apart from inference.             |
| ✅ **Resolve** | The fix is verified                             | Move the entry to `resolved-debt.md` with its ID. Never just delete it. |

> [!IMPORTANT]
> An item moves to resolved debt only after the fix works **and** the original failure no longer reproduces.

## 🚦 Status legend

| Icon | Status        | Meaning                                                     |
| ---- | ------------- | ----------------------------------------------------------- |
| 🟡   | Pending       | Confirmed, not yet worked on                                |
| 🔵   | In progress   | A change is under way                                       |
| 🟠   | Blocked       | Waiting on a decision, access, or an external party         |
| 🔴   | Risk accepted | Known and deliberately kept; review condition still applies |

## 📋 Index

| ID          | Title                | Status     | Category     | Next action                  |
| ----------- | -------------------- | ---------- | ------------ | ---------------------------- |
| {{DEBT-ID}} | {{Short debt title}} | 🟡 Pending | {{category}} | {{smallest concrete action}} |

## 📂 Open items

### {{DEBT-ID}} — {{Short debt title}}

| Field        | Value                                                                              |
| ------------ | ---------------------------------------------------------------------------------- |
| **Status**   | 🟡 Pending                                                                         |
| **Category** | {{e.g. security, compatibility, cost, quality}}                                    |
| **Owner**    | {{Person, team, system, or repository area, or "unassigned" if genuinely unowned}} |

#### 🔎 Evidence

- **✅ Confirmed facts:** {{Paths, revisions, commands, dates: what is actually verified.}}
- **💭 Inferences:** {{Reasoned conclusions not directly verified, or "none".}}
- **❓ Open questions:** {{Unresolved questions that affect the assessment, or "none".}}

#### 📈 Impact and next step

- **💥 Impact / risk:** {{Current or plausible impact.}}
- **👉 Next action:** {{The smallest concrete action that advances or resolves this.}}
- **🔁 Review condition:** {{Event, date, or evidence that triggers reassessment or permits closure.}}
- **🔗 Related records:** {{Links to issues, ADRs, PRs, or "none".}}

<!-- Duplicate the block above for each additional open item. -->
