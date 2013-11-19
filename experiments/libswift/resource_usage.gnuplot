set terminal pngcairo transparent enhanced font "arial,10" fontscale 1.0 size 800, 350
set title "CPU usage (" . peername  .")"
set output plotsdir . "/cpu_usage_" . peername . ".png"

set style fill transparent solid 0.5 noborder
set nokey

set ylabel "Usage (%)"
set xlabel "Time in experiment (s)"

set grid

set yrange [0:100]
set format y "%g %%"
plot logdir . "/resource_usage.log.parsed" using ($1*100) with filledcurve x1
set format y


reset
set style fill transparent solid 0.5 noborder
set nokey
set grid
set yrange [0:]
set title "Memory - Virtual Set Size  (" . peername  .")"
set ylabel "MiB"
set xlabel "Time in experiment (s)"
set output plotsdir . "/vsize_" . peername . ".png"
plot logdir . "/resource_usage.log.parsed" using ($2/1024/1024) with filledcurve x1 lc rgb "#0066CC"

reset
set style fill transparent solid 0.5 noborder
set nokey
set grid
set yrange [0:]
set title "Memory - Resident Set Size (" . peername . ")"
set xlabel "Time in experiment (s)"
set ylabel "MiB"
set output plotsdir . "/rss_" . peername . ".png"
plot logdir . "/resource_usage.log.parsed" using ($3/1024/1024) with filledcurve x1 lc rgb "#00CC00"

reset
set style fill transparent solid 0.5 noborder
set nokey
set grid
set yrange [0:]
set title "Aggregate Delayed Block I/O (" . peername . ")"
set xlabel "Time in experiment (s)"
set ylabel "Seconds"
set output plotsdir . "/dblk_" . peername . ".png"
plot logdir . "/resource_usage.log.parsed" using 4 with filledcurve x1 lc rgb "#FFFF33"
