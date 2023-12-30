#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

# (c)2023-4 Lumeny
# Licensed under Apache License 2.0. See LICENSE file.

import contextlib
import json
import os
import prometheus_client.parser as promparser
import requests
import sys

PROM_CPU = "node_cpu_seconds"
PROM_NETRX = "node_network_receive_bytes"
PROM_NETTX = "node_network_transmit_bytes"

DMON_CPU = "c_cpu_s"
DMON_NETRX = "c_netrx_B"
DMON_NETTX = "c_nettx_B"

URL_VAR = "DM_METRICS_URL"
URL_DEFAULT = "http://localhost:9100/metrics"
NETDEV_VAR = "DM_NET"
NETDEV_DEFAULT = "eth0"


def main():
    url = os.environ.get(URL_VAR, URL_DEFAULT)
    netdev = os.environ.get(NETDEV_VAR, NETDEV_DEFAULT)

    try:
        metrics = get_metrics(url, netdev)
    except Exception as e:
        metrics = {}
        raise e from None
    finally:
        json.dump(metrics, sys.stdout, separators=(",", ":"))
        sys.stdout.flush()


def get_metrics(url: str, netdev: str) -> dict:
    base_metrics = {}

    # old requests.Response (ubuntu 16.04's python3-requests) are not context
    # managers, so we have to wrap it
    with contextlib.closing(requests.get(url, stream=True)) as prom_metrics:
        prom_metrics.raise_for_status()

        # text_fd_to_metric_families claims to take a TextIO (so, a file-ish) but it
        # actually takes just an iterable of lines
        for m in promparser.text_fd_to_metric_families(
            prom_metrics.iter_lines(decode_unicode=True)
        ):
            # at some point prometheus-client's parser started stripping the
            # _total suffix, but we can just check for both
            if m.name == PROM_CPU or m.name == PROM_CPU + "_total":
                cpu_s = 0
                for sample in m.samples:
                    # older versions of prometheus-client used a normal tuple
                    # instead of a named one
                    labels, value = sample[1], sample[2]
                    if labels.get("mode", None) == "idle":
                        continue
                    cpu_s += value
                base_metrics[DMON_CPU] = cpu_s

            elif m.name == PROM_NETRX or m.name == PROM_NETRX + "_total":
                for sample in m.samples:
                    labels, value = sample[1], sample[2]
                    if labels.get("device", None) != netdev:
                        continue
                    base_metrics[DMON_NETRX] = value
                    break

            elif m.name == PROM_NETTX or m.name == PROM_NETTX + "_total":
                for sample in m.samples:
                    labels, value = sample[1], sample[2]
                    if labels.get("device", None) != netdev:
                        continue
                    base_metrics[DMON_NETTX] = value
                    break

    return {"base": base_metrics}


if __name__ == "__main__":
    main()
