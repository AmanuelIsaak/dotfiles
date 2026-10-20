// Jev hooks for OpenCode: runs the same Python hooks Claude Code and Codex use.
// skill_picker -> hint appended to the system prompt; rule_enforcer -> blocks edits.
// Fails open: any error or timeout lets the prompt/edit through.
import type { Plugin } from "@opencode-ai/plugin"
import { spawn } from "node:child_process"
import { homedir } from "node:os"

const HOOKS = `${homedir()}/.agents/jev/hooks`

function runHook(script: string, event: object, timeoutMs: number): Promise<any> {
  return new Promise((resolve) => {
    const p = spawn("python3", [`${HOOKS}/${script}`], { stdio: ["pipe", "pipe", "ignore"] })
    let out = ""
    const timer = setTimeout(() => { p.kill(); resolve(null) }, timeoutMs)
    p.stdout.on("data", (d) => (out += d))
    p.on("error", () => { clearTimeout(timer); resolve(null) })
    p.on("close", () => {
      clearTimeout(timer)
      try { resolve(out.trim() ? JSON.parse(out) : null) } catch { resolve(null) }
    })
    p.stdin.end(JSON.stringify(event))
  })
}

// OpenCode tool args -> the Claude-style event rule_enforcer expects.
function editEvent(tool: string, a: any) {
  if (tool === "write") return { tool_name: "Write", tool_input: { file_path: a.filePath, content: a.content } }
  if (tool === "edit") return { tool_name: "Edit", tool_input: { file_path: a.filePath, old_string: a.oldString, new_string: a.newString } }
  if (tool === "multiedit") return { tool_name: "MultiEdit", tool_input: { file_path: a.filePath,
    edits: (a.edits ?? []).map((e: any) => ({ old_string: e.oldString, new_string: e.newString })) } }
  if (tool === "patch" || tool === "apply_patch") return { tool_name: "apply_patch", tool_input: a }
  return null
}

export const JevPlugin: Plugin = async ({ directory }) => {
  const hints = new Map<string, string>()
  return {
    "chat.message": async (input, output) => {
      hints.delete(input.sessionID)
      const prompt = output.parts.filter((p: any) => p.type === "text" && !p.synthetic).map((p: any) => p.text).join("\n")
      const res = await runHook("skill_picker.py", { hook_event_name: "UserPromptSubmit", prompt, cwd: directory }, 8000)
      const hint = res?.hookSpecificOutput?.additionalContext
      if (hint) hints.set(input.sessionID, hint)
    },
    "experimental.chat.system.transform": async (input, output) => {
      const hint = input.sessionID && hints.get(input.sessionID)
      if (hint) output.system.push(hint)
    },
    "tool.execute.before": async (input, output) => {
      const ev = editEvent(input.tool, output.args)
      if (!ev) return
      const res = await runHook("rule_enforcer.py", { hook_event_name: "PreToolUse", cwd: directory, ...ev }, 15000)
      const h = res?.hookSpecificOutput
      if (h?.permissionDecision === "deny") throw new Error(h.permissionDecisionReason)
    },
  }
}
