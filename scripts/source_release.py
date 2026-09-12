"""Check source-specific public commitments against retained pre-release evidence.

These checks establish references, chronology and saved bytes. A reviewer still
judges whether the quoted rule and evaluation choices are actually adequate.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote


POLICY_EVALUATION_KIND = "saved-policy-evaluation-commitment-v1"
POLICY_EVALUATION_COMPONENTS = ("candidate_rule", "utility", "comparators", "evaluation_procedure")


def require(condition, message):
    if not condition:
        raise ValueError("source release prerequisite: " + message)


def policy_evaluation_prerequisite():
    return {"kind": POLICY_EVALUATION_KIND,
            "required_components": list(POLICY_EVALUATION_COMPONENTS)}


def validate_source_prerequisite(source):
    """Ordinary sources have no prerequisite; gated sources must be on request."""
    if "release_prerequisite" not in source:
        return
    prerequisite = source["release_prerequisite"]
    require(isinstance(prerequisite, dict)
            and set(prerequisite) == {"kind", "required_components"}, "invalid source metadata")
    require(prerequisite["kind"] == POLICY_EVALUATION_KIND, "unsupported prerequisite kind")
    require(prerequisite["required_components"] == list(POLICY_EVALUATION_COMPONENTS),
            "policy commitment needs candidate rule, utility, comparators and evaluation procedure")
    require(source.get("availability") == "on_request", "gated source cannot be initial")


def member(root, relative):
    require(isinstance(relative, str) and bool(relative) and "\\" not in relative
            and ":" not in relative and not relative.startswith("/")
            and all(part not in ("", ".", "..") for part in relative.split("/")),
            "invalid artifact path")
    root = Path(root).resolve()
    path = root.joinpath(*PurePosixPath(relative).parts)
    require(path.resolve().is_relative_to(root), "artifact path escapes evidence root")
    current = path
    while current != root:
        require(not current.is_symlink()
                and not (hasattr(current, "is_junction") and current.is_junction()),
                "artifact evidence cannot use links")
        current = current.parent
    return path


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def validate_release_receipts(attempt, state, sources, attachments, receipts=None):
    """Validate all requested gated sources before any attachment is staged.

``state['turns']`` is the completed turn count, before the pending dispatch is
created. ``sources`` maps source IDs to frozen case source entries. A receipt
contains source_id, public_turn, public_quote and a commitments map whose four
components each have artifact, sha256 and quote. One saved document may supply
all four components. No held-out file identity is required before its release.
    """
    attempt = Path(attempt)
    receipts = [] if receipts is None else receipts
    require(isinstance(receipts, list), "receipts must be a list")
    gated = {}
    for source_id in attachments:
        require(source_id in sources, "unknown attachment source")
        source = sources[source_id]
        validate_source_prerequisite(source)
        if "release_prerequisite" in source:
            gated[source_id] = source
    by_source = {}
    for receipt in receipts:
        require(isinstance(receipt, dict)
                and set(receipt) == {"source_id", "public_turn", "public_quote", "commitments"},
                "invalid receipt fields")
        source_id = receipt["source_id"]
        require(isinstance(source_id, str) and source_id in gated,
                "receipt must refer to a requested gated source")
        require(source_id not in by_source, "duplicate source receipt")
        by_source[source_id] = receipt
    require(set(by_source) == set(gated), "missing saved commitment receipt for "
            + ", ".join(sorted(set(gated) - set(by_source))))
    checked = []
    for source_id, receipt in by_source.items():
        turn = receipt["public_turn"]
        require(type(turn) is int and 0 < turn <= state["turns"],
                "commitment must identify an earlier completed public turn")
        event_ref = f"events/{turn:03d}"
        public_path = member(attempt, event_ref + "/public.json")
        files_path = member(attempt, event_ref + "/work-files.json")
        require(public_path.is_file() and files_path.is_file(),
                "earlier public turn and saved-file inventory must be retained")
        try:
            public = read(public_path)
            files = read(files_path)
        except (OSError, UnicodeError, ValueError) as exc:
            raise ValueError("source release prerequisite: unreadable retained turn evidence") from exc
        quote = receipt["public_quote"]
        require(isinstance(public, dict) and nonempty(public.get("assistant"))
                and nonempty(quote) and quote in public["assistant"],
                "public commitment quote is absent from the earlier assistant response")
        require(isinstance(files, dict), "invalid retained saved-file inventory")
        commitments = receipt["commitments"]
        require(isinstance(commitments, dict)
                and set(commitments) == set(POLICY_EVALUATION_COMPONENTS),
                "receipt needs all four saved commitment components")
        evidence_refs = [event_ref + "/public.json", event_ref + "/work-files.json"]
        for component in POLICY_EVALUATION_COMPONENTS:
            anchor = commitments[component]
            require(isinstance(anchor, dict) and set(anchor) == {"artifact", "sha256", "quote"},
                    "invalid " + component + " artifact reference")
            artifact, sha = anchor["artifact"], anchor["sha256"]
            snapshot_ref = event_ref + "/work-snapshot/" + artifact if isinstance(artifact, str) else ""
            saved = member(attempt, snapshot_ref)
            current = member(state["work"], artifact)
            require(re.search(r"(?<![\w.-])" + re.escape(artifact) + r"(?![\w/-]|\.[\w.-])",
                              unquote(quote).replace("\\", "/")) is not None,
                    "saved artifact must be identified in the public commitment quote")
            require(isinstance(sha, str) and re.fullmatch(r"[0-9a-f]{64}", sha) is not None,
                    "invalid saved artifact hash")
            require(saved.is_file() and files.get(artifact) == sha,
                    "artifact was not saved with that hash in the earlier turn")
            require(digest(saved) == sha, "retained saved artifact hash mismatch")
            require(current.is_file() and digest(current) == sha,
                    "saved commitment artifact changed or disappeared before release")
            try:
                content = saved.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                raise ValueError("source release prerequisite: commitment artifact must contain readable text") from exc
            require(nonempty(anchor["quote"]) and anchor["quote"] in content,
                    "saved artifact does not contain the " + component + " commitment quote")
            if snapshot_ref not in evidence_refs:
                evidence_refs.append(snapshot_ref)
        checked.append({"source_id": source_id, "kind": POLICY_EVALUATION_KIND,
                        "public_turn": turn, "public_sha256": digest(public_path),
                        "receipt": receipt, "evidence_refs": evidence_refs,
                        "scope": "Public references, chronology and saved bytes checked; semantic adequacy requires review."})
    return checked


def source_release_observations(attempt, frozen, index):
    """Compare retained source bytes with recorded releases, without inferring use.

    Renamed byte-identical copies are observable. Transformed data and access
    outside retained snapshots are not. Receipt contents still need review.
    """
    files = index.get("files", {})
    case = frozen.get("case_manifest", {})
    events = sorted({int(match[1]) for name in files
                     if (match := re.match(r"private/events/(\d+)/", name))})
    if not events:
        return []
    cache = {}

    def retained(relative, refs, gaps, *, document=False, expected=None):
        key = (relative, document, expected)
        ref = "private/" + relative
        if key not in cache:
            try:
                path = member(attempt, relative)
                if ref not in files:
                    raise ValueError("not indexed")
                if not path.is_file():
                    raise ValueError("not retained")
                sha = digest(path)
                if sha != files[ref] or (expected is not None and sha != expected):
                    raise ValueError("hash mismatch")
                value = read(path) if document else True
                if document and not isinstance(value, dict):
                    raise ValueError("expected a JSON object")
                cache[key] = (value, None)
            except (OSError, ValueError, UnicodeError) as exc:
                cache[key] = (None, {"evidence_ref": ref, "reason": str(exc)})
        value, gap = cache[key]
        if gap is not None:
            if gap not in gaps:
                gaps.append(gap)
        elif ref not in refs:
            refs.append(ref)
        return value

    observations = []
    for source in case.get("sources", []):
        if source.get("availability") != "on_request":
            continue
        source_id = source["id"]
        sha = case.get("files", {}).get(source["file"])
        refs, gaps, releases = [], [], []
        mentioned = claimed_source = False
        first = None
        for turn in range(1, events[-1] + 1):
            event = f"events/{turn:03d}"
            inventory = retained(event + "/work-files.json", refs, gaps, document=True)
            if first is None and isinstance(sha, str):
                for path, saved_sha in (inventory or {}).items():
                    if saved_sha == sha:
                        claimed_source = True
                        if retained(event + "/work-snapshot/" + path, refs, gaps, expected=sha):
                            first = {"first_observed_event": turn, "first_observed_path": path, "sha256": sha}
                            break
            released = retained(event + "/releases.json", refs, gaps, document=True)
            if released is not None and source_id in released:
                mentioned = True
                entry = released[source_id]
                if isinstance(sha, str) and isinstance(entry, dict) and entry.get("sha256") == sha and entry.get("path") == source["destination"]:
                    releases.append(turn)
                else:
                    gaps.append({"evidence_ref": "private/" + event + "/releases.json",
                                 "reason": "source release does not match the frozen destination and hash"})
            # Only pre-appearance release chronology can establish its acquisition.
            if first is not None:
                break
        if first is None and not releases and not mentioned and not claimed_source:
            continue
        retained("case/" + source["file"], refs, gaps, expected=sha)
        base = {"source_id": source_id, **(first or {}), "evidence_refs": refs}
        if first is not None and not releases:
            observations.append({**base, "status": "evidence_gap" if gaps else "acquisition_unverified",
                                 "evidence_gaps": gaps,
                                 "meaning": "Source bytes are retained without a verified release at or before their first observed event. This does not establish when they were accessed or used."})
            continue
        missing_receipts = []
        if "release_prerequisite" in source:
            for turn in releases:
                event = f"events/{turn:03d}"
                receipt = retained(event + "/source-release-check.json", refs, gaps, document=True)
                verified = receipt.get("verified_receipts") if receipt is not None else None
                if not isinstance(verified, list):
                    if receipt is not None:
                        gaps.append({"evidence_ref": "private/" + event + "/source-release-check.json",
                                     "reason": "verified_receipts is not a list"})
                elif not any(isinstance(item, dict) and item.get("source_id") == source_id for item in verified):
                    missing_receipts.append(turn)
        if gaps or missing_receipts:
            observations.append({**base, "status": "evidence_gap" if gaps else "receipt_unverified",
                                 "release_events": releases, "missing_receipt_events": missing_receipts,
                                 "evidence_gaps": gaps,
                                 "meaning": "The retained release trace needs review; a recorded release alone does not establish the gated commitment. No access or analysis timing is inferred."})
    return observations
