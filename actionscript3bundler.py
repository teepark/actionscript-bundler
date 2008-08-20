#!/usr/bin/env python

from optparse import OptionParser
import os
import re


IGNORED_TOPLEVELS = ("adobe", "flash", "fl", "mx")

import_re = re.compile(r"import(?: )+((?:\w+\.)*)(\w+);")
starimport_re = re.compile(r"import(?: )+((?:\w+\.)*)\*;")
linecomment_re = re.compile(r"//")

files = {}

def process_actionscript(location):
    if location in files:
        return

    f = open(location, "r")
    t = f.read()
    f.close()

    files[location] = t

    imports, starimports = [], []
    for line in t.split():
        comment = linecomment_re.search(line)

        match = import_re.search(line)
        if match and ((not comment) or comment.start() > match.end()):
            imports.append("".join(match.groups()))

        match = starimport_re.search(line)
        if match and ((not comment) or comment.start() > match.end()):
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
    for i in os.listdir(location):
        i = os.path.join(location, i)
        if i.endswith(".as") and i not in files:
            process_actionscript(i)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--start")

    options, args = parser.parse_args()
