#!/usr/bin/env python3
"""Batch runner for multi-turn causal-consultant tests using send_one.py.

Writes all turn prompt files and runs each turn sequentially, passing
--continue for turns 2+. Handles ANTHROPIC_API_KEY fallback for
background/subprocess contexts where the env var isn't inherited.

Reports per-turn: Turn | Dur | Tokens | Shape (PASS/FAIL).
Final summary: Turns, Shape, Output, YAML, Tokens.

Usage:
    cd ~/test-center/v4.5.0/session-<name>
    export ANTHROPIC_BASE_URL=<your-proxy-url>
    python3 run_all_turns.py

The TURNS dict should be customized per session.
"""

import subprocess
import os
import sys
import time
import json
import glob

SEND_ONE = os.path.expanduser("~/.hermes/skills/interactive-test-cc/scripts/send_one.py")
SHAPE_MARKERS = ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]']

# Replace with your test prompts
TURNS = {
    1: "I'm studying factors that influence college graduation rates in the US. I have data on 777 colleges with variables like admissions stats, selectivity measures, institutional resources, and student spending. I want to understand what drives better graduation outcomes — is it selectivity? resources? teaching quality? Let me know what you think and how you'd approach this.",
    # ... add turns 2-13
}


def check_shape(result_text):
    hits = [s for s in SHAPE_MARKERS if s in result_text]
    return len(hits) >= 2, hits


def main():
    session_dir = os.getcwd()
    env = os.environ.copy()
    if "ANTHROPIC_BASE_URL" not in env:
        print("⚠️  ANTHROPIC_BASE_URL not set — set it and retry")
        sys.exit(1)
    if "ANTHROPIC_API_KEY" not in env:
        env["ANTHROPIC_API_KEY"] = "dummy"

    results = {}  # turn_num -> {dur, tok, shape, hits}

    for turn_num in sorted(TURNS.keys()):
        msg = TURNS[turn_num]
        msg_file = os.path.join(session_dir, f"turn-{turn_num}.md")
        out_file = os.path.join(session_dir, f"turn-{turn_num}.json")

        with open(msg_file, "w") as f:
            f.write(msg)

        cmd = [
            sys.executable, SEND_ONE,
            "--msg-file", msg_file,
            "--out-file", out_file,
            "--workdir", session_dir,
        ]
        if turn_num > 1:
            cmd.append("--continue")

        print(f"\n{'='*60}")
        print(f"TURN {turn_num}/{len(TURNS)} — {len(msg)} chars")
        print(f"{'='*60}")

        start = time.time()
        result = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
        elapsed = time.time() - start

        print(result.stderr.strip())

        if result.returncode != 0:
            print(f"❌ Exit {result.returncode}")
            results[turn_num] = {"dur": elapsed, "tok": 0, "shape": "ERROR", "hits": []}
            continue

        # Read and parse output
        try:
            with open(out_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("❌ Could not parse output JSON")
            results[turn_num] = {"dur": elapsed, "tok": 0, "shape": "ERROR", "hits": []}
            continue

        usage = data.get("usage", {})
        tok = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        result_text = data.get("result", "")
        shape_ok, hits = check_shape(result_text)
        shape_str = "PASS" if shape_ok else "FAIL"

        results[turn_num] = {"dur": elapsed, "tok": tok, "shape": shape_str, "hits": hits}
        print(f"Turn {turn_num:2d}: {elapsed:.0f}s | {tok/1000:.0f}K tok | Shape: {shape_str}")

    # Final summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print(f"{'='*60}")

    # Turns table
    print(f"\n{'Turn':>4} | {'Dur':>5} | {'Tokens':>6} | Shape")
    print(f"{'-'*4}-+-{'-'*5}-+-{'-'*6}-+-{'-'*5}")
    total_tok = 0
    total_in = 0
    total_out = 0
    pass_count = 0
    fail_turns = []

    for tn in sorted(results.keys()):
        r = results[tn]
        total_tok += r["tok"]
        print(f"{tn:4d} | {r['dur']:.0f}s | {r['tok']/1000:5.0f}K | {r['shape']}")
        if r["shape"] == "PASS":
            pass_count += 1
        else:
            fail_turns.append(tn)

    # Count tokens from all JSON files
    for f in sorted(glob.glob(os.path.join(session_dir, "turn-*.json"))):
        with open(f) as fh:
            d = json.load(fh)
        u = d.get("usage", {})
        total_in += u.get("input_tokens", 0)
        total_out += u.get("output_tokens", 0)

    print(f"\nShape:  {pass_count}/{len(TURNS)} PASS" +
          (f", {len(fail_turns)}/{len(TURNS)} FAIL (T{','.join(str(t) for t in fail_turns)})" if fail_turns else ""))
    print(f"Tokens: {total_in/1000:.0f}K in + {total_out/1000:.0f}K out = {(total_in+total_out)/1000:.0f}K total")

    # Check YAML
    yaml_path = os.path.join(session_dir, "project_state.yaml")
    if os.path.exists(yaml_path):
        yaml_size = os.path.getsize(yaml_path)
        print(f"YAML:   ✅ {yaml_size}B")
    else:
        print("YAML:   ❌ not found")

    # Check output
    output_dir = os.path.join(session_dir, "output")
    if os.path.exists(output_dir):
        files = []
        for root, _, filenames in os.walk(output_dir):
            for fn in filenames:
                files.append(os.path.relpath(os.path.join(root, fn), output_dir))
        print(f"Output: {len(files)} files in output/ — {', '.join(files[:8])}{'...' if len(files) > 8 else ''}")
    else:
        # Loose artifacts
        loose = []
        for fn in sorted(os.listdir(session_dir)):
            if fn.endswith(('.html', '.pptx', '.png', '.py')) and fn != 'run_all_turns.py':
                fp = os.path.join(session_dir, fn)
                loose.append(f"{fn} ({os.path.getsize(fp)}B)")
        if loose:
            print(f"Output: {', '.join(loose[:5])}")
        else:
            print("Output: none found")

    print(f"\n✅ All {len(TURNS)} turns complete")


if __name__ == "__main__":
    main()
