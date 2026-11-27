# Find missing scripts in a Unity project — without opening Unity

`find_missing_scripts.py` lists every component that shows **"The referenced script (Unknown) on this Behaviour is missing!"** across your scenes and prefabs. It reads Unity's text-serialized files directly, so it works in CI, on a build server, or on a machine with no Unity install or licence.

One file, Python 3.8+, standard library only. MIT licensed.

```
python3 find_missing_scripts.py /path/to/YourUnityProject
```

```
MISSING SCRIPT  Assets/Scenes/GameScene.unity:162  Enemy (missing script)  (script GUID not found in Assets/ or Packages/, guid 9999999999999999999999999999999a)

1 missing script(s) in 3 scene/prefab file(s).
```

Add `--json` for machine-readable output. Exit code is `0` when clean, `1` when a missing script is found, `2` for bad input — so it can fail a CI job:

```yaml
- run: python3 find_missing_scripts.py . 
```

## How it decides a script is missing

For each `MonoBehaviour` in every `.unity` and `.prefab` under `Assets/`, it reads `m_Script`. The script counts as present when some `.cs.meta` or `.dll.meta` in `Assets/` or `Packages/` declares that GUID **and** the script file next to it exists. An empty `m_Script` (`fileID: 0`) is also reported. Stripped prefab-instance documents are skipped.

## Limits

- Needs **Asset Serialization: Force Text** (Unity's default). Binary scenes/prefabs are listed as skipped, not read.
- Scripts that live only in `Library/PackageCache` (registry packages not embedded in `Packages/`) are not visible here and will show as missing. Check package-provided components by hand.
- Only scenes and prefabs are scanned; `.asset`, `.mat`, `.controller` and `.anim` files are not.
- Tested against the included `example-project` (Unity 2022.3 text format) and hand-written fixtures (`python3 -m unittest test_find_missing_scripts.py`, 10 tests). No other editor version has been tried.

## Need more than missing scripts?

[**scene-audit**](https://binding-bench.itch.io/scene-audit) is the full release check this script was cut from ($24.99, .NET 8 source CLI):

- **Broken references** — fields pointing at deleted objects or assets, including inside lists like `m_Materials`
- **GUID collisions** — two `.meta` files claiming the same GUID
- Scans `.asset`, `.mat`, `.controller` and `.anim` as well as scenes and prefabs
- JSON reports you commit as a baseline, and `diff` to see what broke since the last release

On the included example project, this free script finds 1 problem; scene-audit finds all 6 (1 missing script, 1 GUID collision, 4 broken references).

Code and text were written with AI assistance and checked with the included tests.
