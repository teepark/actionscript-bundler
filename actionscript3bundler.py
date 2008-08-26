#!/usr/bin/env python

import logging
import optparse
import os
import re
import shutil
import sys
import tempfile
from xml.dom import minidom
import zipfile


IGNORED_TOPLEVELS = ["adobe", "flash", "fl", "mx"]

import_re = re.compile(r"import(?: )+((?:\w+\.)*)(\w+);")
starimport_re = re.compile(r"import(?: )+((?:\w+\.)*)\*;")

package_re = re.compile(r"package(?: )+((?:\w+\.)*\w+)")
#as2class_re = re.compile(r"class(?: )+((?:\w+\.)*\w+)")

files = []
folders = []
top = ""
tempdir = None

logger = logging.getLogger("as3bundler")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter())
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.CRITICAL)

def process_actionscript(location):
    if location in files:
        return

    logger.info("processing file %s", location)

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
            imp = "".join(match.groups())
            imports.append(imp)
            logger.info("found import '%s' in file %s", imp, location)

        match = starimport_re.search(line)
        if match:
            imp = match.groups()[0][:-1]
            starimports.append(imp)
            logger.info("found import '%s.*' in file %s", imp, location)

    for i in imports:
        if i.split(".")[0] in IGNORED_TOPLEVELS: continue
        process_actionscript(get_path(i) + ".as")

    for i in starimports:
        if i.split(".")[0] in IGNORED_TOPLEVELS: continue
        process_folder(get_path(i))

def process_folder(location):
    if location in folders:
        return

    logger.info("processing folder %s", location)
    folders.append(location)

    for i in [f for f in os.listdir(location) if f.endswith("as")]:
        process_actionscript(os.path.join(location, i))

def process_flp(location):
    logger.info("processing flash project file %s", location)
    try:
        flp = minidom.parse(location)
    except ExpatError:
        logger.error("error parsing flp file %s", location)
        return
    except IOError:
        logger.error("error reading flp file %s", location)
        return
    recurse_xml(flp)

def recurse_xml(node):
    if node.nodeName == "project_file" and \
            node.attributes["filetype"].value == "as":
        path = node.attributes["path"].value
        logger.info("found project file %s in flp file", path)
        process_actionscript(path)
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

def parse_options():
    parser = optparse.OptionParser()
    parser.set_defaults(output_location="ASBundle", output_format="zip",
                        verbose=False)

    parser.add_option("-o", "--output-location",
            help="location to store the bundle")
    parser.add_option("-f", "--output-format",
            choices=("zip", "folder", "none"),
            help="type of bundle to create ('zip', 'folder', or 'none')")
    parser.add_option("-i", "--ignore", action="append",
            help="ignore this top-level package (you may add this option more" +
                " than once. (%s) are already ignored)" %
                    ", ".join("'%s'" % a for a in IGNORED_TOPLEVELS))
    parser.add_option("-v", "--verbose", action="store_true",
            help="print information about what's going on")

    options, args = parser.parse_args()

    if options.verbose:
        logger.setLevel(logging.INFO)

    for ignored in options.ignore:
        IGNORED_TOPLEVELS.append(ignored)

    return options, args

def main(options, args):
    globals()["tempdir"] = tempfile.mkdtemp()
    for start in (args or (".",)):
        if os.path.isfile(start) and start.endswith(".as"):
            process_actionscript(start)
        elif os.path.isfile(start) and start.endswith(".flp"):
            process_flp(start)
        elif os.path.isdir(start):
            process_folder(start)

    if options.output_format == "zip":
        zfile = zipfile.ZipFile(options.output_location, 'w')
        for root, dirs, files in os.walk(tempdir):
            for filename in files:
                source = os.path.join(root, filename)
                destination = os.path.join(root[len(tempdir):], filename)
                zfile.write(source, destination, zipfile.ZIP_STORED)
        shutil.rmtree(tempdir)
        zfile.close()
    elif options.output_format == "folder":
        shutil.copytree(tempdir, options.output_location)


if __name__ == "__main__":
    main(*parse_options())
