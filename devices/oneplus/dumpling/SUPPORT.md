# OnePlus 5T support notes

Build-only profile. No phone was contacted. Gate 0 (postmarketOS on this
user's phone) is **unverified / pending**. A kernel compile is not a boot.

Official staging text is the generic port page
<https://simplyluma.com/download/mobile/generic>, quoted in `INSTALL.md`.
Wiki rows below are leads from that page's own rule, not results on this phone.

| Item | Lead, checked 2026-11-19 | This tree |
|---|---|---|
| postmarketOS on this phone | Not observed | unverified / pending |
| Kernel we compile | SimplyLuma/linux `497791a0a96b` Linux 7.2.15, dumpling DTS already in tree (BSD-3-Clause, Jami Kettunen, 2021) | compiled locally: ARM64 Image, `CONFIG_FUSE_FS=y`. Not booted. Modules were not built |
| postmarketOS kernel package | `linux-postmarketos-qcom-msm8998` 6.0, commit `90169e6e` (2022-10-09), not 5.15 | not the tree we build |
| Phosh | Wiki caption still says a 5.15 photo. Not a 7.2 result | not run |
| Camera | Wiki `status_camera = N` | not tested |
| Wi-Fi | Wiki `status_wifi = Y` on their port. In Linux 7.2.15 `msm8998-oneplus-common.dtsi`, `&wifi` is not given `status = "okay"`; the comment says to leave it disabled until MSS works. The compiled DTB has `wifi@18800000` `status = "disabled"`. `qcom-diag` (andersson/diag `d06e599d`) installs an init script named `diag-router`, and the non-free firmware package depends on `qcom-diag` | disabled in this DTB, not tested |
| Firmware | Proprietary, OxygenOS 10.0.1 per the pmaports commit that added the package | not downloaded, zero manifest rows |
| Storage | DTS sets `&ufshc` `status = "okay"`. deviceinfo sets a 4096-byte sector size. Wiki `status_emmc = Y` is that table's internal-storage flag | source only |
| Temporary RAM boot | Wiki lead: OxygenOS 9 gets stuck. Not checked on this bootloader | not authorized; do not fall back to writing boot |
| Modem, calls, SMS, data | Wiki N for mobile data, SMS, and calls | not in scope; Modem app/CRM not installed |
| vbmeta, relock, repartition, persist, modem partitions | Forbidden by the generic page and by the scripts | no command exists |

`scripts/kernel/build-dumpling.sh` is the only build entry. It refuses phone operations.
