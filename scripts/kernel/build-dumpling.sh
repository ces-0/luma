#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Local OnePlus 5T (dumpling) kernel, device tree, and boot-image compile.
#
# Gate 0, postmarketOS on this user's phone, is unverified/pending.
# Gate 2 (temporary RAM boot) and gate 3 (any persistent write) are not
# implemented. The generic port page says to prove a known-good image first,
# then RAM-boot, and to stop rather than invent a write when a command fails:
# https://simplyluma.com/download/mobile/generic
#
# usage: build-dumpling.sh --source KERNEL_TREE --output DIR
#
# KERNEL_TREE must be SimplyLuma/linux commit
# 497791a0a96b866d90add64041c47acdff49cae6 (Linux 7.2.15).
# DIR is a local directory. This script never calls a phone tool.

hardware_prerequisite=unverified-pending
phone_operations=forbidden

if [ -n "${LUMA_DUMPLING_ALLOW_FLASH:-}${LUMA_ALLOW_PHONE:-}${LUMA_ALLOW_FASTBOOT:-}" ]; then
  printf 'build-dumpling: phone operations are not enabled by environment variables\n' >&2
  exit 2
fi

for arg in "$@"; do
  case "$arg" in
    --flash|--erase|--format|--unlock|--relock|--repartition|--vbmeta|--boot-phone|--persist|--modem|--oem)
      printf 'build-dumpling: refused %s\n' "$arg" >&2
      exit 2
      ;;
  esac
done

set -euo pipefail

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
fail() { printf 'build-dumpling: %s\n' "$*" >&2; exit 1; }

source_dir=""
output_dir=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --source) source_dir=$(realpath -e "${2:?}"); shift 2 ;;
    --output) output_dir=${2:?}; shift 2 ;;
    -h|--help)
      printf 'usage: build-dumpling.sh --source KERNEL_TREE --output DIR\n'
      printf 'Build-only. Phone operations are refused. hardware_prerequisite=%s\n' "$hardware_prerequisite"
      exit 0
      ;;
    *) fail "unknown argument $1" ;;
  esac
done
[ -n "$source_dir" ] && [ -n "$output_dir" ] || fail "need --source and --output"
mkdir -p "$output_dir"
output_dir=$(realpath "$output_dir")

pin="$repo_root/config/kernel/msm8998-dumpling-source.json"
fragment="$repo_root/config/kernel/msm8998-dumpling.fragment"
boot_toml="$repo_root/devices/oneplus/dumpling/boot.toml"
soc_toml="$repo_root/socs/qcom/msm8998/soc.toml"
[ -f "$pin" ] && [ -f "$fragment" ] && [ -f "$boot_toml" ] && [ -f "$soc_toml" ] || fail "missing pin, fragment, or device files"

eval "$(python3 - "$pin" "$boot_toml" "$soc_toml" <<'PY'
import json, shlex, sys, tomllib
pin = json.load(open(sys.argv[1]))
boot = tomllib.load(open(sys.argv[2], "rb"))
soc = tomllib.load(open(sys.argv[3], "rb"))
off = soc["boot"]["offsets"]
vals = {
    "expect_commit": pin["commit"],
    "expect_prereq": pin["hardware_prerequisite"],
    "cmdline": " ".join(boot["cmdline"]["args"]),
    "page_size": str(soc["boot"]["page_size"]),
    "base": str(off["base"]),
    "kernel_offset": str(off["kernel"]),
    "ramdisk_offset": str(off["ramdisk"]),
    "tags_offset": str(off["tags"]),
}
if pin["phone_operations"] != "forbidden":
    raise SystemExit("source pin does not forbid phone operations")
for key, value in vals.items():
    print(f"{key}={shlex.quote(value)}")
PY
)"
[ "$expect_prereq" = "unverified-pending" ] || fail "source pin lost the unverified hardware prerequisite"
[ "$hardware_prerequisite" = "unverified-pending" ] || fail "internal prerequisite flag changed"

head_commit=$(git -C "$source_dir" rev-parse HEAD)
[ "$head_commit" = "$expect_commit" ] || fail "source HEAD $head_commit is not $expect_commit"
git -C "$source_dir" diff --quiet && git -C "$source_dir" diff --cached --quiet || fail "kernel tree is dirty; refusing to build from an unpinned patch"

dts="$source_dir/arch/arm64/boot/dts/qcom/msm8998-oneplus-dumpling.dts"
[ -f "$dts" ] || fail "dumpling DTS is not in this tree"
grep -q 'SPDX-License-Identifier: BSD-3-Clause' "$dts" || fail "dumpling DTS SPDX line missing"
grep -q 'Copyright (c) 2021, Jami Kettunen' "$dts" || fail "dumpling DTS copyright missing"
grep -q 'oneplus,dumpling' "$dts" || fail "dumpling compatible string missing"

if ! grep -q '^CONFIG_FUSE_FS=y$' "$fragment"; then
  fail "fragment does not build FUSE in"
fi

cross=${CROSS_COMPILE:-aarch64-linux-gnu-}
command -v "${cross}gcc" >/dev/null || fail "missing ${cross}gcc"
jobs=${JOBS:-2}
stamp=$(git -C "$source_dir" log -1 --format=%ct)
kbuild="$output_dir/kbuild"
mkdir -p "$kbuild"
printf 'running\n' >"$output_dir/status"

export ARCH=arm64
export CROSS_COMPILE="$cross"
export KBUILD_BUILD_USER=luma-dumpling-experimental
export KBUILD_BUILD_HOST=build-only
export SOURCE_DATE_EPOCH="$stamp"
export KBUILD_BUILD_TIMESTAMP
KBUILD_BUILD_TIMESTAMP=$(git -C "$source_dir" log -1 --format=%cI)

make -C "$source_dir" O="$kbuild" defconfig
KCONFIG_CONFIG="$kbuild/.config" "$source_dir/scripts/kconfig/merge_config.sh" -m -O "$kbuild" "$kbuild/.config" "$fragment"
make -C "$source_dir" O="$kbuild" olddefconfig
grep -q '^CONFIG_FUSE_FS=y$' "$kbuild/.config" || fail "CONFIG_FUSE_FS is not built-in after olddefconfig"
cp -a "$kbuild/.config" "$output_dir/config"

# %.dtb is remade as $(dtstree)/$@, so the goal is the path under arch/arm64/boot/dts.
make -C "$source_dir" O="$kbuild" -j"$jobs" Image Image.gz qcom/msm8998-oneplus-dumpling.dtb

image="$kbuild/arch/arm64/boot/Image"
image_gz="$kbuild/arch/arm64/boot/Image.gz"
dtb="$kbuild/arch/arm64/boot/dts/qcom/msm8998-oneplus-dumpling.dtb"
[ -f "$image" ] && [ -f "$image_gz" ] && [ -f "$dtb" ] || fail "kernel or DTB output missing"
file_image=$(file -b "$image")
case "$file_image" in
  *ARM64*|*aarch64*) ;;
  *) fail "kernel is not an arm64 Image: $file_image" ;;
esac
gzip -t "$image_gz"
dtb_magic=$(od -An -tx1 -N4 "$dtb" | tr -d ' ')
[ "$dtb_magic" = "d00dfeed" ] || fail "DTB magic is $dtb_magic"
install -m 0644 "$image" "$output_dir/Image"
install -m 0644 "$image_gz" "$output_dir/Image.gz"
install -m 0644 "$dtb" "$output_dir/msm8998-oneplus-dumpling.dtb"

# postmarketOS deviceinfo sets append_dtb and does not set a header version.
# The DTB is concatenated after the gzip payload. Header version stays 0.
cat "$output_dir/Image.gz" "$output_dir/msm8998-oneplus-dumpling.dtb" >"$output_dir/kernel.gz-dtb"

init_dir="$output_dir/initramfs"
rm -rf "$init_dir"
install -D -m 0755 /dev/null "$init_dir/init"
"${cross}gcc" -static -Os -Wall -Wextra -o "$init_dir/init" \
  "$repo_root/scripts/kernel/dumpling-experimental-init.c"
file_init=$(file -b "$init_dir/init")
case "$file_init" in
  *aarch64*) ;;
  *) fail "placeholder init is not a static aarch64 binary: $file_init" ;;
esac
install -D -m 0644 "$repo_root/scripts/mobile/common/initramfs/luma-ostree-boot.sh" \
  "$init_dir/usr/lib/luma/ostree-boot.sh"
install -D -m 0755 "$repo_root/scripts/mobile/common/initramfs/hooks-extra/50-luma-ostree-default.sh" \
  "$init_dir/hooks-extra/50-luma-ostree-default.sh"
printf '%s\n' \
  'EXPERIMENTAL AND NOT HARDWARE TESTED' \
  'hardware_prerequisite=unverified-pending' \
  'This archive is not a Luma root and not permission to write a phone.' \
  'The OSTree scripts are included and are not executed by the placeholder init.' \
  >"$init_dir/EXPERIMENTAL_NOT_HARDWARE_TESTED.txt"
find "$init_dir" -exec touch -h -d "@${stamp}" {} +
find "$init_dir" -type d -exec chmod 00755 {} +
(
  cd "$init_dir"
  find . -mindepth 1 | LC_ALL=C sort | cpio --quiet --reproducible -o -H newc -R 0:0
) | gzip -9n >"$output_dir/initramfs.cpio.gz"

boot_name="luma-dumpling-EXPERIMENTAL-NOT-HARDWARE-TESTED.boot"
python3 "$repo_root/scripts/kernel/pack-legacy-android-boot.py" \
  --kernel "$output_dir/kernel.gz-dtb" \
  --ramdisk "$output_dir/initramfs.cpio.gz" \
  --output "$output_dir/$boot_name" \
  --base "$base" \
  --kernel-offset "$kernel_offset" \
  --ramdisk-offset "$ramdisk_offset" \
  --tags-offset "$tags_offset" \
  --pagesize "$page_size" \
  --cmdline "$cmdline" \
  --header-version 0 \
  --name dumpling-expt

python3 - "$output_dir" "$head_commit" "$file_image" "$file_init" "$cmdline" "$jobs" "$cross" <<'PY'
import hashlib, json, platform, subprocess, sys
from pathlib import Path
out = Path(sys.argv[1])
names = [
    "Image", "Image.gz", "msm8998-oneplus-dumpling.dtb", "kernel.gz-dtb",
    "initramfs.cpio.gz", "luma-dumpling-EXPERIMENTAL-NOT-HARDWARE-TESTED.boot",
    "config",
]
checksums = {}
for name in names:
    data = (out / name).read_bytes()
    checksums[name] = hashlib.sha256(data).hexdigest()
(out / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name, digest in checksums.items()))
boot = (out / "luma-dumpling-EXPERIMENTAL-NOT-HARDWARE-TESTED.boot").read_bytes()
record = {
    "label": "EXPERIMENTAL AND NOT HARDWARE TESTED",
    "hardware_prerequisite": "unverified-pending",
    "phone_operations": "forbidden",
    "hardware_tested": False,
    "boot_success": False,
    "modules_built": False,
    "initramfs_kind": "placeholder-static-init-plus-unexecuted-resolver-scripts",
    "ostree_command_line_applied": False,
    "header_version": 0,
    "kernel_commit": sys.argv[2],
    "image_file": sys.argv[3],
    "init_file": sys.argv[4],
    "cmdline": sys.argv[5],
    "jobs": int(sys.argv[6]),
    "cross_compile": sys.argv[7],
    "host": platform.platform(),
    "sha256": checksums,
    "boot_magic": boot[:8].decode("ascii"),
    "boot_header_version_field": int.from_bytes(boot[40:44], "little"),
}
if record["boot_header_version_field"] != 0 or record["boot_magic"] != "ANDROID!":
    raise SystemExit("packed image is not a version-0 Android boot image")
(out / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps({k: record[k] for k in ("label", "kernel_commit", "header_version", "sha256")}, indent=2))
PY

printf 'built\n' >"$output_dir/status"
printf 'build-dumpling: EXPERIMENTAL AND NOT HARDWARE TESTED, local files only, in %s\n' "$output_dir"
