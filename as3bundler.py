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


IGNORED_TOPLEVELS = set(("adobe", "flash", "fl", "mx"))

import_re = re.compile(r"import(?: )+((?:\w+\.)*)(\w+);")
starimport_re = re.compile(r"import(?: )+((?:\w+\.)*)\*;")

package_re = re.compile(r"package(?: )+((?:\w+\.)*\w+)")
#as2class_re = re.compile(r"class(?: )+((?:\w+\.)*\w+)")

classpaths = set()
searched_classpaths = set()
files = set()
folders = set()
tempdir = None

logger = logging.getLogger("as3bundler")
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter())
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.CRITICAL)

def process_actionscript(location):
    "include an actionscript file and look for imports to include"
    if location in files:
        # then we've done this one before
        return

    # remember this file so we won't process it again
    files.add(location)

    logger.info("processing file %s", location)

    # read the file
    f = open(location, "r")
    text = f.read()
    f.close()

    # pull all comments out before searching for package and imports
    text = strip_multiline_comments(text)
    text = strip_singleline_comments(text)

    # find the package statement, use that to figure out the
    # location of the whole classpath
    for line in text.splitlines():
        match = package_re.search(line)
        if match:
            package = "".join(match.groups())
            break
    else:
        raise Exception("no package statement in AS file '" + location + "'")

    # if we are intentionally ignoring this package, quit processing now
    if package.split(".", 1)[0] in IGNORED_TOPLEVELS:
        return

    # copy the file to a directory in /temp
    destination = os.sep.join([tempdir] + package.split(".") +
                              [os.path.basename(location)])
    if not os.path.isdir(os.path.dirname(destination)):
        os.makedirs(os.path.dirname(destination))
    shutil.copyfile(location, destination)

    # if we don't have any classpaths, find the one this file belogs to
    if location not in searched_classpaths:
        find_classpath(location, text)

    # line by line, look for imports
    imports, starimports = set(), set()
    for line in text.splitlines():
        match = import_re.search(line)
        if match:
            imp = "".join(match.groups())
            imports.add(imp)
            logger.info("found import '%s' in file %s", imp, location)

        match = starimport_re.search(line)
        if match:
            imp = match.groups()[0][:-1]
            starimports.add(imp)
            logger.info("found import '%s.*' in file %s", imp, location)

    # recurse into each import found
    for i in imports:
        if i.split(".")[0] in IGNORED_TOPLEVELS: continue
        process_folder(os.sep.join(get_path(i).split(os.sep)[:-1]))

    for i in starimports:
        if i.split(".")[0] in IGNORED_TOPLEVELS: continue
        process_folder(get_path(i))

def process_folder(location):
    "run process_actionscript on every .as file in the given folder"
    if location in folders:
        return

    logger.info("processing folder %s", location)
    folders.add(location)

    for i in [f for f in os.listdir(os.path.abspath(location))
            if f.endswith(".as")]:
        process_actionscript(os.path.join(location, i))

def process_flp(location):
    "run process_actionscript on every .as file in the given .flp file"
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
    "recurse into childnodes in a .flp file"
    if node.nodeName == "project_file" and \
            node.attributes["filetype"].value == "as":
        path = node.attributes["path"].value
        logger.info("found project file %s in flp file", path)
        process_folder(os.path.dirname(path))
    else:
        for child in node.childNodes:
            recurse_xml(child)

def strip_singleline_comments(text):
    "pull out '//' comments"
    results = []
    for line in text.splitlines():
        start = line.find("//")
        if start + 1: results.append(line[:start])
        else: results.append(line)

    return "\n".join(results)

def strip_multiline_comments(text):
    "pull out /* ... */ comments"
    while 1:
        start = text.find("/*")
        if start == -1: break
        end = ((text.find("*/", start) + 1) or (len(text) - 1)) + 1

        text = text[:start] + text[end:]
    return text

def find_classpath(asfileloc, asfiletext):
    """use a 'package' statement and the location of the file
    to calculate the classpath"""
    for line in asfiletext.splitlines():
        match = package_re.search(line)
        if match:
            package = "".join(match.groups())
            break

    path = os.sep.join(os.path.abspath(asfileloc).split(os.sep)[:-len(
            package.split(".")) - 1])

    classpaths.add(path)

    searched_classpaths.add(asfileloc)

def get_path(dotpath):
    "translate a '.'-based path into a filesystem path"
    slashpath = dotpath.replace(".", os.sep)
    for classpath in classpaths:
        filepath = os.sep.join((classpath, slashpath))
        if os.path.isfile(filepath) or os.path.isdir(filepath):
            return filepath
    raise Exception(("An AS file corresponding to '%s' can't be found. " +
            "Did you forget to specify an extra classpath?") % slashpath)

def parse_options():
    "use optparse to determine command-line options and arguments"
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
    parser.add_option("-p", "--class-path", action="append",
            help="search the provided class-path in addition to the one " +
                "containing the starting point(s) (you may add this option " +
                "more than once)")

    options, args = parser.parse_args()

    if options.verbose:
        logger.setLevel(logging.INFO)

    for ignored in (options.ignore or ()):
        IGNORED_TOPLEVELS.add(ignored)

    for path in (options.class_path or ()):
        classpaths.add(path)

    return options, args

def main(options, args):
    globals()["tempdir"] = tempfile.mkdtemp()

    try:
        # use all the provided start points to build up the temp dir
        for start in (args or (".",)):
            if os.path.isfile(start) and start.endswith(".as"):
                process_folder(os.path.dirname(start))
            elif os.path.isfile(start) and start.endswith(".flp"):
                process_flp(start)
            elif os.path.isdir(start):
                process_folder(start)

        # copy everything in the temp dir into the new bundle
        output = options.output_location
        if options.output_format == "zip":
            if not output.endswith(".zip"):
                output += ".zip"
            zfile = zipfile.ZipFile(output, 'w')
            for root, dirs, files in os.walk(tempdir):
                for filename in files:
                    source = os.path.join(root, filename)
                    destination = os.path.join(root[len(tempdir):], filename)
                    zfile.write(source, destination, zipfile.ZIP_STORED)
            zfile.close()
        elif options.output_format == "folder":
            shutil.copytree(tempdir, output)
    finally:
        # clean up the tempdir
        shutil.rmtree(tempdir)


if __name__ == "__main__":
    main(*parse_options())
