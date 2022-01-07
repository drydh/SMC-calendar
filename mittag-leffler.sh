#!/bin/bash
#
# Usage: mittag-leffler

# ----------------------------------------------------------------------
# Python setup
python="/usr/local/bin/python3" # Replace with specific version (e.g. python2) if necessary

# ----------------------------------------------------------------------
# Change to script directory

cd $(dirname "${BASH_SOURCE[0]}")
install -d Mittag-Leffler

DATE=$(date +"%Y%m%d-%H%M")

output_file="Mittag-Leffler/ML-seminars-$DATE.txt"

#$python ML-ads.py --start=20210801 --stop=20211231 --output "$output_file"
$python ML-ads.py --start=20220101 --stop=20220630 --output "$output_file"
