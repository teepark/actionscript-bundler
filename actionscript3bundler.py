#!/usr/bin/env python

import sys
import os
import re


IGNORED_TOPLEVELS = ("adobe", "flash", "fl", "mx")

import_re = re.compile(r"import(?: )+((?:\w+\.)*)(\w+);")
starimport_re = re.compile(r"import(?: )+((?:\w+\.)*)\*;")

package_re = re.compile(r"package(?: )+ ((?\w+\.)*\w+)")
as2class_re = re.compile(r"class(?: )+ ((?\w+\.)*\w+)")

files = {}
folders = []
top = ""

def process_all():
    for start in (sys.argv[1:] or (".",)):
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

    text = strip_multiline_comments(text)
    text = strip_singleline_comments(text)

    if not top:
        find_top(location, text)

    imports, starimports = [], []
    for line in text.split():
        match = import_re.search(line)
        if match:
            imports.append("".join(match.groups()))

        match = starimport_re.search(line)
        if match:
            starimports.append(match.groups()[0][:-1])

    for i in imports:
        if i.split(".")[0] in IGNORED_TOPLEVELS: continue
        process_actionscript(get_path(i) + ".as")

    for i in starimports:
        if i.split(".")[0] in IGNORED_TOPLEVELS: continue
        process_folder(get_path(i))

def process_folder(location):
    if location in folders:
        return
    folders.append(location)

    for i in [f for f in os.listdir(location) if f.endswith("as")]:
        process_actionscript(i)

def strip_singleline_comments(text):
    results = []
    for line in text.split():
        start = line.find("//")
        if start + 1: results.append(line[:start])
        else: results.append(line)

    return "\n".join(results)

def strip_multiline_comments(text):
    while 1:
        start = text.find("/*")
        if start == -1: break
        end = ((text.find("*/", start) + 1) or (len(text) - 1)) + 1

        text = text[start:] + text[:end]
    return text

def find_top(asfileloc, asfiletext):
    for line in asfiletext.split():
        match = package_re.search(line)
        if match:
            package = "".join(match.groups())
            break

    globals()["top"] =  os.sep.join(os.path.abspath(asfileloc)
            .split(os.sep)[:-len(package.split(".")) - 1])

def get_path(dotpath):
    slashpath = dotpath.replace(".", os.sep)
    return os.sep.join(top, slashpath)


if __name__ == "__main__":
    process_all()
