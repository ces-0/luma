# OnePlus 5T (dumpling): build only

This page is not an install guide. Nothing here is allowed to write, erase,
repartition, unlock, relock, or RAM-boot a phone. The image this tree can
compile is **EXPERIMENTAL AND NOT HARDWARE TESTED**.

## Hardware prerequisite: unverified / pending

There is no evidence that postmarketOS boots on this user's OnePlus 5T.
That gap is a hard stop for every later phone step.

The public generic port page at <https://simplyluma.com/download/mobile/generic>
says, in its own words:

- "Boot a known-good image first, such as postmarketOS, then test your kernel RAM-only with `fastboot boot`."
- "Test it RAM-only with `fastboot boot` before you write anything to the phone."
- "Prove a known-good boot. An existing postmarketOS or other Linux image for this or a sibling device, if one exists. It tells you the boot chain, the console and the USB gadget work before you've written anything."
- "Never repartition, relock the bootloader, write `vbmeta`, or touch modem storage."
- "If a command fails, stop. Don't improvise a fix that writes to the phone."

postmarketOS is the page's example of a known-good image. The page does not
say that this phone has already started it. A wiki photo or another person's
port is not that evidence. Wikis are leads: the same page says "Treat wikis
and older guides as leads, not facts."

The OnePlus 5T wiki lead (not a fact about this phone) says an OxygenOS 9
bootloader gets stuck on a temporary RAM boot, and that a mainline kernel
with several appended device trees does not start. Because that support is
not verified here, a failed RAM boot must not be replaced by writing the
boot partition.

The longer brief also says "write `vbmeta` (unless the documented unlock flow
requires it)". This port does not implement that exception. Unlock, relock,
and any vbmeta write stay refused.

## Gates

| Gate | What it requires | State |
|---|---|---|
| 0 | This specific phone has booted postmarketOS, with a log the owner accepts | unverified / pending |
| 1 | Local compile of the pinned kernel, device tree, and a boot image file | this tree; compile is not a boot |
| 2 | Temporary RAM boot only, and only if gate 0 passed and this bootloader is known to support it | not authorized |
| 3 | A persistent write, only after gate 2 succeeded and a separate explicit confirmation | not authorized |

Persistent writes, if they are ever confirmed later, still may not
repartition, relock the bootloader, write vbmeta, or touch modem, persist,
fsg, or fsc. `modemst1` and `modemst2` stay preserved.

The Modem app and CRM are not part of this port and are not installed.

## What a local compile is

`scripts/kernel/build-dumpling.sh` checks out SimplyLuma/linux commit
`497791a0a96b866d90add64041c47acdff49cae6` (Linux 7.2.15 on `luma-7.2`),
builds `qcom/msm8998-oneplus-dumpling.dtb` and a kernel, and packs a header
version 0 boot image on the host. It exits if it is asked to flash, erase,
unlock, relock, repartition, or touch vbmeta, modem, or persist. Environment
variables cannot turn those paths on. There is no such path.

`device.toml` uses the release name `luma-kernel-7.2.15` because that is the
name `docs/kernel.md` gives a 7.2.15 kernel release. On 2026-11-19 that tag
did not exist. The script pins the commit, not a missing tag. There is also
no `msm8998` branch in SimplyLuma/linux; the family branch name in
`soc.toml` is the name the kernel document uses, and the source pin records
that the branch was absent.

## Firmware

Do not download or commit proprietary firmware. postmarketOS
`firmware-oneplus-msm8998` `pkgver=10.0.1` says the bytes were extracted from
OxygenOS 10.0.1. The license is proprietary. This manifest lists zero files.
A later, separate step can hash files the owner extracts from their own
factory image. Those bytes stay out of git.

## Build

On an x86_64 host with an aarch64 cross compiler:

```sh
scripts/kernel/build-dumpling.sh \
  --source /path/to/linux-497791a0a96b \
  --output /path/to/dumpling-out
```

The output directory is local. A successful compile does not mean the phone
starts, and a boot image is not permission to write it.

The host compile of commit `497791a0a96b866d90add64041c47acdff49cae6` is
recorded in `config/kernel/msm8998-dumpling-build-record.json`. That record
is a checksum list, not a boot result. `hardware_tested` and `boot_success`
are false. Kernel modules were not built. The initramfs is a placeholder
that does not start OSTree.
