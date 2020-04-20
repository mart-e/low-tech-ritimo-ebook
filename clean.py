#!/usr/bin/env python

from pathlib import Path
from lxml import etree

# where we want to cut in sections
CLASS_SECTION = "span5"
DEFAULT_CONTENT = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta content="text/html; charset=utf-8" http-equiv="content-type" />
    <link href="../styles/stylesheet.css" rel="stylesheet" type="text/css" />
    <title></title>
  </head>
  <body class="body0" xmlns:epub="http://www.idpf.org/2007/ops">
  </body>
</html>
"""


def get_body(content):
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
    root = etree.fromstring(content.encode('utf-8'), parser=parser)
    for child in root.getchildren():
        if child.tag.rpartition('}')[2] != "body":
            continue
        return root, child

new_section, new_body = get_body(DEFAULT_CONTENT)

for filename in sorted(Path("src/EPUB/sections/").glob("section*.xhtml")):
    with filename.open() as f:
        fcontent = f.read()
    content, body = get_body(fcontent)
    for p in body.getchildren():
        if p.tag.rpartition('}')[2] != "p":
            # not a tag, blindy copy it and move to next
            new_body.insert(p)
            continue

        # create new clone element
        new_p = etree.Element("p")
        # copy paragraph class
        for key, value in p.items():
            new_p.set(key, value)
        for span in p.getchildren():
            if span.tag.rpartition('}')[2] != "span":
                new_p.insert(span)
