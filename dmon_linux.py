#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

# (c)2023-4 Lumeny
# Licensed under Apache License 2.0. See LICENSE file.
# a couple of ideas from https://rosettacode.org/wiki/Linux_CPU_utilization#Python

import json
import os
import sys


def main():
    dm_net = os.environ.get("DM_NET", "eth0")
    clk_tck = os.sysconf("SC_CLK_TCK")

    base = {}

    with open(f"/sys/class/net/{dm_net}/statistics/tx_bytes", "rt") as f:
        base["c_nettx_B"] = int(f.read().strip())
    with open(f"/sys/class/net/{dm_net}/statistics/rx_bytes", "rt") as f:
        base["c_netrx_B"] = int(f.read().strip())

    with open("/proc/stat", "rt") as f:
        fields = [int(column) for column in f.readline().split()[1:]]
        idle, total = fields[3], sum(fields)
        base["c_cpu_s"] = (total - idle) / clk_tck

    json.dump({"base": base}, sys.stdout, separators=(",", ":"))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
