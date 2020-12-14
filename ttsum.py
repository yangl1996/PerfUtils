#!/usr/local/bin/python3

import argparse
import re

# parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("trace", help="path to the trace to analyze", type=open)
parser.add_argument("-s", "--start", required=True, help="starting event")
parser.add_argument("-e", "--end", help="end event")
parser.add_argument("-t", "--tail", help="tail percentile", type=float, required=True, argument_default=99.0)
args = parser.parse_args()

# precompile the regex for performance
tracelineRegex = re.compile(r"  - .* function: (.*), cpu: .*, kind: (.*), tsc: ([0-9.]+), data: .*")
# we need to track the call stack
#stack = []
# collect the time to handle each request
latency = []
startTime = 0

# read the file once to account for event latency
for line in args.trace:
    match = tracelineRegex.match(line)
    if not match:
        continue
    func = match.group(1)
    event = match.group(2)
    tsc = int(match.group(3))
    # First match the end event. If the end event is not specified, use the start event
    if args.end is None:
        if func == args.start and event == "function-enter":
            t = tsc - startTime
            latency.append(t)
    else:
        if func == args.end and event == "function-exit":
            t = tsc - startTime
            latency.append(t)
    # Then we match the start event.
    if func == args.start and event == "function-enter":
        startTime = tsc

# sort the latency list to get the tail
latency.sort()

print(latency)
