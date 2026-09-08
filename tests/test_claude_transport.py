from pathlib import Path
import sys
import tempfile
import unittest
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from claude_transport import invoke

FAKE = Path(__file__).with_name("fake_claude.py")


class TransportTests(unittest.TestCase):
    def run_case(self, scenario, root, fresh=True, session=None, name="call"):
        config = {"claude_command": [sys.executable, str(FAKE), scenario], "max_agent_turns_per_call": 8}
        return invoke(config, root, session or str(uuid.uuid4()), fresh, "A literal $1,000; `quote`\nsecond line", 0.3 if scenario == "timeout" else 10, root / name)

    def test_real_subprocess_exact_resume_and_untruncated_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, session = Path(tmp), str(uuid.uuid4())
            first = self.run_case("ok", root, session=session)
            second = self.run_case("ok", root, fresh=False, session=session, name="second")
            self.assertIsNone(first["error"])
            self.assertIsNone(second["error"])
            self.assertEqual(first["session_id"], second["session_id"])
            self.assertIsNone(first["usage"])
            self.assertGreater((root / "call/stderr.txt").stat().st_size, 6000)
            self.assertEqual((root / "fake-message.txt").read_text(), "A literal $1,000; `quote`\nsecond line")
            self.assertIn("tool_use", (root / "call/stdout.txt").read_text())
            self.assertNotIn("--dangerously-skip-permissions", first["argv"])
            self.assertIn("--resume", second["argv"])

    def test_delivery_failures_are_retained(self):
        for scenario in ("timeout", "invalid", "empty", "changed", "missing_id", "empty_message", "provider_error", "duplicate", "nonzero"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                result = self.run_case(scenario, root)
                self.assertIsNotNone(result["error"])
                self.assertIsNone(result["message"])
                self.assertTrue((root / "call/process.json").exists())
                self.assertGreater((root / "call/stderr.txt").stat().st_size, 6000)

    def test_usage_is_raw_without_worker_or_cache_double_counting(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_case("usage", Path(tmp))
            self.assertEqual(result["usage"], {"input_tokens": 9, "cache_read_input_tokens": 12, "output_tokens": 7})
            self.assertEqual(result["total_cost_usd"], 0.1)


if __name__ == "__main__":
    unittest.main()
