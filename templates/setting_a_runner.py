#!/usr/bin/env python3
"""Setting A (13-turn) runner for causal-consultant testing.

Copy this to your session directory, customize TURNS for your dataset/domain,
and run with ANTHROPIC_BASE_URL set.

Usage:
    cd ~/test-center/v5.0.0/session-<name>
    cp ~/.hermes/skills/interactive-test-cc/templates/setting_a_runner.py run_all_turns.py
    # Edit TURNS prompts for your domain/dataset
    cp ~/test-center/causal-data/<dataset>/<file>.csv data.csv
    export ANTHROPIC_BASE_URL=http://127.0.0.1:8777
    python3 run_all_turns.py
"""

import subprocess
import os
import sys
import time
import json
import glob

SEND_ONE = os.path.expanduser("~/.hermes/skills/interactive-test-cc/scripts/send_one.py")
SHAPE_MARKERS = ['[> Framing]', '[+ Consultant Options]', '[? Next Steps]']

# --- CUSTOMIZE BELOW for your dataset/domain ---
TURNS = {
    1: "Use the causal-consultant skill. I'm studying <DOMAIN>. I have data on <N> observations with variables like <LIST KEY VARS>. I want to understand <RESEARCH QUESTION>. Let me know what you think and how you'd approach this.",

    2: "<DEEPER DOMAIN QUESTION — probe a specific aspect of the research question>",

    3: "Here is the data — data.csv, take a look. <OUTCOME VAR> is the outcome, and <KEY PREDICTOR> is the main variable of interest. I'd like you to explore the data and tell me what patterns stand out.",

    4: "Interesting findings. <FOLLOW UP ON DATA EXPLORATION — dig deeper into a specific relationship>",

    5: "Let's get more causal. If I want to estimate the effect of <TREATMENT VAR> on <OUTCOME VAR>, what would be a defensible causal identification strategy given this observational data? What assumptions would we need and can we defend them?",

    6: "<PROBE EDGE CASE OR ALTERNATIVE ANGLE — e.g., heterogeneity, subgroup, alternative mechanism>",

    7: "Great discussion. I'd like you to run a formal causal analysis now. Estimate the effect of <TREATMENT VAR> on <OUTCOME VAR>, controlling for the key confounders you've identified. Use a method you think is most appropriate and defensible given what we've discussed.",

    8: "Yes, that analysis plan looks solid. Please go ahead and execute it. I'm comfortable with the method choice and the confounder selection you've laid out.",

    9: "That's a good analysis. Now I'd like you to do a second analysis — this time looking at <HETEROGENEITY DIMENSION>. Is the effect of <TREATMENT> different across <SUBGROUPS>? Run this as a separate analysis.",

    10: "The <HETEROGENEITY> analysis plan makes sense. Please go ahead and run it.",

    11: "We have two good analyses now. Can you write up a full report? I'd like it in HTML format with clear sections: background, data description, methods, results from both analyses, and conclusions. Include the key figures and tables.",

    12: "The report outline looks comprehensive. Please go ahead and generate the full HTML report. I want the final version with all figures embedded.",

    13: "One last thing — can you create a 3-slide PPT summary of the key findings? Slide 1: problem and data, Slide 2: main analysis results, Slide 3: <HETEROGENEITY/SUPPLEMENTARY> findings and conclusions.",
}
# --- END CUSTOMIZE ---


def check_shape(result_text):
    hits = [s for s in SHAPE_MARKERS if s in result_text]
    return len(hits) >= 2, hits


def main():
    session_dir = os.getcwd()
    env = os.environ.copy()
    if "ANTHROPIC_BASE_URL" not in env:
        print("ANTHROPIC_BASE_URL not set — set it and retry")
        sys.exit(1)
    if "ANTHROPIC_API_KEY" not in env:
        env["ANTHROPIC_API_KEY"] = "dummy"

    results = {}

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
            print(f"Exit {result.returncode}")
            results[turn_num] = {"dur": elapsed, "tok": 0, "shape": "ERROR", "hits": []}
            continue

        try:
            with open(out_file) as f:
                data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("Could not parse output JSON")
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

    print(f"\n{'Turn':>4} | {'Dur':>5} | {'Tokens':>6} | Shape")
    print(f"{'-'*4}-+-{'-'*5}-+-{'-'*6}-+-{'-'*5}")
    total_in = 0
    total_out = 0
    pass_count = 0
    fail_turns = []

    for tn in sorted(results.keys()):
        r = results[tn]
        print(f"{tn:4d} | {r['dur']:.0f}s | {r['tok']/1000:5.0f}K | {r['shape']}")
        if r["shape"] == "PASS":
            pass_count += 1
        else:
            fail_turns.append(tn)

    for f in sorted(glob.glob(os.path.join(session_dir, "turn-*.json"))):
        with open(f) as fh:
            d = json.load(fh)
        u = d.get("usage", {})
        total_in += u.get("input_tokens", 0)
        total_out += u.get("output_tokens", 0)

    print(f"\nShape:  {pass_count}/{len(TURNS)} PASS" +
          (f", {len(fail_turns)}/{len(TURNS)} FAIL (T{','.join(str(t) for t in fail_turns)})" if fail_turns else ""))
    print(f"Tokens: {total_in/1000:.0f}K in + {total_out/1000:.0f}K out = {(total_in+total_out)/1000:.0f}K total")

    yaml_path = os.path.join(session_dir, "project_state.yaml")
    if os.path.exists(yaml_path):
        print(f"YAML:   {os.path.getsize(yaml_path)}B")
    else:
        print("YAML:   not found")

    output_dir = os.path.join(session_dir, "output")
    if os.path.exists(output_dir):
        files = []
        for root, _, filenames in os.walk(output_dir):
            for fn in filenames:
                files.append(os.path.relpath(os.path.join(root, fn), output_dir))
        print(f"Output: {len(files)} files in output/ — {', '.join(files[:8])}{'...' if len(files) > 8 else ''}")
    else:
        print("Output: none found")

    print(f"\nAll {len(TURNS)} turns complete")


if __name__ == "__main__":
    main()
