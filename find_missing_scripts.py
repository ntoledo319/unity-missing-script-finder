#!/usr/bin/env python3
"""find_missing_scripts.py — list Unity components whose script is missing, without opening Unity.

Free, MIT-licensed companion to scene-audit. Reads text-serialized .unity and
.prefab files plus .meta files directly. Python 3.8+, standard library only.

Usage:
    python3 find_missing_scripts.py /path/to/UnityProject
    python3 find_missing_scripts.py /path/to/UnityProject --json

Exit code: 0 = no missing scripts, 1 = missing scripts found, 2 = usage/input error.

Scope: only the "The referenced script (Unknown) on this Behaviour is missing!"
case — a MonoBehaviour whose m_Script GUID resolves to no script in Assets/ or
Packages/. Broken object references, GUID collisions and report diffs are
not checked here; that is what the full scene-audit tool does.
"""
import json
import os
import re
import sys

DOC_HEADER = re.compile(r"^--- !u!(\d+) &(-?\d+)( stripped)?\s*$")
SCRIPT_REF = re.compile(r"^\s*m_Script:\s*\{fileID:\s*(-?\d+)(?:,\s*guid:\s*([0-9a-fA-F]+))?")
GAMEOBJECT_REF = re.compile(r"^\s*m_GameObject:\s*\{fileID:\s*(-?\d+)")
NAME = re.compile(r"^\s*m_Name:\s*(.*)$")
META_GUID = re.compile(r"^guid:\s*([0-9a-fA-F]{32})\s*$", re.M)
SCANNED = (".unity", ".prefab")
SCRIPT_EXTS = (".cs.meta", ".dll.meta")
# Built-in / engine GUIDs that never have a .meta in the project.
BUILTIN = {"0000000000000000e000000000000000", "0000000000000000f000000000000000"}


def project_script_guids(root):
    guids = set()
    for top in ("Assets", "Packages"):
        base = os.path.join(root, top)
        for dirpath, _, files in os.walk(base):
            for f in files:
                if f.endswith(SCRIPT_EXTS):
                    try:
                        with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                            m = META_GUID.search(fh.read())
                    except OSError:
                        continue
                    if m:
                        script = os.path.join(dirpath, f[: -len(".meta")])
                        if os.path.exists(script):
                            guids.add(m.group(1).lower())
    return guids


def parse_docs(path):
    """Yield dicts: class_id, file_id, line, lines[] for each YAML document."""
    docs, cur = [], None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            m = DOC_HEADER.match(line)
            if m:
                cur = {"class_id": int(m.group(1)), "file_id": m.group(2), "stripped": bool(m.group(3)), "line": n, "lines": []}
                docs.append(cur)
            elif cur is not None:
                cur["lines"].append(line)
    return docs


def scan_file(path, rel, known):
    with open(path, "rb") as fh:
        if b"\x00" in fh.read(8192):
            return None  # binary-serialized asset (NUL bytes): cannot read
    docs = parse_docs(path)
    names = {}
    for d in docs:
        if d["class_id"] == 1:  # GameObject
            for l in d["lines"]:
                m = NAME.match(l)
                if m:
                    names[d["file_id"]] = m.group(1).strip()
                    break
    found = []
    for d in docs:
        if d["class_id"] != 114 or d["stripped"]:
            continue
        fid, guid, go = None, None, None
        for l in d["lines"]:
            m = SCRIPT_REF.match(l)
            if m:
                fid, guid = m.group(1), (m.group(2) or "").lower()
            m = GAMEOBJECT_REF.match(l)
            if m:
                go = m.group(1)
        obj = names.get(go, "&" + d["file_id"])
        if fid is None or fid == "0" or not guid or guid == "0":
            found.append({"file": rel, "line": d["line"], "object": obj, "guid": guid or None, "reason": "m_Script is empty"})
        elif guid not in known and guid not in BUILTIN:
            found.append({"file": rel, "line": d["line"], "object": obj, "guid": guid, "reason": "script GUID not found in Assets/ or Packages/"})
    return found


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    if len(args) != 1 or "--help" in argv or "-h" in argv:
        print(__doc__.strip())
        return 2
    root = os.path.abspath(args[0])
    if not os.path.isdir(os.path.join(root, "Assets")):
        print(f"error: {root} has no Assets/ folder; pass the Unity project root", file=sys.stderr)
        return 2
    known = project_script_guids(root)
    findings, scanned, binary = [], 0, []
    for dirpath, dirs, files in os.walk(os.path.join(root, "Assets")):
        dirs.sort()
        for f in sorted(files):
            if f.endswith(SCANNED):
                full = os.path.join(dirpath, f)
                rel = os.path.relpath(full, root).replace(os.sep, "/")
                r = scan_file(full, rel, known)
                if r is None:
                    binary.append(rel)
                else:
                    scanned += 1
                    findings.extend(r)
    if as_json:
        print(json.dumps({"scanned": scanned, "binary_skipped": binary, "missing_scripts": findings}, indent=2))
    else:
        for x in findings:
            print(f"MISSING SCRIPT  {x['file']}:{x['line']}  {x['object']}  ({x['reason']}{', guid ' + x['guid'] if x['guid'] else ''})")
        print(f"\n{len(findings)} missing script(s) in {scanned} scene/prefab file(s).", end="")
        if binary:
            print(f" {len(binary)} binary-serialized file(s) skipped (set Asset Serialization to Force Text).", end="")
        print()
        if findings:
            print("Broken object references and GUID collisions are not checked by this free script.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
