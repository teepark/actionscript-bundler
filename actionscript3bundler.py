#!/usr/bin/env python

import os
import re
import shutil
import sys
import tempfile
from xml.dom import minidom
import zipfile


IGNORED_TOPLEVELS = ("adobe", "flash", "fl", "mx")
ARCHIVE_NAME = "ASBundle.zip"

import_re = re.compile(r"import(?: )+((?:\w+\.)*)(\w+);")
starimport_re = re.compile(r"import(?: )+((?:\w+\.)*)\*;")

package_re = re.compile(r"package(?: )+((?:\w+\.)*\w+)")
#as2class_re = re.compile(r"class(?: )+((?:\w+\.)*\w+)")

files = []
folders = []
top = ""
tempdir = None

def process_actionscript(location):
    if location in files:
        return

    f = open(location, "r")
    text = f.read()
    f.close()

    files.append(location)

    text = strip_multiline_comments(text)
    text = strip_singleline_comments(text)

    for line in text.splitlines():
        match = package_re.search(line)
        if match:
            package = "".join(match.groups())
            break
    else:
        raise Exception("no package statement in AS file '" + location + "'")
    compath = os.sep.join(package.split(".") +
            [os.path.basename(location)])

    destination = tempdir + os.sep + compath
    if not os.path.isdir(os.path.dirname(destination)):
        os.makedirs(os.path.dirname(destination))
    shutil.copyfile(location, destination)

    if not top:
        find_top(location, text)

    imports, starimports = [], []
    for line in text.splitlines():
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
        process_actionscript(os.path.join(location, i))

def process_flp(location):
    try:
        flp = minidom.parse(location)
    except ExpatError:
        return
    except IOError:
        return
    recurse_xml(flp)

def recurse_xml(node):
    if node.nodeName == "project_file" and \
            node.attributes["filetype"].value == "as":
        process_actionscript(node.attributes["path"].value)
    else:
        for child in node.childNodes:
            recurse_xml(child)

def strip_singleline_comments(text):
    results = []
    for line in text.splitlines():
        start = line.find("//")
        if start + 1: results.append(line[:start])
        else: results.append(line)

    return "\n".join(results)

def strip_multiline_comments(text):
    while 1:
        start = text.find("/*")
        if start == -1: break
        end = ((text.find("*/", start) + 1) or (len(text) - 1)) + 1

        text = text[:start] + text[end:]
    return text

def find_top(asfileloc, asfiletext):
    for line in asfiletext.splitlines():
        match = package_re.search(line)
        if match:
            package = "".join(match.groups())
            break

    globals()["top"] =  os.sep.join(os.path.abspath(asfileloc)
            .split(os.sep)[:-len(package.split(".")) - 1])

def get_path(dotpath):
    slashpath = dotpath.replace(".", os.sep)
    return os.sep.join((top, slashpath))

def main():
    globals()["tempdir"] = tempfile.mkdtemp()
    for start in (sys.argv[1:] or (".",)):
        if os.path.isfile(start) and start.endswith(".as"):
            process_actionscript(start)
        elif os.path.isfile(start) and start.endswith(".flp"):
            process_flp(start)
        elif os.path.isdir(start):
            process_folder(start)

    zfile = zipfile.ZipFile(ARCHIVE_NAME, 'w')
    for root, dirs, files in os.walk(tempdir):
        for filename in files:
            source = os.path.join(root, filename)
            destination = os.path.join(root[len(tempdir):], filename)
            zfile.write(source, destination, zipfile.ZIP_STORED)
    shutil.rmtree(tempdir)
    zfile.close()


if __name__ == "__main__":
    main()
