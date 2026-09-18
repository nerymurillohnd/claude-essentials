import assert from "node:assert/strict";
import { test } from "node:test";
import { hasChangelogEntry } from "./changelog.mjs";

const sample = `# Changelog

## [Unreleased]

## [2.0.0-beta.1] - 2026-09-25

### Changed

- **Breaking:** Renamed the skill.

## [1.1.0] - 2026-09-20

### Added

- New skill.

## [1.0.0] - 2026-09-01

### Added

- Initial release.

[Unreleased]: https://github.com/o/r/compare/demo--v1.1.0...HEAD
[1.1.0]: https://github.com/o/r/compare/demo--v1.0.0...demo--v1.1.0
`;

test("hasChangelogEntry matches exact dated headings only", () => {
  assert.equal(hasChangelogEntry(sample, "1.1.0"), true);
  assert.equal(hasChangelogEntry(sample, "2.0.0-beta.1"), true);
  assert.equal(hasChangelogEntry(sample, "1.2.0"), false);
  assert.equal(hasChangelogEntry(sample, "1.1"), false);
  assert.equal(hasChangelogEntry("## [3.0.0] - {{YYYY-MM-DD}}\n", "3.0.0"), false);
  assert.equal(hasChangelogEntry(null, "1.0.0"), false);
});
