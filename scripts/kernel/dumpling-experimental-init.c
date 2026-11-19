// SPDX-License-Identifier: Apache-2.0
/*
 * Placeholder init for a local OnePlus 5T boot-image compile.
 *
 * It is not Luma's OSTree resolver, it does not mount a root filesystem,
 * and it does not reboot. A reboot is intentionally absent: on some Qualcomm
 * phones a normal restart is what lets the bootloader erase modem storage.
 * This binary must not be written to a phone from this tree.
 */
#include <fcntl.h>
#include <sys/types.h>
#include <unistd.h>

int main(void)
{
	static const char msg[] =
		"luma-dumpling: EXPERIMENTAL AND NOT HARDWARE TESTED\n"
		"luma-dumpling: postmarketOS prerequisite unverified/pending\n"
		"luma-dumpling: placeholder init, no root mount, no reboot\n";
	int fd = open("/dev/kmsg", O_WRONLY | O_NOCTTY);

	if (fd >= 0) {
		ssize_t wrote = write(fd, msg, sizeof(msg) - 1);

		if (wrote < 0)
			wrote = 0;
		(void)close(fd);
	}
	for (;;)
		sleep(3600);
}
