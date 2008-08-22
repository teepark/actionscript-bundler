#!/usr/bin/env python

import sys
import os
import re


IGNORED_TOPLEVELS = ("adobe", "flash", "fl", "mx")

import_re = re.compile(r"import(?: )+((?:\w+\.)*)(\w+);")
starimport_re = re.compile(r"import(?: )+((?:\w+\.)*)\*;")

files = {}

def process_all():
    starts = sys.argv[1:]
    if not starts:
        starts = (".",)

    for start in starts:
        if os.path.isfile(start) and start.endswith(".as"):
            process_actionscript(start)
        elif os.path.isdir(start):
            process_folder(start)

def process_actionscript(location):
    if location in files:
        return

    f = open(location, "r")
    text = f.read()
    f.close()

    files[location] = text

    while 1:
        start = text.find("/*")
        if start == -1: break
        end = ((text.find("*/", start) + 1) or (len(text) - 1)) + 1
        text = text[start:] + text[:end]

    imports, starimports = [], []
    for line in text.split():
        comment_start = line.find("//")
        comment = comment_start != -1

        match = import_re.search(line)
        if match and (not comment or comment_start > match.end()):
            imports.append("".join(match.groups()))

        match = starimport_re.search(line)
        if match and (not comment or comment_start > match.end()):
            starimports.append(match.groups()[0][:-1])

    for i in imports:
        i = i.replace(".", os.sep) + ".as"
        if i.split(os.sep, 1)[0] in IGNORED_TOPLEVELS or i in files:
            continue
        process_actionscript(i)

    for i in starimports:
        i = i.replace(".", os.sep)
        if i.split(os.sep, 1)[0] in IGNORED_TOPLEVELS:
            continue
        process_folder(i)

def process_folder(location):
    for i in [f for f in os.listdir(location) if f.endswith("as")]:
        process_actionscript(i)


if __name__ == "__main__":
    process_all()
