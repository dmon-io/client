:local telemetryKey Ssc8WBEuf4YNvjnEyMGZgK
:local jobName mikrotik-gw
:local iface ether8
# utility function because of the wonky way routeros presents "bytes"
:global removeSpace do={ :local temp;
    :for i from=0 to=([:len $t] - 1) do={ :local char [:pick $t $i];
        :if ($char = " ") do={ :set $char ""; }
        :set temp ($temp . $char); }
    :return $temp; }
#:local temperature [/system health get temperature]
:local cpuload [/system resource get cpu-load]
:local rxbytes [$removeSpace t=[:tostr [/interface ethernet get value-name=rx-bytes $iface]]]
:local txbytes [$removeSpace t=[:tostr [/interface ethernet get value-name=tx-bytes $iface]]]
#:local rxbytes [/interface ethernet get $iface rx-bytes]
/tool fetch http-method=post mode=https url="https://in.dmon.io:443/$telemetryKey/$jobName" http-header-field="content-type:application/json" output=none http-data="{\"base\":{\"c_netrx_B\": $rxbytes, \"c_nettx_B\": $txbytes }}"
# for when g_cpu is implemented on in.dmon.io
# /tool fetch http-method=post mode=https url="https://in.dmon.io:443/$telemetryKey/$jobName" http-header-field="content-type:application/json" output=none http-data="{\"base\":{\"c_cpu_s\": $cpuload, \"c_netrx_B\": $rxbytes, \"c_nettx_B\": $txbytes }}"
:log info ("dmon_metrics posted to in.dmon.io")
