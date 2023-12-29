import json, os, requests, re, sys

PROMURL = "http://localhost:9100/metrics"
PROM_CPU = "node_cpu_seconds_total"
PROM_NETRX = "node_network_receive_bytes_total"
PROM_NETTX = "node_network_transmit_bytes_total"
DM_NET = os.environ.get("DM_NET", "eth0")


def main():
    try:
        prom_metrics = requests.get(PROMURL)
        if prom_metrics.status_code != 200:
            print("{}")  # fix this later so failure doesn't break cron job
            sys.exit("Unable to get metrics from {}".format(PROMURL))
    except:
        print("{}")
        sys.exit("Unable to get metrics from {}".format(PROMURL))

    c_cpu_s = 0
    c_netrx_B = 0
    c_nettx_B = 0

    for line in prom_metrics.text.splitlines():
        metric = re.match(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)\{(.+)\}\s(\d.+)$", line)
        if metric:
            ### CPU
            if metric.group(1) == PROM_CPU:
                # sloppy here but probably mostly works
                # count everything except mode="idle"
                if not re.search(r'mode="idle"', metric.group(2)):
                    c_cpu_s += float(metric.group(3))
            ### NET
            if metric.group(1) == PROM_NETRX:
                if re.search('device="' + DM_NET + '"', metric.group(2)):
                    c_netrx_B += float(metric.group(3))
            if metric.group(1) == PROM_NETTX:
                if re.search('device="' + DM_NET + '"', metric.group(2)):
                    c_nettx_B += float(metric.group(3))

    output = {"base": {}}
    if c_cpu_s:
        output["base"]["c_cpu_s"] = c_cpu_s
    if c_netrx_B:
        output["base"]["c_netrx_B"] = int(c_netrx_B)
    if c_nettx_B:
        output["base"]["c_nettx_B"] = int(c_nettx_B)

    print(json.dumps(output))


if __name__ == "__main__":
    main()
