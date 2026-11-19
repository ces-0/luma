#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Pack a local legacy Android boot image, header version 0.

The header layout follows AOSP system/tools/mkbootimg/mkbootimg.py
write_header() for header_version == 0, commit
d2bb0af5ba6d3198a3e99529c97eda1be0b5a093 (Apache-2.0, Copyright 2015,
The Android Open Source Project).

This writes one local file. It does not talk to a phone.
"""

from __future__ import annotations

import argparse
import hashlib
import struct
import sys
from pathlib import Path

BOOT_MAGIC = b"ANDROID!"
BOOT_ARGS_SIZE = 512
BOOT_EXTRA_ARGS_SIZE = 1024
BOOT_NAME_SIZE = 16
HEADER_VERSION = 0


def pad(blob: bytes, page: int) -> bytes:
    extra = (page - (len(blob) % page)) % page
    return blob + bytes(extra)


def pack_image(
    kernel: bytes,
    ramdisk: bytes,
    *,
    base: int,
    kernel_offset: int,
    ramdisk_offset: int,
    tags_offset: int,
    page_size: int,
    cmdline: str,
    name: str,
) -> bytes:
    if page_size not in (2048, 4096, 16384):
        raise SystemExit(f"refusing page size {page_size}")
    encoded = cmdline.encode("ascii")
    if len(encoded) > BOOT_ARGS_SIZE + BOOT_EXTRA_ARGS_SIZE - 1:
        raise SystemExit("command line does not fit a version-0 header")
    # AOSP keeps a NUL at the end of the first field, then the remainder.
    cmdline_field = encoded[: BOOT_ARGS_SIZE - 1] + b"\x00"
    cmdline_field = cmdline_field.ljust(BOOT_ARGS_SIZE, b"\x00")
    extra = encoded[BOOT_ARGS_SIZE - 1 :].ljust(BOOT_EXTRA_ARGS_SIZE, b"\x00")
    board = name.encode("ascii")[: BOOT_NAME_SIZE - 1].ljust(BOOT_NAME_SIZE, b"\x00")

    digest = hashlib.sha1()
    for blob in (kernel, ramdisk, b""):
        digest.update(blob)
        digest.update(struct.pack("<I", len(blob)))
    image_id = digest.digest().ljust(32, b"\x00")

    kernel_addr = base + kernel_offset
    ramdisk_addr = (base + ramdisk_offset) if ramdisk else 0
    # AOSP writes 0 when the second bootloader image is absent.
    second_addr = 0
    header = b"".join(
        (
            struct.pack("<8s", BOOT_MAGIC),
            struct.pack("<I", len(kernel)),
            struct.pack("<I", kernel_addr),
            struct.pack("<I", len(ramdisk)),
            struct.pack("<I", ramdisk_addr),
            struct.pack("<I", 0),
            struct.pack("<I", second_addr),
            struct.pack("<I", base + tags_offset),
            struct.pack("<I", page_size),
            struct.pack("<I", HEADER_VERSION),
            struct.pack("<I", 0),
            board,
            cmdline_field,
            image_id,
            extra,
        )
    )
    if len(header) > page_size:
        raise SystemExit("header does not fit one page")
    blob = pad(header, page_size) + pad(kernel, page_size) + pad(ramdisk, page_size)
    return blob


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--kernel", type=Path, required=True)
    parser.add_argument("--ramdisk", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base", type=lambda s: int(s, 0), required=True)
    parser.add_argument("--kernel-offset", type=lambda s: int(s, 0), required=True)
    parser.add_argument("--ramdisk-offset", type=lambda s: int(s, 0), required=True)
    parser.add_argument("--tags-offset", type=lambda s: int(s, 0), required=True)
    parser.add_argument("--pagesize", type=int, required=True)
    parser.add_argument("--cmdline", required=True)
    parser.add_argument("--name", default="dumpling-expt")
    parser.add_argument("--header-version", type=int, default=0)
    args = parser.parse_args(argv)
    if args.header_version != 0:
        print("pack-legacy-android-boot: only header version 0 is implemented", file=sys.stderr)
        return 2
    image = pack_image(
        args.kernel.read_bytes(),
        args.ramdisk.read_bytes(),
        base=args.base,
        kernel_offset=args.kernel_offset,
        ramdisk_offset=args.ramdisk_offset,
        tags_offset=args.tags_offset,
        page_size=args.pagesize,
        cmdline=args.cmdline,
        name=args.name,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(image)
    print(
        f"EXPERIMENTAL AND NOT HARDWARE TESTED header_version=0 bytes={len(image)} output={args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
