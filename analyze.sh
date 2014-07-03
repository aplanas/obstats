#!/bin/bash

source ./obstats.cfg

function process_day {
    year=$1; month=$2; day=$3
    d=$year$month$day

    bunzip2 -k -c $DBENV/$year/$d.bz2 > $DBENV/$d
    bunzip2 -k -c $DBENV/$year/${d}_paths.bz2 > $DBENV/${d}_paths
    # bunzip2 -k -c $DBENV/$year/${d}_uuids.bz2 > $DBENV/${d}_uuids

    python analyze.py --dbenv $DBENV --db $d &> $LOGS/${d}-analyze.txt

    rm $DBENV/${d} $DBENV/${d}_paths
}


# If we don't say anything, we get since the beginning until today (excluded)
SINCE=${1:-"2014-01-01"}
LAST=${2:-`date -d "tomorrow" +%Y-%m-%d`}

echo "Analyzing from [$SINCE to $LAST)"


# Store the # on concurrent procs
count=0

current=$SINCE
while [ "$current" != "$LAST" ]; do
    # Extract date the components
    year=`echo $current | cut -d'-' -f1`
    month=`echo $current | cut -d'-' -f2`
    day=`echo $current | cut -d'-' -f3`

    echo "Converting $current ..."

    count=$((count + 1))
    ( process_day $year $month $day ) &

    if [ $((count % $NPROCS)) -eq 0 ]; then
	wait
    fi

    # Next day
    current=`date -d "$current +1 day " +%Y-%m-%d`
done

wait
