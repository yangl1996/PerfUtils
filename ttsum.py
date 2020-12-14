#!/usr/local/bin/python3

import argparse
import re

# parse command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("trace", help="path to the trace to analyze", type=open)
parser.add_argument("-s", "--start", required=True, help="starting event")
parser.add_argument("-e", "--end", required=True, help="end event")
parser.add_argument("-t", "--tail", help="tail percentile", type=float, nargs="?", default=99.0)
args = parser.parse_args()

# precompile the regex for performance
tracelineRegex = re.compile(r"  - .* function: (.*), cpu: .*, kind: (.*), tsc: ([0-9.]+), data: .*")
# collect the time to handle each request
latency = []
startTime = 0

def isEndEvent(func, event):
    if func == args.end and event == "function-exit":
        return True
    else:
        return False

def isStartEvent(func, event):
    if func == args.start and event == "function-enter":
        return True
    else:
        return False

# read the file once to account for event latency
started = False
for line in args.trace:
    match = tracelineRegex.match(line)
    if not match:
        continue
    func = match.group(1)
    event = match.group(2)
    tsc = int(match.group(3))
    # First match the end event. If the end event is not specified, use the start event
    if isEndEvent(func, event) and started:
        t = tsc - startTime
        latency.append(t)
    # Then we match the start event.
    if isStartEvent(func, event):
        startTime = tsc
        started = True

# sort the latency list to get the tail
latency.sort()
tailLatency = latency[int(len(latency) * args.tail / 100.0)]
print("Tail latency: {} ns @ {} %".format(tailLatency, args.tail))

def printTrace(lines):
    baseDepth = lines[0][3]
    for line in lines:
        print("{}{} - {}".format("  " * (line[3] - baseDepth), line[0], line[2]))


# read the file again to grab the trace for tail events
tailTrace = []
args.trace.seek(0)  # reset the file cursor
startTime = 0
stack = []  # track the call stack
trace = []  # track the trace for a single request
started = False
for line in args.trace:
    match = tracelineRegex.match(line)
    if not match:
        continue
    func = match.group(1)
    event = match.group(2)
    tsc = int(match.group(3))

    # If this is the starting event, empty the trace.
    if isStartEvent(func, event):
        trace = []

    # update the trace and the stack
    if event == "function-enter":
        traceLine = [func, tsc, None, None]  # function name, tsc counter upon enter, duration, stack depth
        # note that we do not fill the duration and the stack depth now
        trace.append(traceLine) # we are appending a pointer
        stack.append((func, tsc, traceLine)) # keep a point to the corresponding traceline
        traceLine[3] = len(stack)   # now that we know the depth of the stack, fill in the missing value
    elif event == "function-exit":
        (funcName, enterTime, traceLine) = stack.pop()
        traceLine[2] = tsc - enterTime

    # If this is the end event, dump the trace
    if isEndEvent(func, event) and started:
        t = tsc - startTime
        if t >= tailLatency:
            print("-------")
            printTrace(trace)
            print("-------")

    # If this is the starting event, set the start time.
    if isStartEvent(func, event):
        startTime = tsc
        started = True
