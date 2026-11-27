"""Run: python3 -m unittest test_find_missing_scripts.py"""
import json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "find_missing_scripts.py")
HDR = "%YAML 1.1\n%TAG !u! tag:unity3d.com,2011:\n"


def go(fid, name):
    return f"--- !u!1 &{fid}\nGameObject:\n  m_Name: {name}\n"


def mb(fid, go_id, script):
    return f"--- !u!114 &{fid}\nMonoBehaviour:\n  m_GameObject: {{fileID: {go_id}}}\n  m_Script: {script}\n"


class T(unittest.TestCase):
    def proj(self, files):
        d = tempfile.mkdtemp()
        for rel, body in files.items():
            p = os.path.join(d, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "wb") as fh:
                fh.write(body if isinstance(body, bytes) else body.encode())
        return d

    def run_tool(self, d, *extra):
        r = subprocess.run([sys.executable, TOOL, d, "--json", *extra], capture_output=True, text=True)
        return r.returncode, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else r.stdout)

    def test_present_script_is_clean(self):
        d = self.proj({"Assets/A.cs": "class A{}", "Assets/A.cs.meta": "fileFormatVersion: 2\nguid: " + "a" * 32 + "\n",
                       "Assets/S.unity": HDR + go(1, "Player") + mb(2, 1, "{fileID: 11500000, guid: " + "a" * 32 + ", type: 3}")})
        code, out = self.run_tool(d)
        self.assertEqual(code, 0); self.assertEqual(out["missing_scripts"], [])

    def test_missing_guid_reported_with_object_and_line(self):
        d = self.proj({"Assets/S.unity": HDR + go(1, "Enemy") + mb(2, 1, "{fileID: 11500000, guid: " + "b" * 32 + ", type: 3}")})
        code, out = self.run_tool(d)
        self.assertEqual(code, 1)
        [f] = out["missing_scripts"]
        self.assertEqual((f["file"], f["line"], f["object"], f["guid"]), ("Assets/S.unity", 6, "Enemy", "b" * 32))

    def test_meta_without_script_file_counts_as_missing(self):
        d = self.proj({"Assets/Gone.cs.meta": "guid: " + "c" * 32 + "\n",
                       "Assets/P.prefab": HDR + go(1, "Box") + mb(2, 1, "{fileID: 11500000, guid: " + "c" * 32 + ", type: 3}")})
        self.assertEqual(self.run_tool(d)[0], 1)

    def test_null_script_reference(self):
        d = self.proj({"Assets/S.unity": HDR + go(1, "X") + mb(2, 1, "{fileID: 0}")})
        code, out = self.run_tool(d)
        self.assertEqual(code, 1); self.assertEqual(out["missing_scripts"][0]["reason"], "m_Script is empty")

    def test_package_script_resolves(self):
        d = self.proj({"Packages/com.x/R.cs": "", "Packages/com.x/R.cs.meta": "guid: " + "d" * 32 + "\n",
                       "Assets/S.unity": HDR + go(1, "X") + mb(2, 1, "{fileID: 11500000, guid: " + "d" * 32 + ", type: 3}")})
        self.assertEqual(self.run_tool(d)[0], 0)

    def test_dll_script_resolves(self):
        d = self.proj({"Assets/Plugins/L.dll": b"MZ", "Assets/Plugins/L.dll.meta": "guid: " + "e" * 32 + "\n",
                       "Assets/S.unity": HDR + go(1, "X") + mb(2, 1, "{fileID: 123456, guid: " + "e" * 32 + ", type: 3}")})
        self.assertEqual(self.run_tool(d)[0], 0)

    def test_stripped_doc_ignored(self):
        d = self.proj({"Assets/S.unity": HDR + "--- !u!114 &5 stripped\nMonoBehaviour:\n  m_Script: {fileID: 11500000, guid: " + "f" * 32 + ", type: 3}\n"})
        self.assertEqual(self.run_tool(d)[0], 0)

    def test_binary_scene_skipped_not_crashing(self):
        d = self.proj({"Assets/B.unity": b"\x00\x01binary\x00"})
        code, out = self.run_tool(d)
        self.assertEqual(code, 0); self.assertEqual(out["binary_skipped"], ["Assets/B.unity"])

    def test_not_a_project(self):
        self.assertEqual(subprocess.run([sys.executable, TOOL, tempfile.mkdtemp()], capture_output=True).returncode, 2)

    def test_shipped_example(self):
        ex = os.path.join(HERE, "example-project")
        if os.path.isdir(ex):
            code, out = self.run_tool(ex)
            self.assertEqual(code, 1)
            self.assertEqual([(f["file"], f["object"]) for f in out["missing_scripts"]], [("Assets/Scenes/GameScene.unity", "Enemy (missing script)")])


if __name__ == "__main__":
    unittest.main()
