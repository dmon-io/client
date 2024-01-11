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
MAX_DISKFR_ENTRIES = 4  # in.dmon.io will reject more than this

NETDEV_VAR = "DM_NET"
NETDEV_DEFAULT = "eth0"
REPORTED_FS = ["btrfs", "ext2", "ext3", "ext4", "xfs", "zfs"]

### only used for --container
CONTAINER_DIR = "/var/lib/docker/containers"
CGROUP_DIR = "/sys/fs/cgroup/system.slice/docker-{container}.scope/"
# CGROUP_DIR = "/sys/fs/cgroup/docker/{container}/"
# CGROUP_DIR = "/sys/fs/cgroup/memory/docker/{container}/"
# CGROUP_DIR = "/sys/fs/cgroup/memory/system.slice/docker-{container}.scope/"
CGROUP_CPU_FILE = "cpu.stat"
CGROUP_CPU_STAT = "usage_usec"
CGROUP_CPU_DIV = 1024 * 1024

parser = argparse.ArgumentParser()
parser.add_argument("--net")
parser.add_argument("--cron", action="store_true")
parser.add_argument("--container", action="store_true")
args = parser.parse_args()


def main():
    if args.net:
        netdev = args.net
    else:
        netdev = os.environ.get(NETDEV_VAR, NETDEV_DEFAULT)

    # this flag staggers the cron by a repeatable amount for a given host
    # please run with --cron to help ease the :00 second burst on in.dmon.io
    # the stagger will offset the cron execution for between 5 and 55 seconds
    if args.cron:
        time.sleep(cron_stagger(netdev))

    try:
        metrics = get_metrics(netdev)
        if args.container:
            metrics["container"] = get_container_metrics()
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
    disk_metrics = []
    info_metrics = {}

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
    # first get the ior,iow stats per major,minor
    diskstats = {}
    with open("/proc/diskstats", "rt") as ds:
        for line in ds:
            fields = line.split()
            majorminor = fields[0] + "," + fields[1]
            diskstats[majorminor] = [int(fields[3]), int(fields[7])]
    with open("/proc/mounts", "rt") as f:
        entries_sent = 0
        for line in f:
            newdisk = {}
            [dev, mountpoint, fstype] = line.split()[:3]
            if fstype.strip() not in REPORTED_FS:
                continue
            # 20 character max for in.dmon.io
            newdisk["n"] = mountpoint[:20]
            try:
                du_res = shutil.disk_usage(mountpoint)
                newdisk["sz_B"] = du_res.total
                newdisk["g_av_B"] = du_res.free
                # get major,minor and check for disk stats
                majorminor = (
                    str(os.major(os.stat(dev).st_rdev))
                    + ","
                    + str(os.minor(os.stat(dev).st_rdev))
                )
                if majorminor in diskstats:
                    [newdisk["c_ior"], newdisk["c_iow"]] = diskstats[majorminor]
            except:
                pass
            disk_metrics.append(newdisk)
            entries_sent += 1
            if entries_sent >= MAX_DISKFR_ENTRIES:
                break

    ##### INFO metrics
    try:
        info_metrics["cpus"] = os.cpu_count()
    except:
        pass

    return {"base": base_metrics, "disk": disk_metrics, "info": info_metrics}


def get_container_metrics() -> dict:
    containers = []
    count = 0
    for containerid in os.listdir(CONTAINER_DIR):
        # currently the script assumes and only works with this structure
        # will have to get feedback on other needs
        # tested on ubuntu 22
        # if any of this fails, just basically skip gracefully
        try:
            configv2 = os.path.join(CONTAINER_DIR, containerid) + "/config.v2.json"
            f = open(configv2, "rt")  # failure wil just except-out here
            contents = json.load(f)
            if contents["State"]["Running"] == True:
                cg = open(CGROUP_DIR.format(container=containerid) + CGROUP_CPU_FILE)
                cpu_s = 0
                for line in cg:
                    if line[0 : len(CGROUP_CPU_STAT)] == CGROUP_CPU_STAT:
                        cpu_s = float(line.split()[1]) / CGROUP_CPU_DIV
                        break
                # if we got this far, add it to the list
                containers.append({"name": contents["Name"][1:], "c_cpu_s": cpu_s})
                count += 1
        except:
            pass
        if count >= 20:
            break
    return containers


if __name__ == "__main__":
    main()
