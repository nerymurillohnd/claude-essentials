<!--
  Reusable resolved technical debt ledger.

  Copy this file to the repository's maintenance documentation area. Replace
  every {{placeholder}}, remove unused optional fields, and duplicate the entry
  block for each verified resolution.
-->

# ✅ Resolved Debt

> [!NOTE]
> An auditable history of maintenance and technical debt that was corrected and verified: what was wrong, what changed, and the evidence that closes it. Entries move here from `pending-debt.md`.

> [!IMPORTANT]
> Keep resolved entries as dated historical records. If a later change invalidates a resolution, keep the original entry and open a new pending item that links back to it. Do not rewrite history.

## 📚 Index

| Date           | ID          | Resolution                 | Superseded        |
| -------------- | ----------- | -------------------------- | ----------------- |
| {{YYYY-MM-DD}} | {{DEBT-ID}} | {{Short resolution title}} | {{none, or link}} |

## 🏁 Resolved items

### {{DEBT-ID}} — {{Short resolution title}}

| Field                            | Value                                                         |
| -------------------------------- | ------------------------------------------------------------- |
| **📅 Resolved on**               | {{YYYY-MM-DD}}                                                |
| **🧭 Original pending record**   | {{Link to the pending-debt.md entry this closes, or "none".}} |
| **👤 Owner or responsible area** | {{Person, team, system, or repository area}}                  |

#### ❗ The problem

{{The original limitation, risk, or follow-up item.}}

#### 🔧 The fix

{{The corrective change and the resulting state.}}

#### 🧪 Verification

| Check                                                      | Evidence                              |
| ---------------------------------------------------------- | ------------------------------------- |
| ✅ **Positive:** the fix works                             | {{Commands, tests, review.}}          |
| 🚫 **Negative:** the original failure no longer reproduces | {{Not just that the new path works.}} |

#### 🔗 Follow-up

- **⚠️ Residual risk / follow-up:** {{Anything left over, or "none".}}
- **🔗 Related records:** {{Links to issues, ADRs, PRs, or "none".}}
- **🔁 Superseded by:** {{Link to a newer item when this resolution no longer describes the current state, or "none".}}

<!-- Duplicate the block above for each additional resolution. -->
