// @ts-check
import assert from "node:assert/strict";
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { listPluginDirs, rootDir } from "./plugins.mjs";
import {
  badgeMinimums,
  catalogRows,
  checkChangelogLinks,
  checkLicense,
  checkNetworkClaim,
  checkPluginReadme,
  checkRequirementMinimums,
  checkRootCatalog,
  headerBadges,
  headingTitle,
  LICENSE_TEMPLATE,
  licenseSha,
  PLUGIN_TEMPLATE,
  readContract,
  sectionBodies,
  sectionTitles,
  surfaceStatus,
  validateReadmes,
} from "./readme-contract.mjs";

const template = readFileSync(join(rootDir, PLUGIN_TEMPLATE), "utf8");
const contract = readContract(template);
const fence = "```";

/** @param {Record<string, string>} [overrides] Section title → body replacement. */
function readme(overrides = {}) {
  const sections = contract.order.filter((title) => title !== "Other components");
  const body = sections.map((title) => {
    if (overrides[title] !== undefined) return `## 🔹 ${title}\n\n${overrides[title]}`;
    if (title === "Installation") {
      return [
        "## ⚡ Installation",
        "",
        `${fence}text`,
        "/plugin install demo@claude-essentials",
        fence,
        "",
        "**Claude Cowork** — **Customize → Plugins → Add marketplace**, enter the repo.",
        "",
        "In Cowork, use **Update** on the marketplace, and **Uninstall** on the plugin.",
      ].join("\n");
    }
    return `## 🔹 ${title}\n\nText.`;
  });
  const badges = [
    "[![Version](https://img.shields.io/badge/dynamic/json?url=x%2Fplugins%2Fdemo%2F.claude-plugin%2Fplugin.json&query=v)](CHANGELOG.md)",
    "[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)",
    "[![Kind](https://img.shields.io/badge/kind-skill--only-8A2BE2)](x)",
    "[![Claude Code](https://img.shields.io/badge/Claude_Code-supported-D97757)](#)",
    "[![Claude Cowork](https://img.shields.io/badge/Claude_Cowork-not_tested-D97757)](#)",
  ];
  return ["# 🧪 Demo", "", ...badges, "", ...body].join("\n");
}

test("the template yields the required sections in order, minus the optional ones", () => {
  assert.ok(contract.required.includes("What it does not do"));
  assert.ok(contract.required.includes("Limitations"));
  assert.ok(!contract.required.includes("FAQ"));
  assert.ok(!contract.required.includes("Other components"));
  assert.ok(contract.badgeLabels.has("Git") && contract.badgeLabels.has("Bash"));
});

test("headingTitle drops the marker and the emoji", () => {
  assert.equal(headingTitle("## 🔐 Security"), "Security");
  assert.equal(headingTitle("# 🛡️ Block No Verify"), "Block No Verify");
});

test("sections inside code fences and comments are ignored", () => {
  const md = `## A\n${fence}text\n## Not a section\n${fence}\n<!--\n## Hidden\n-->\n## B`;
  assert.deepEqual(sectionTitles(md), ["A", "B"]);
  assert.deepEqual(sectionBodies(md, true).get("A"), [`${fence}text`, "## Not a section", fence]);
});

test("a conforming README passes", () => {
  assert.deepEqual(checkPluginReadme("demo", readme(), contract), []);
});

test("missing, unknown, and reordered sections are reported", () => {
  const missing = readme().replace(/## 🔹 Security\n\nText\./, "");
  assert.match(
    checkPluginReadme("demo", missing, contract).join("\n"),
    /missing required section "Security"/,
  );
  const unknown = `${readme()}\n## 🔹 Extras\n\nText.`;
  assert.match(checkPluginReadme("demo", unknown, contract).join("\n"), /unknown section "Extras"/);
  const swapped = readme()
    .replace("## 🔹 Security", "## 🔹 TMP")
    .replace("## 🔹 Limitations", "## 🔹 Security")
    .replace("## 🔹 TMP", "## 🔹 Limitations");
  assert.match(checkPluginReadme("demo", swapped, contract).join("\n"), /out of template order/);
});

test("placeholders, extra alerts, unlabeled fences, and missing Cowork steps are reported", () => {
  const problems = checkPluginReadme(
    "demo",
    readme({
      Security: "{{fill me}}",
      Limitations: "> [!NOTE]\n> a\n\n> [!TIP]\n> b",
      Examples: `${fence}\nplain\n${fence}`,
      Installation: `${fence}text\n/plugin install demo@claude-essentials\n${fence}`,
    }),
    contract,
  ).join("\n");
  assert.match(problems, /unreplaced \{\{placeholder\}\}/);
  assert.match(problems, /"Limitations" has 2 alerts/);
  assert.match(problems, /1 code block\(s\) without a language/);
  assert.match(problems, /missing the Claude Cowork install steps/);
  assert.match(problems, /missing the Cowork update\/uninstall line/);
});

test("badges must come from the template catalog and read the plugin's own version", () => {
  const bad = readme()
    .replace("plugins%2Fdemo%2F", "plugins%2Fother%2F")
    .replace("# 🧪 Demo\n", "# 🧪 Demo\n![Rust](https://img.shields.io/badge/Rust-1.80-000)\n");
  const problems = checkPluginReadme("demo", bad, contract).join("\n");
  assert.match(problems, /badge "Rust" is not in the template's requirement badge catalog/);
  assert.match(problems, /Version badge must read plugins\/demo/);
  assert.equal(headerBadges(readme()).size, 5);
});

test("surfaceStatus maps badge statuses to the catalog vocabulary", () => {
  assert.equal(surfaceStatus("https://img.shields.io/badge/Claude_Code-not_tested-D97757"), "🧪");
  assert.equal(
    surfaceStatus("https://img.shields.io/badge/Claude_Cowork-not_supported-D97757"),
    "❌",
  );
  assert.equal(surfaceStatus("https://img.shields.io/badge/Claude_Code-%7B%7Bstatus%7D%7D-x"), "");
});

const entry = {
  id: "demo",
  displayName: "Demo",
  kind: "skill-only",
  code: "✅",
  cowork: "🧪",
  minimums: new Map([["jq", "1.6"]]),
};
/** @param {string} rows */
const root = (rows) =>
  `## 🧩 Plugin catalog\n\n| Plugin | Description | Kind | Claude Code | Claude Cowork | Additional requirements |\n| --- | --- | --- | :---: | :---: | --- |\n${rows}\n\n## ⚡ Quick start`;

test("the root catalog must list every plugin exactly once, matching its README", () => {
  const good = root(
    "| [Demo](plugins/demo/README.md) | Does x. | `skill-only` | ✅ | 🧪 | `jq` ≥ 1.6 |",
  );
  assert.deepEqual(catalogRows(good).length, 1);
  assert.deepEqual(checkRootCatalog(good, [entry]), []);
  const placeholder = root("| _No plugins published yet_ | Soon. | — | — | — | — |");
  const problems = checkRootCatalog(placeholder, [entry]).join("\n");
  assert.match(problems, /still has the "_No plugins published yet_" row/);
  assert.match(problems, /must list exactly demo/);
  const drift = root("| [Demo](plugins/demo/README.md) | Does x. | `bundle` | 🧪 | 🧪 | None |");
  assert.match(checkRootCatalog(drift, [entry]).join("\n"), /kind must be `skill-only`/);
  assert.match(checkRootCatalog(drift, [entry]).join("\n"), /Claude Code must be ✅/);
  assert.match(checkRootCatalog(drift, [entry]).join("\n"), /must include jq ≥ 1\.6/);
  assert.deepEqual(checkRootCatalog(placeholder, []), []);
});

test("this repository's READMEs conform", () => {
  assert.deepEqual(validateReadmes(rootDir, listPluginDirs()), []);
});

test("every plugin-shape template keeps the master template's sections and order", () => {
  for (const shape of ["plugin-bundle", "plugin-skill-only", "plugin-agent-only"]) {
    const text = readFileSync(join(rootDir, "templates", shape, "README.md"), "utf8");
    const found = sectionTitles(text);
    const missing = contract.required.filter((title) => !found.includes(title));
    assert.deepEqual(missing, [], `${shape} is missing ${missing.join(", ")}`);
    const known = found.filter((title) => contract.order.includes(title));
    assert.deepEqual(known, found, `${shape} has sections the master template lacks`);
    assert.deepEqual(
      known,
      contract.order.filter((title) => known.includes(title)),
      `${shape} is out of order`,
    );
  }
});

test("a plugin LICENSE must be the verbatim Apache-2.0 text and be declared", () => {
  const sha = licenseSha(readFileSync(join(rootDir, LICENSE_TEMPLATE), "utf8"));
  const good = readFileSync(join(rootDir, "plugins", "block-no-verify", "LICENSE"));
  assert.deepEqual(checkLicense("demo", good, "Apache-2.0", sha), []);
  const altered = Buffer.from(
    good.toString("utf8").replace("WITHOUT WARRANTIES", "WITH WARRANTIES"),
  );
  assert.match(
    checkLicense("demo", altered, "Apache-2.0", sha).join("\n"),
    /not the verbatim Apache-2.0 text/,
  );
  assert.match(checkLicense("demo", good, "MIT", sha).join("\n"), /license must be "Apache-2.0"/);
});

test("requirement minimums must agree between badges and the Requirements table", () => {
  const badges = new Map([
    ["jq", "https://img.shields.io/badge/jq-%E2%89%A51.6-555555"],
    ["Git", "https://img.shields.io/badge/Git-%E2%89%A52.18-F05032?logo=git"],
    ["Network", "https://img.shields.io/badge/network-none-lightgrey"],
  ]);
  const minimums = badgeMinimums(badges);
  assert.deepEqual(
    [...minimums],
    [
      ["jq", "1.6"],
      ["Git", "2.18"],
    ],
  );
  /** @param {string} jq */
  const table = (jq) =>
    sectionBodies(
      `## 📋 Requirements\n\n| Requirement | Minimum | Check |\n| --- | --- | --- |\n| \`jq\` | ${jq} | x |\n| Git | 2.18 | x |`,
    );
  assert.deepEqual(checkRequirementMinimums(minimums, table("1.6")), []);
  assert.match(
    checkRequirementMinimums(minimums, table("1.5")).join("\n"),
    /jq "1.5", but its badge says ≥ 1.6/,
  );
});

test("a network-none plugin must not ship scripts that call network tools", () => {
  const dir = mkdtempSync(join(tmpdir(), "network-claim-"));
  mkdirSync(join(dir, "scripts"));
  const badges = new Map([["Network", "https://img.shields.io/badge/network-none-lightgrey"]]);
  writeFileSync(
    join(dir, "scripts", "ok.sh"),
    "#!/usr/bin/env bash\njq -nc '{}'\n# curl is mentioned in a comment\n",
  );
  writeFileSync(join(dir, "README.md"), "curl https://example.com\n");
  assert.deepEqual(checkNetworkClaim(dir, badges), []);
  writeFileSync(
    join(dir, "scripts", "bad.sh"),
    "#!/usr/bin/env bash\ncurl -fsS https://x.example\n",
  );
  assert.match(
    checkNetworkClaim(dir, badges).join("\n"),
    /scripts\/bad\.sh:2 calls a network tool/,
  );
  // A badge row with no Network badge is the misleading case: the reader sees
  // nothing about the network and assumes there is none.
  assert.deepEqual(checkNetworkClaim(dir, new Map()), [
    "the badge row has no Network badge; every plugin states its network posture (network-none, network-optional or network-required)",
  ]);
  // A plugin that declares the network carries no obligation about its scripts.
  const declared = new Map([
    ["Network", "https://img.shields.io/badge/network-required-lightgrey"],
  ]);
  assert.deepEqual(checkNetworkClaim(dir, declared), []);
  rmSync(dir, { recursive: true });
});

test("every CHANGELOG heading has a link definition", () => {
  const base = "## [Unreleased]\n\n## [0.1.1] - 2026-09-18\n\n## [0.1.0] - 2026-09-18\n";
  const links =
    "[Unreleased]: https://github.com/o/r/compare/p--v0.1.1...HEAD\n[0.1.1]: https://github.com/o/r/compare/p--v0.1.0...p--v0.1.1\n";
  assert.deepEqual(
    checkChangelogLinks(`${base}\n${links}[0.1.0]: https://github.com/o/r/tree/p--v0.1.0\n`),
    [],
  );
  assert.match(
    checkChangelogLinks(`${base}\n${links}`).join("\n"),
    /no link definition for \[0\.1\.0\]/,
  );
});
