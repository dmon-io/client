#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

# (c)2023-4 Lumeny
# Licensed under Apache License 2.0. See LICENSE file.
# a couple of ideas from https://rosettacode.org/wiki/Linux_CPU_utilization#Python

import argparse
import json
import os
import shutil
import sys
import time
import zlib

DMON_CPU = "c_cpu_s"
DMON_NETRX = "c_netrx_B"
DMON_NETTX = "c_nettx_B"
DMON_DISKFR = "m_g_diskfr_p"
MAX_DISKFR_ENTRIES = 4  # in.dmon.io will reject more than this

NETDEV_VAR = "DM_NET"
NETDEV_DEFAULT = "eth0"
REPORTED_FS = ["btrfs", "ext2", "ext3", "ext4", "xfs", "zfs"]

parser = argparse.ArgumentParser()
parser.add_argument("--cron", action="store_true")
args = parser.parse_args()


def main():
    netdev = os.environ.get(NETDEV_VAR, NETDEV_DEFAULT)

    # this flag staggers the cron by a repeatable amount for a given host
    # please run with --cron to help ease the :00 second burst on in.dmon.io
    # the stagger will offset the cron execution for between 5 and 55 seconds
    if args.cron:
        time.sleep(cron_stagger(netdev))

    try:
        metrics = get_metrics(netdev)
    except Exception as e:
        metrics = {}
        raise e from None
    finally:
        json.dump(metrics, sys.stdout, separators=(",", ":"))
        sys.stdout.flush()


def cron_stagger(netdev: str) -> int:
    try:
        with open("/sys/class/net/{}/address".format(netdev), "rt") as f:
            mac = f.read().strip()
            stagger = 5 + zlib.crc32(mac.encode("utf-8")) % 50
    except:
        stagger = 15
    return stagger


def get_metrics(netdev: str) -> dict:
    # as per proc(5), /proc/stat is in units of USER_HZ, readable from
    # sysconf(_SC_CLK_TCK)
    user_hz = os.sysconf("SC_CLK_TCK")

    base_metrics = {}

    ##### NET metrics
    try:
        with open("/sys/class/net/{}/statistics/rx_bytes".format(netdev), "rt") as f:
            rx = int(f.read().strip())
        with open("/sys/class/net/{}/statistics/tx_bytes".format(netdev), "rt") as f:
            tx = int(f.read().strip())
    except FileNotFoundError:
        pass
    else:
        # only send rx and tx if we successfully read both
        base_metrics[DMON_NETRX] = rx
        base_metrics[DMON_NETTX] = tx

    ##### CPU metrics
    with open("/proc/stat", "rt") as f:
        # the first line is always the "cpu" line, the first column is the line
        # name, the rest are all numbers, in units of USER_HZ ticks; the fourth
        # number is the ticks spent in the idle task
        fields = [int(column) for column in f.readline().split()[1:]]
        idle, total = fields[3], sum(fields)
        base_metrics[DMON_CPU] = (total - idle) / user_hz

    ##### DISKFREE metrics
    with open("/etc/mtab", "rt") as f:
        entries_sent = 0
        for line in f:
            [dev, mountpoint, fstype] = line.split()[:3]
            if fstype.strip() not in REPORTED_FS:
                continue
            try:
                du_res = shutil.disk_usage(mountpoint)
                if DMON_DISKFR not in base_metrics:
                    base_metrics[DMON_DISKFR] = {}
                # 20 character max for in.dmon.io
                base_metrics[DMON_DISKFR][mountpoint[:20]] = du_res.free / du_res.total
            except:
                pass
            entries_sent += 1
            if entries_sent >= MAX_DISKFR_ENTRIES:
                break

    return {"base": base_metrics}


if __name__ == "__main__":
    main()
