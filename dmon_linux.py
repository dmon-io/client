# (c)2023-4 Lumeny
# Licensed under Apache License 2.0. See LICENSE file.
# a couple of ideas from https://rosettacode.org/wiki/Linux_CPU_utilization#Python
import json, os

DM_NET = os.environ.get("DM_NET", "eth0")


def main():
    c_cpu_s = 0
    c_netrx_B = 0
    c_nettx_B = 0

    output = {"base": {}}

    with open("/proc/net/dev") as f:
        for line in f.readlines():
            fields = line.split()
            if fields[0] != DM_NET + ":":
                continue
            output["base"]["c_netrx_B"] = int(fields[1])
            output["base"]["c_nettx_B"] = int(fields[9])

    with open("/proc/stat") as f:
        fields = [int(column) for column in f.readline().strip().split()[1:]]
        idle, total = fields[3], sum(fields)
        output["base"]["c_cpu_s"] = (total - idle) / 100

    print(json.dumps(output))


if __name__ == "__main__":
    main()
