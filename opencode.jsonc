{
  "$schema": "https://opencode.ai/config.json",
  // Second Brain для OpenCode: MCP-серверы из .mcp.json (формат V2: mcp.servers).
  // Генерируется: python brain.py sync (канон: .mcp.json + agents/rules/CORE_RULES.md).
  // Секреты — только через переменные окружения: {env:VAR}. Не править руками.
  "mcp": {
    "servers": {
      "brain": {
        "type": "local",
        "command": ["python", "./agents/mcp/brain_mcp.py"]
      },
      "filesystem": {
        "type": "local",
        "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "."]
      },
      "github": {
        "type": "local",
        "command": ["npx", "-y", "@modelcontextprotocol/server-github"],
        "environment": {
          "GITHUB_PERSONAL_ACCESS_TOKEN": "{env:GITHUB_TOKEN}"
        }
      },
      "postgres": {
        "type": "local",
        "command": ["npx", "-y", "@modelcontextprotocol/server-postgres", "{env:POSTGRES_CONNECTION_STRING}"]
      },
      "context7": {
        "type": "local",
        "command": ["npx", "-y", "@upstash/context7-mcp"]
      },
      "playwright": {
        "type": "local",
        "command": ["npx", "-y", "@playwright/mcp@latest"]
      },
      "sentry": {
        "type": "local",
        "command": ["npx", "-y", "@sentry/mcp-server@latest"],
        "environment": {
          "SENTRY_AUTH_TOKEN": "{env:SENTRY_AUTH_TOKEN}",
          "SENTRY_ORG": "{env:SENTRY_ORG}",
          "SENTRY_PROJECT": "{env:SENTRY_PROJECT}"
        }
      }
    }
  },
  "permissions": [
    { "action": "edit", "resource": "*.env", "effect": "deny" },
    { "action": "edit", "resource": "*.env.*", "effect": "deny" },
    { "action": "edit", "resource": "*.env.example", "effect": "allow" },
    { "action": "edit", "resource": "*.pem", "effect": "deny" },
    { "action": "edit", "resource": "*.key", "effect": "deny" }
  ]
}
