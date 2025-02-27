#!/usr/bin/env python3
import socket
import time

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(('192.168.4.1', 123))
s.settimeout(5)

ignorefirst = 4
baseline = None
with s.makefile() as f:
    for line in f:
        if ignorefirst > 0:
            ignorefirst -= 1
            continue
        there = int(line.strip()) * 0.001
        diff = time.perf_counter() - there
        if baseline is None:
            baseline = diff
            continue
        print(diff - baseline)
