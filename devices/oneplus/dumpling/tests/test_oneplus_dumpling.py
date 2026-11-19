# SPDX-License-Identifier: Apache-2.0
"""Build-only checks for the OnePlus 5T profile.

These tests do not touch a phone. They check the manifests, the safety
refusals, and the legacy boot-image packer.
"""

import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

DEVICE = Path(__file__).resolve().parents[1]
REPO = DEVICE.parents[2]
BUILD = REPO / "scripts" / "kernel" / "build-dumpling.sh"
PACKER = REPO / "scripts" / "kernel" / "pack-legacy-android-boot.py"
PIN = REPO / "config" / "kernel" / "msm8998-dumpling-source.json"
RECORD = REPO / "config" / "kernel" / "msm8998-dumpling-build-record.json"
CONFIG = REPO / "config" / "kernel" / "msm8998-dumpling.config"


def code_text(path: Path) -> str:
    lines = []
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("#"):
            continue
        lines.append(line.split("#", 1)[0])
    return "\n".join(lines)


class DumplingProfile(unittest.TestCase):
    def test_experimental_pin_and_empty_firmware(self):
        device = tomllib.loads((DEVICE / "device.toml").read_text())
        pin = json.loads(PIN.read_text())
        manifest = (DEVICE / "firmware.manifest").read_bytes()
        self.assertEqual(device["tier"], "experimental")
        self.assertEqual(device["soc"], "qcom/msm8998")
        self.assertEqual(device["kernel"]["dtb"], "qcom/msm8998-oneplus-dumpling.dtb")
        self.assertEqual(device["kernel"]["release"], "7.2.15")
        self.assertEqual(pin["commit"], "497791a0a96b866d90add64041c47acdff49cae6")
        self.assertFalse(pin["luma_kernel_tag_present_on_2026_11_19"])
        self.assertFalse(pin["family_branch_present_on_2026_11_19"])
        self.assertEqual(pin["hardware_prerequisite"], "unverified-pending")
        self.assertEqual(pin["phone_operations"], "forbidden")
        self.assertEqual(hashlib.sha256(manifest).hexdigest(), device["firmware"]["manifest_sha256"])
        self.assertEqual(device["firmware"]["files"], 0)
        self.assertEqual(manifest, b"H\t0\t-\t-\t-\n")
        self.assertNotIn("releases", device)
        self.assertNotIn("device_repo", device)
        self.assertEqual(device["updates"]["ostree_ref"], "luma/1/aarch64/nightly")
        record = json.loads(RECORD.read_text())
        self.assertEqual(record["hardware_prerequisite"], "unverified-pending")
        self.assertFalse(record["hardware_tested"])
        self.assertFalse(record["boot_success"])
        self.assertEqual(record["phone_operations"], "forbidden")
        self.assertEqual(record["header_version"], 0)
        self.assertEqual(record["kernel_commit"], pin["commit"])
        self.assertEqual(record["label"], "EXPERIMENTAL AND NOT HARDWARE TESTED")
        self.assertFalse(record["modules_built"])
        self.assertEqual(
            hashlib.sha256(CONFIG.read_bytes()).hexdigest(),
            record["sha256"]["config"],
        )
        for part in ("modemst1", "modemst2", "fsg", "fsc", "persist"):
            self.assertIn(part, device["install"]["preserve"])

    def test_boot_policy_does_not_sign_or_apply_dtbo(self):
        boot = tomllib.loads((DEVICE / "boot.toml").read_text())
        self.assertEqual(boot["avb"]["footer"], "none")
        self.assertEqual(boot["avb"]["vbmeta"], "untouched")
        self.assertEqual(boot["dtbo"]["policy"], "none")
        self.assertIn("clk_ignore_unused", boot["cmdline"]["args"])
        self.assertNotIn("pmos_root_uuid", [a.split("=", 1)[0] for a in boot["cmdline"]["args"]])
        guide = (DEVICE / "INSTALL.md").read_text()
        self.assertIn("unverified / pending", guide)
        self.assertIn("EXPERIMENTAL AND NOT HARDWARE TESTED", guide)
        self.assertNotRegex(guide, r"fastboot\s+(flash|erase|format)\b")

    def test_builder_refuses_phone_operations(self):
        code = code_text(BUILD)
        self.assertIn("hardware_prerequisite=unverified-pending", code)
        self.assertNotRegex(code, r"\b(fastboot|adb|sgdisk|parted)\b")
        for flag in ("--flash", "--erase", "--unlock", "--relock", "--repartition", "--vbmeta", "--boot-phone"):
            result = subprocess.run(["bash", str(BUILD), flag], check=False, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, flag)
            self.assertIn("refused", result.stderr)
        env = os.environ.copy()
        env["LUMA_DUMPLING_ALLOW_FLASH"] = "1"
        result = subprocess.run(
            ["bash", str(BUILD), "--help"], check=False, capture_output=True, text=True, env=env
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not enabled by environment", result.stderr)

    def test_packer_is_header_version_0_and_roundtrips(self):
        code = code_text(PACKER)
        self.assertNotRegex(code, r"\b(fastboot|adb|sgdisk|parted)\b")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kernel = root / "kernel"
            ramdisk = root / "ramdisk"
            output = root / "boot"
            kernel.write_bytes(b"K" * 100 + b"\xd0\x0d\xfe\xed" + b"DTB")
            ramdisk.write_bytes(b"R" * 50)
            result = subprocess.run(
                [
                    "python3", str(PACKER),
                    "--kernel", str(kernel),
                    "--ramdisk", str(ramdisk),
                    "--output", str(output),
                    "--base", "0",
                    "--kernel-offset", "0x8000",
                    "--ramdisk-offset", "0x1000000",
                    "--tags-offset", "0x100",
                    "--pagesize", "4096",
                    "--cmdline", "clk_ignore_unused quiet init=/init",
                    "--header-version", "0",
                ],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("EXPERIMENTAL AND NOT HARDWARE TESTED", result.stdout)
            blob = output.read_bytes()
            magic, ksize, kaddr, rsize, raddr, ssize, saddr, tags, page, version = struct.unpack_from(
                "<8s9I", blob, 0
            )
            self.assertEqual(magic, b"ANDROID!")
            self.assertEqual(version, 0)
            self.assertEqual(page, 4096)
            self.assertEqual(ksize, 100 + 7)
            self.assertEqual(kaddr, 0x8000)
            self.assertEqual(rsize, 50)
            self.assertEqual(raddr, 0x01000000)
            self.assertEqual(ssize, 0)
            self.assertEqual(saddr, 0)
            self.assertEqual(tags, 0x100)
            self.assertEqual(blob[4096:4096 + ksize], kernel.read_bytes())
            refused = subprocess.run(
                ["python3", str(PACKER), "--header-version", "2", "--kernel", str(kernel),
                 "--ramdisk", str(ramdisk), "--output", str(output), "--base", "0",
                 "--kernel-offset", "0", "--ramdisk-offset", "0", "--tags-offset", "0",
                 "--pagesize", "4096", "--cmdline", "x"],
                check=False, capture_output=True, text=True,
            )
            self.assertEqual(refused.returncode, 2)


if __name__ == "__main__":
    unittest.main()
