#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0

# (c)2023-4 Lumeny
# Licensed under Apache License 2.0. See LICENSE file.

import io
import json
import os
import re
import sys
import urllib.request

PROM_CPU = "node_cpu_seconds_total"
PROM_NETRX = "node_network_receive_bytes_total"
PROM_NETTX = "node_network_transmit_bytes_total"

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

    with urllib.request.urlopen(url) as prom_metrics:
        encoding = prom_metrics.info().get_content_charset(failobj="latin-1")

        for l in io.TextIOWrapper(prom_metrics, encoding=encoding):
            l = l.strip()
            if l == "" or l.startswith("#"):
                continue

            name, labels, value = _parse_sample(l)

            if name == PROM_CPU:
                if labels.get("mode", None) == "idle":
                    continue
                base_metrics[DMON_CPU] = base_metrics.get(DMON_CPU, 0.0) + value

            elif name == PROM_NETRX:
                if labels.get("device", None) == netdev:
                    base_metrics[DMON_NETRX] = value

            elif name == PROM_NETTX:
                if labels.get("device", None) == netdev:
                    base_metrics[DMON_NETTX] = value

    return {"base": base_metrics}


# code extracted from prometheus_client.parser 0.19.0
# https://github.com/prometheus/client_python/blob/v0.19.0/prometheus_client/parser.py
#
# Prometheus instrumentation library for Python applications
# Copyright 2015 The Prometheus Authors


def _parse_sample(text: str) -> tuple:
    # Detect the labels in the text
    try:
        label_start, label_end = text.index("{"), text.rindex("}")
        # The name is before the labels
        name = text[:label_start].strip()
        # We ignore the starting curly brace
        label = text[label_start + 1 : label_end]
        # The value is after the label end (ignoring curly brace)
        value = _parse_value(text[label_end + 1 :])
        return (name, _parse_labels(label), value)

    # We don't have labels
    except ValueError:
        # Detect what separator is used
        separator = " "
        if separator not in text:
            separator = "\t"
        name_end = text.index(separator)
        name = text[:name_end]
        # The value is after the name
        value = _parse_value(text[name_end:])
        return (name, {}, value)


def _parse_value(s: str) -> float:
    s = s.lstrip()
    separator = " "
    if separator not in s:
        separator = "\t"
    values = [value.strip() for value in s.split(separator) if value.strip()]
    if not values:
        return float(s), None
    value = float(values[0])
    # timestamp = (float(values[-1]) / 1000) if len(values) > 1 else None
    return value


def _is_character_escaped(s: str, charpos: int) -> bool:
    num_bslashes = 0
    while charpos > num_bslashes and s[charpos - 1 - num_bslashes] == "\\":
        num_bslashes += 1
    return num_bslashes % 2 == 1


_ESCAPING_RE = re.compile(r'\\[\\n"]')
_ESCAPE_SEQUENCES = {
    "\\\\": "\\",
    "\\n": "\n",
    '\\"': '"',
}


def _parse_labels(labels_string: str) -> dict:
    labels = {}
    # Return if we don't have valid labels
    if "=" not in labels_string:
        return labels

    escaping = False
    if "\\" in labels_string:
        escaping = True

    # Process one label at a time
    while labels_string:
        # The label name is before the equal
        value_start = labels_string.index("=")
        label_name = labels_string[:value_start]
        labels_string = labels_string[value_start + 1 :].lstrip()
        # Find the first quote after the equal
        quote_start = labels_string.index('"') + 1
        value_substr = labels_string[quote_start:]

        # Find the last unescaped quote
        i = 0
        while i < len(value_substr):
            i = value_substr.index('"', i)
            if not _is_character_escaped(value_substr, i):
                break
            i += 1

        # The label value is between the first and last quote
        quote_end = i + 1
        label_value = labels_string[quote_start:quote_end]
        # Replace escaping if needed
        if escaping:
            label_value = _ESCAPING_RE.sub(
                lambda match: _ESCAPE_SEQUENCES[match.group(0)],
                label_value,
            )
        labels[label_name.strip()] = label_value

        # Remove the processed label from the sub-slice for next iteration
        labels_string = labels_string[quote_end + 1 :]
        next_comma = labels_string.find(",") + 1
        labels_string = labels_string[next_comma:].lstrip()

    return labels


# end of code extracted from prometheus_client.parser 0.19.0


if __name__ == "__main__":
    main()
