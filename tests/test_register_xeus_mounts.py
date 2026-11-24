import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from register_xeus_mounts import register_mounts  # noqa: E402


class RegisterXeusMountsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env_dir = Path(self.tmp.name)
        packages = self.env_dir / "kernel_packages"
        packages.mkdir()
        for name in ["mount_10.tar.gz", "mount_2.tar.gz", "pkg.tar.gz"]:
            (packages / name).write_bytes(b"")
        (self.env_dir / "empack_env_meta.json").write_text(
            json.dumps({"prefix": "/", "packages": [], "specs": [], "channels": []}),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def read_mounts(self):
        meta = json.loads((self.env_dir / "empack_env_meta.json").read_text(encoding="utf-8"))
        return [item["filename"] for item in meta["mounts"]]

    def test_registers_mount_tarballs_in_index_order(self):
        register_mounts(self.env_dir)

        self.assertEqual(self.read_mounts(), ["mount_2.tar.gz", "mount_10.tar.gz"])

    def test_second_run_does_not_duplicate_entries(self):
        register_mounts(self.env_dir)
        register_mounts(self.env_dir)

        self.assertEqual(self.read_mounts(), ["mount_2.tar.gz", "mount_10.tar.gz"])


if __name__ == "__main__":
    unittest.main()
