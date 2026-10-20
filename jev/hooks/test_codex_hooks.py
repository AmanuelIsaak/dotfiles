"""Focused compatibility checks for Jev's Claude and Codex hooks."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))
import action_gate
import done_check
import transcript


class CodexHooksTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "rollout.jsonl")
        events = [
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Remove the old files"}]}},
            {"type": "response_item", "payload": {"type": "custom_tool_call", "name": "Bash", "input": "{\"command\":\"pwd\"}"}},
            {"type": "response_item", "payload": {"type": "custom_tool_call_output", "output": "workspace"}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "All done"}]}},
        ]
        with open(self.path, "w") as f:
            for event in events:
                f.write(json.dumps(event) + "\n")
        pending = patch.object(action_gate, "PENDING", os.path.join(self.tmp.name, "pending.json"))
        pending.start()
        self.addCleanup(pending.stop)

    def reply(self, text):
        event = {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": text}]}}
        with open(self.path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def run_hook(self, module, event, answers):
        out = io.StringIO()
        with patch.object(sys, "stdin", io.StringIO(json.dumps(event))), \
             contextlib.redirect_stdout(out), \
             patch.object(module.jev, "api_key", return_value="test"), \
             patch.object(module.jev, "ask", return_value=answers):
            module.main()
        return json.loads(out.getvalue()) if out.getvalue() else None

    def test_codex_transcript(self):
        self.assertEqual(transcript.last_prompt(self.path), "Remove the old files")
        convo = transcript.since_last_prompt(self.path)
        self.assertIn("[tool Bash:", convo)
        self.assertIn("ASSISTANT: All done", convo)

    def test_codex_gate_denies_ask_case(self):
        answers = {k: {"p": 0.9 if k == "destructive" else 0.0} for k in action_gate.CHECKS}
        result = self.run_hook(action_gate, {
            "hook_event_name": "PreToolUse", "turn_id": "t1", "tool_name": "Bash",
            "tool_input": {"command": "rm old-file"}, "transcript_path": self.path,
        }, answers)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_claude_gate_keeps_ask_case(self):
        answers = {k: {"p": 0.9 if k == "destructive" else 0.0} for k in action_gate.CHECKS}
        result = self.run_hook(action_gate, {
            "hook_event_name": "PreToolUse", "tool_name": "Bash",
            "tool_input": {"command": "rm old-file"}, "transcript_path": self.path,
        }, answers)
        self.assertEqual(result["hookSpecificOutput"]["permissionDecision"], "ask")

    def gate(self, answers):
        return self.run_hook(action_gate, {
            "hook_event_name": "PreToolUse", "turn_id": "t1", "tool_name": "Bash",
            "tool_input": {"command": "rm old-file"}, "transcript_path": self.path,
        }, answers)

    def test_codex_retry_runs_once_after_approval(self):
        destructive = {k: {"p": 0.9 if k == "destructive" else 0.0} for k in action_gate.CHECKS}
        self.gate(destructive)
        self.reply("yes, delete it")
        self.assertIsNone(self.gate({"approved": {"p": 0.95}}))
        self.assertEqual(self.gate(destructive)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_codex_retry_without_reply_is_denied(self):
        destructive = {k: {"p": 0.9 if k == "destructive" else 0.0} for k in action_gate.CHECKS}
        self.gate(destructive)
        self.assertEqual(self.gate(destructive)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_codex_retry_after_decline_is_denied(self):
        destructive = {k: {"p": 0.9 if k == "destructive" else 0.0} for k in action_gate.CHECKS}
        self.gate(destructive)
        self.reply("no, keep it")
        with patch.object(action_gate.jev, "api_key", return_value="test"), \
             patch.object(action_gate.jev, "ask", side_effect=[{"approved": {"p": 0.05}}, destructive]), \
             patch.object(sys, "stdin", io.StringIO(json.dumps({
                 "hook_event_name": "PreToolUse", "turn_id": "t1", "tool_name": "Bash",
                 "tool_input": {"command": "rm old-file"}, "transcript_path": self.path}))), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            action_gate.main()
        self.assertEqual(json.loads(out.getvalue())["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_codex_deny_level_is_not_remembered(self):
        exfil = {k: {"p": 0.95 if k == "exfiltration" else 0.0} for k in action_gate.CHECKS}
        self.gate(exfil)
        self.assertEqual(action_gate.load_pending(), {})

    def test_codex_stop_continues_false_completion(self):
        result = self.run_hook(done_check, {
            "hook_event_name": "Stop", "turn_id": "t1", "transcript_path": self.path,
            "last_assistant_message": "All done", "stop_hook_active": False,
        }, {"waiting": {"p": 0.0}, "premature": {"p": 0.95}})
        self.assertEqual(result["decision"], "block")

    def test_stop_does_not_repeat(self):
        result = self.run_hook(done_check, {
            "hook_event_name": "Stop", "turn_id": "t1", "transcript_path": self.path,
            "stop_hook_active": True,
        }, {})
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
