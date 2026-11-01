// Second Brain для OpenCode: Plan-First-гейт и защита секретов.
//
// Тот же единственный источник правды, что у Claude Code и Codex:
//   agents/tools/hooks/pre_tool_gate.py (deny -> JSON permissionDecision).
// Плагин вызывает его на permission.evaluate для edit/read/shell и при
// permissionDecision=deny ставит effect="deny". Любая ошибка — fail-open
// (как у Claude-хуков): не блокируем сессию из-за сбоя гейта.

import { spawnSync } from "node:child_process"
import { join } from "node:path"
import { Plugin } from "@opencode/plugin"

interface GateDecision {
  effect?: string
  message?: string
}

// PermissionEvaluation: action: "edit" | "read" | "shell" | ..., resources: readonly string[]
function buildPayload(action: string, resource: string): { tool_name: string; tool_input: Record<string, string> } | null {
  if (action === "edit") return { tool_name: "Edit", tool_input: { file_path: resource } }
  if (action === "read") return { tool_name: "Read", tool_input: { file_path: resource } }
  if (action === "shell") return { tool_name: "Bash", tool_input: { command: resource } }
  return null
}

function runGate(root: string, payload: Record<string, unknown>): GateDecision {
  let out: string
  try {
    const res = spawnSync("python", [join(root, "agents", "tools", "hooks", "pre_tool_gate.py")], {
      input: JSON.stringify({ ...payload, cwd: root }),
      encoding: "utf-8",
      timeout: 3000,
      windowsHide: true,
    })
    if (res.error || res.status !== 0 || !res.stdout) return {}
    out = res.stdout
  } catch {
    return {} // fail-open
  }
  try {
    const parsed = JSON.parse(out)
    const hook = parsed?.hookSpecificOutput
    if (hook?.permissionDecision === "deny") {
      return { effect: "deny", message: hook.permissionDecisionReason ?? "Заблокировано Second Brain" }
    }
  } catch {
    return {} // невалидный JSON — fail-open
  }
  return {}
}

export default Plugin.define({
  id: "second_brain",
  async setup(ctx) {
    const root = ctx.location.project.canonical ?? ctx.location.directory

    await ctx.permission.hook("evaluate", async (event) => {
      // Гейту интересны только действия над файлами и shell; остальное — мимо
      if (event.action !== "edit" && event.action !== "read" && event.action !== "shell") return

      const resources = event.resources?.length ? event.resources : [""]
      for (const resource of resources) {
        const payload = buildPayload(event.action, resource)
        if (!payload) continue
        const decision = runGate(root, payload as unknown as Record<string, unknown>)
        if (decision.effect === "deny") {
          event.effect = "deny"
          event.message = decision.message
          return
        }
      }
    })
  },
})
