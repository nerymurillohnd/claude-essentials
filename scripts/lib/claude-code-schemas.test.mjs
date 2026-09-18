// Upstream-faithful Claude Code schemas (schemas/claude-code/): each must compile,
// accept the complete examples from the official docs, and reject known mistakes.
// Fixtures are the docs' own examples (verified 2026-09-18), so a failing case
// here means either a schema bug or upstream drift worth a docs-drift audit.
// biome-ignore-all lint/suspicious/noTemplateCurlyInString: fixtures hold Claude Code's literal ${...} placeholders, not JS templates.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import Ajv from "ajv";
import addFormats from "ajv-formats";
import { readJson, rootDir } from "./plugins.mjs";

const schemaDir = join(rootDir, "schemas", "claude-code");
const base = "https://github.com/nerymurillohnd/claude-essentials/schemas/claude-code/";

function makeAjv() {
  const ajv = new Ajv({ allErrors: true, strict: false });
  addFormats(ajv);
  for (const file of readdirSync(schemaDir).filter((f) => f.endsWith(".schema.json"))) {
    ajv.addSchema(JSON.parse(readFileSync(join(schemaDir, file), "utf8")));
  }
  return ajv;
}

const ajv = makeAjv();
const validator = (name) => ajv.getSchema(`${base}${name}.schema.json`);

function assertValid(name, data) {
  const validate = validator(name);
  assert.ok(validate(data), JSON.stringify(validate.errors, null, 2));
}

function assertInvalid(name, data) {
  assert.equal(validator(name)(data), false);
}

test("every schema in schemas/claude-code compiles and resolves cross-file refs", () => {
  for (const name of ["plugin-manifest", "marketplace", "hooks", "mcp", "lsp", "monitors"]) {
    assert.equal(typeof validator(name), "function", `${name} did not compile`);
  }
});

test("plugin-manifest accepts the docs' complete example", () => {
  assertValid("plugin-manifest", {
    $schema: "https://json.schemastore.org/claude-code-plugin-manifest.json",
    name: "enterprise-deployment",
    displayName: "Enterprise Deployment Tools",
    version: "2.1.0",
    description: "Comprehensive deployment automation and monitoring",
    author: {
      name: "DevOps Team",
      email: "devops@company.com",
      url: "https://github.com/company/deployment-plugin",
    },
    homepage: "https://docs.company.com/deployment-plugin",
    repository: "https://github.com/company/deployment-plugin",
    license: "MIT",
    keywords: ["deployment", "ci-cd", "monitoring"],
    defaultEnabled: false,
    skills: ["./skills/", "./custom-skills/"],
    commands: ["./commands/deploy.md"],
    agents: ["./agents/reviewer.md"],
    hooks: "./hooks/hooks.json",
    mcpServers: "./config/mcp-servers.json",
    lspServers: "./.lsp.json",
    outputStyles: "./styles/",
    experimental: { monitors: "./monitors.json", themes: "./themes/", evals: "quality/evals" },
    userConfig: {
      api_token: {
        type: "string",
        title: "API Token",
        description: "Deployment API authentication token",
        sensitive: true,
        required: true,
      },
      environment: {
        type: "string",
        title: "Target Environment",
        description: "Deployment target",
        default: "staging",
        options: ["dev", "staging", "prod"],
      },
      max_concurrent: {
        type: "number",
        title: "Max Concurrent Deployments",
        description: "Maximum parallel deployments",
        min: 1,
        max: 10,
        default: 3,
      },
    },
    dependencies: ["secrets-vault", { name: "logging-plugin", version: "~2.0.0" }],
    channels: [
      {
        server: "slack-notifications",
        userConfig: {
          webhook_url: {
            type: "string",
            title: "Slack Webhook",
            description: "Slack incoming webhook URL",
            sensitive: true,
          },
        },
      },
    ],
    settings: { agent: "enterprise-deployment:reviewer" },
    metadata: { catalogId: "cat-enterprise-001", tier: "pro" },
  });
});

test("plugin-manifest accepts inline hooks, MCP, and LSP servers", () => {
  assertValid("plugin-manifest", {
    name: "inline-demo",
    hooks: {
      hooks: {
        PostToolUse: [{ matcher: "Write|Edit", hooks: [{ type: "command", command: "./fmt.sh" }] }],
      },
    },
    mcpServers: { db: { command: "${CLAUDE_PLUGIN_ROOT}/servers/db", args: ["--ro"] } },
    lspServers: { go: { command: "gopls", extensionToLanguage: { ".go": "go" } } },
  });
});

test("plugin-manifest rejects unknown fields, non-kebab names, and paths without ./", () => {
  assertInvalid("plugin-manifest", { name: "demo", kind: "bundle" });
  assertInvalid("plugin-manifest", { name: "Demo Plugin" });
  assertInvalid("plugin-manifest", { name: "demo", skills: "skills/" });
  assertInvalid("plugin-manifest", { name: "demo", experimental: { evals: "../evals" } });
  assertInvalid("plugin-manifest", { name: "demo", experimental: { evals: "/abs/evals" } });
  assertInvalid("plugin-manifest", {
    name: "demo",
    userConfig: { token: { type: "secret", title: "T", description: "d" } },
  });
});

test("marketplace accepts the docs' complete example and this repo's catalog", () => {
  assertValid("marketplace", {
    $schema: "https://code.claude.com/schemas/marketplace.json",
    name: "acme-enterprise",
    owner: { name: "Acme DevTools Team", email: "devtools@acme.com", url: "https://acme.com" },
    description: "Enterprise tools for Acme Corp",
    version: "1.0.0",
    metadata: { pluginRoot: "./plugins" },
    renames: { "old-formatter": "code-formatter", "deprecated-linter": null },
    allowCrossMarketplaceDependenciesOn: ["anthropics/claude-plugins-official"],
    plugins: [
      {
        name: "code-formatter",
        displayName: "Code Formatter",
        description: "Automatic code formatting",
        source: "./plugins/code-formatter",
        version: "2.1.0",
        author: { name: "Acme DevTools", email: "devtools@acme.com" },
        homepage: "https://docs.acme.com/code-formatter",
        repository: "https://github.com/acme-corp/code-formatter",
        license: "MIT",
        keywords: ["formatting", "style"],
        category: "productivity",
        commands: ["./commands"],
        strict: true,
        defaultEnabled: true,
      },
      {
        name: "security-scanner",
        description: "Security scanning tool",
        source: {
          source: "github",
          repo: "acme-corp/security-scanner",
          ref: "stable",
          sha: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        },
        version: "1.5.0",
        tags: ["security", "scanning"],
        agents: ["./agents/scanner.md"],
      },
      { name: "formatter", source: "formatter" },
      {
        name: "subdir",
        source: {
          source: "git-subdir",
          url: "https://github.com/acme-corp/monorepo.git",
          path: "tools/claude-plugin",
          sha: "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0",
        },
      },
      { name: "npm-plugin", source: { source: "npm", package: "@acme/claude-plugin" } },
      {
        name: "zip-plugin",
        source: {
          source: "archive",
          url: "https://artifacts.example.com/p.zip",
          sha256: "6bfa50e3d2e00c052b46abe51fff89346ac803e45771f76dcf6df1ab74cca5e1",
        },
      },
      {
        name: "cmd-plugin",
        source: { source: "command", command: "my-tool claude-plugin-path", mode: "copy" },
      },
    ],
  });
  assertValid("marketplace", readJson(join(rootDir, ".claude-plugin", "marketplace.json")));
});

test("marketplace rejects reserved names, short SHAs, and http archives", () => {
  const owner = { name: "x" };
  assertInvalid("marketplace", { name: "claude-plugins-official", owner, plugins: [] });
  assertInvalid("marketplace", { name: "gh", owner, plugins: [] });
  assertInvalid("marketplace", {
    name: "ok",
    owner,
    plugins: [{ name: "p", source: { source: "github", repo: "a/b", sha: "a1b2c3d" } }],
  });
  assertInvalid("marketplace", {
    name: "ok",
    owner,
    plugins: [{ name: "p", source: { source: "archive", url: "http://x/p.zip" } }],
  });
});

test("hooks accepts every handler type from the docs' complete example", () => {
  assertValid("hooks", {
    description: "Security and formatting hooks",
    hooks: {
      PreToolUse: [
        {
          matcher: "Bash",
          hooks: [
            {
              type: "command",
              if: "Bash(rm *)",
              command: "${CLAUDE_PROJECT_DIR}/.claude/hooks/block-rm.sh",
              args: [],
              timeout: 30,
            },
          ],
        },
        {
          matcher: "mcp__.*",
          hooks: [
            {
              type: "http",
              url: "http://localhost:8080/hooks/pre-tool",
              headers: { Authorization: "Bearer $MY_TOKEN" },
              allowedEnvVars: ["MY_TOKEN"],
            },
          ],
        },
      ],
      PostToolUse: [
        {
          matcher: "Edit|Write",
          hooks: [
            { type: "command", command: "prettier", args: ["${tool_input.file_path}", "--write"] },
            {
              type: "mcp_tool",
              server: "my_server",
              tool: "security_scan",
              input: { file_path: "${tool_input.file_path}" },
            },
            {
              type: "prompt",
              prompt: "Review this code change: $ARGUMENTS",
              model: "claude-opus-5",
            },
          ],
        },
      ],
      Stop: [{ hooks: [{ type: "agent", prompt: "Verify tests pass: $ARGUMENTS" }] }],
      SessionStart: [
        {
          matcher: "resume",
          hooks: [{ type: "command", command: "echo resumed", async: true }],
        },
      ],
    },
  });
});

test("hooks rejects unknown events, handler types, and a missing command", () => {
  assertInvalid("hooks", { hooks: { PreToolUsage: [] } });
  assertInvalid("hooks", { hooks: { Stop: [{ hooks: [{ type: "script", command: "x" }] }] } });
  assertInvalid("hooks", { hooks: { Stop: [{ hooks: [{ type: "command" }] }] } });
});

test("mcp accepts every transport from the docs and rejects `transport` as the key", () => {
  assertValid("mcp", {
    mcpServers: {
      database: {
        type: "stdio",
        command: "npx",
        args: ["-y", "@bytebase/dbhub"],
        env: { DSN: "${DB_CONNECTION_STRING:-postgresql://localhost}" },
        timeout: 30000,
      },
      playwright: { command: "npx", args: ["-y", "@playwright/mcp@latest"] },
      github: {
        type: "http",
        url: "https://api.githubcopilot.com/mcp/",
        headers: { Authorization: "Bearer ${GITHUB_PAT}" },
      },
      internal: {
        type: "sse",
        url: "https://mcp.internal.example.com",
        headersHelper: "/opt/bin/get-mcp-auth-headers.sh",
        oauth: { clientId: "my-client-id", callbackPort: 8080, scopes: "read write" },
      },
      socket: { type: "ws", url: "wss://mcp.example.com/socket", alwaysLoad: false },
    },
  });
  assertInvalid("mcp", { mcpServers: { x: { transport: "http", url: "https://x" } } });
  assertInvalid("mcp", { mcpServers: { x: { type: "http" } } });
});

test("lsp accepts the docs' full server example and requires extensionToLanguage", () => {
  assertValid("lsp", {
    go: {
      command: "gopls",
      args: ["serve"],
      extensionToLanguage: { ".go": "go" },
      transport: "stdio",
      env: { GO_ENV: "production" },
      initializationOptions: { hints: { assignVariableTypes: true } },
      settings: { gopls: { "build.directoryFilters": ["-vendor"] } },
      workspaceFolder: "${CLAUDE_PROJECT_DIR}",
      startupTimeout: 10000,
      shutdownTimeout: 5000,
      restartOnCrash: true,
      maxRestarts: 5,
      diagnostics: true,
    },
  });
  assertInvalid("lsp", { go: { command: "gopls" } });
  assertInvalid("lsp", { go: { command: "gopls", extensionToLanguage: { go: "go" } } });
});

test("monitors accepts the docs' example and rejects an unknown trigger", () => {
  assertValid("monitors", [
    {
      name: "deploy-status",
      command: '"${CLAUDE_PLUGIN_ROOT}"/scripts/poll-deploy.sh',
      description: "Deployment status changes",
      when: "always",
    },
    {
      name: "error-log",
      command: "tail -F ./logs/error.log",
      description: "Application error log",
      when: "on-skill-invoke:debug",
    },
  ]);
  assertInvalid("monitors", [{ name: "x", command: "y", description: "z", when: "sometimes" }]);
  assertInvalid("monitors", [{ name: "x", command: "y" }]);
});
