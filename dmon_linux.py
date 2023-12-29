#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

# (c)2023-4 Lumeny
# Licensed under Apache License 2.0. See LICENSE file.
# a couple of ideas from https://rosettacode.org/wiki/Linux_CPU_utilization#Python

import json
import os
import sys

DMON_CPU = "c_cpu_s"
DMON_NETRX = "c_netrx_B"
DMON_NETTX = "c_nettx_B"

NETDEV_VAR = "DM_NET"
NETDEV_DEFAULT = "eth0"


def main():
    netdev = os.environ.get(NETDEV_VAR, NETDEV_DEFAULT)

    try:
        metrics = get_metrics(netdev)
    except Exception as e:
        metrics = {}
        raise e from None
    finally:
        json.dump(metrics, sys.stdout, separators=(",", ":"))
        sys.stdout.flush()


def get_metrics(netdev: str) -> dict:
    # as per proc(5), /proc/stat is in units of USER_HZ, readable from
    # sysconf(_SC_CLK_TCK)
    user_hz = os.sysconf("SC_CLK_TCK")

    base_metrics = {}

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

    with open("/proc/stat", "rt") as f:
        # the first line is always the "cpu" line, the first column is the line
        # name, the rest are all numbers, in units of USER_HZ ticks; the fourth
        # number is the ticks spent in the idle task
        fields = [int(column) for column in f.readline().split()[1:]]
        idle, total = fields[3], sum(fields)
        base_metrics[DMON_CPU] = (total - idle) / user_hz

    return {"base": base_metrics}


if __name__ == "__main__":
    main()
