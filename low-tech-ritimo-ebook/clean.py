#!/usr/bin/env python

from pathlib import Path
from lxml import etree

# where we want to cut in sections
CLASS_SECTION = ["para14", "para26"]
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
DEFAULT_TOC = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
  <head>
    <title></title>
  </head>
  <body>
    <nav epub:type="toc">
      <ol>
      </ol>
    </nav>
  </body>
</html>
"""


def get_body(content):
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
    root = etree.fromstring(content.encode("utf-8"), parser=parser)
    for child in root.getchildren():
        if child.tag.rpartition("}")[2] != "body":
            continue
        return root, child


def find_footnote(node):
    for key, val in node.attrib.items():
        if key.rpartition("}")[2] == "type" and val == "noteref":
            # print("FOUND FOOTNOTE", node.attrib["href"], node.text)
            yield node.attrib["href"]
    for child in node.getchildren():
        yield from find_footnote(child)


def insert_footnotes(footnote_ids, from_body, to_body):
    found = []
    # find all footnotes and insert them at the end of the new body
    for child in from_body.getchildren():
        if (
            child.tag.rpartition("}")[2] == "aside"
            and "#" + child.attrib.get("id") in footnote_ids
        ):
            to_body.append(child)
            found.append("#" + child.attrib.get("id"))
    missing = set(footnote_ids) - set(found)
    if missing:
        print("!! MISSING FOOTNOTES !!", missing)
    return found


def split_sections():
    new_section, new_body = get_body(DEFAULT_CONTENT)
    sec_index = 1
    sec_footnotes = []
    section_titles = []
    section_title = "Introduction"

    # ensure target folder exists
    new_sections = Path("src/EPUB/new_sections")
    if not new_sections.exists():
        new_sections.mkdir()
        psrc = Path("src/EPUB/sections/cover.xhtml")
        pdst = Path("src/EPUB/new_sections/cover.xhtml")
        pdst.touch()
        with psrc.open() as src:
            with pdst.open("w") as dst:
                dst.write(src.read())

    for filename in sorted(Path("src/EPUB/sections/").glob("section*.xhtml")):
        print("READING", filename)
        with filename.open() as f:
            fcontent = f.read()
        _, body = get_body(fcontent)

        for p in body.getchildren():

            if p.tag.rpartition("}")[2] == "aside":
                # aside is for footnote, handled individually
                continue

            if p.tag.rpartition("}")[2] != "p":
                # not a tag, blindy copy it and move to next
                new_body.append(p)
                for footnote in find_footnote(p):
                    sec_footnotes.append(footnote)
                continue

            if p.attrib.get("class") in CLASS_SECTION:
                # break the document marker

                # 1. add section title to the list of sections
                section_titles.append(
                    (
                        section_title,
                        "sections/section%s.xhtml" % str(sec_index).rjust(4, "0"),
                    )
                )
                section_title = " ".join(
                    etree.tostring(p, method="text", encoding="utf-8")
                    .decode()
                    .replace("\n", "")
                    .strip()
                    .split()
                )

                # 2. retrieve all the footnotes
                insert_footnotes(sec_footnotes, body, new_body)

                # 3. write previous content to file
                path = Path(
                    "src/EPUB/new_sections/section%s.xhtml"
                    % str(sec_index).rjust(4, "0")
                )
                path.touch()
                print(
                    "WRITE TO FILE",
                    "src/EPUB/new_sections/section%s.xhtml"
                    % str(sec_index).rjust(4, "0"),
                )
                with path.open("w") as f:
                    # save everything computed so far
                    f.write(etree.tostring(new_section, encoding="utf-8").decode())

                # 4. generate new section
                new_section, new_body = get_body(DEFAULT_CONTENT)
                sec_index += 1  # increase filename
                sec_footnotes = []

            new_body.append(p)
            for footnote in find_footnote(p):
                sec_footnotes.append(footnote)

        print("END OF FILE", filename, "searching for footnotes", sec_footnotes)
        found = insert_footnotes(sec_footnotes, body, new_body)
        # should be empty
        sec_footnotes = list(set(sec_footnotes) - set(found))

    # write remaining content to file
    # 1. add section title to the list of sections
    section_titles.append(
        (section_title, "sections/section%s.xhtml" % str(sec_index).rjust(4, "0"),)
    )
    section_title = " ".join(
        etree.tostring(p, method="text", encoding="utf-8")
        .decode()
        .replace("\n", "")
        .strip()
        .split()
    )

    # 2. retrieve all the footnotes
    insert_footnotes(sec_footnotes, body, new_body)

    # 3. write previous content to file
    path = Path("src/EPUB/new_sections/section%s.xhtml" % str(sec_index).rjust(4, "0"))
    path.touch()
    print(
        "WRITE TO FILE",
        "src/EPUB/new_sections/section%s.xhtml" % str(sec_index).rjust(4, "0"),
    )
    with path.open("w") as f:
        # save everything computed so far
        f.write(etree.tostring(new_section, encoding="utf-8").decode())

    old_sections = Path("src/EPUB/sections")
    old_sections.rename("src/EPUB/old_sections")
    new_sections.rename("src/EPUB/sections")

    return section_titles


def write_content():
    fcontent = Path("src/EPUB/content.opf")
    with fcontent.open() as f:
        content = f.read()

    parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
    root = etree.fromstring(content.encode("utf-8"), parser=parser)
    for child in root.getchildren():

        if child.tag.rpartition("}")[2] == "manifest":
            all_sections = set(
                p.name for p in Path("src/EPUB/sections/").glob("section*.xhtml")
            )
            for item in child.getchildren():
                sid = item.attrib["id"]
                all_sections -= set([sid + ".xhtml"])
            for missing_sec in all_sections:
                item = etree.Element("item")
                path = Path(missing_sec)
                item.attrib["href"] = "sections/" + path.name
                item.attrib["id"] = path.name.split(".")[0]
                item.attrib["media-type"] = "application/xhtml+xml"
                child.append(item)

        elif child.tag.rpartition("}")[2] == "spine":
            all_sections = set(
                p.name.split(".")[0]
                for p in Path("src/EPUB/sections/").glob("section*.xhtml")
            )
            for itemref in child.getchildren():
                idref = itemref.attrib["idref"]
                all_sections -= set([idref])
            for missing_ref in sorted(list(all_sections)):
                itemref = etree.Element("itemref")
                path = Path(missing_ref)
                itemref.attrib["idref"] = path.name.split(".")[0]
                child.append(itemref)

    with fcontent.open("w") as f:
        f.write(etree.tostring(root, encoding="utf-8", pretty_print=True).decode())


def generate_toc(titles):
    # fcontent = Path("src/EPUB/toc.xhtml")
    # with fcontent.open() as f:
    #     content = f.read()
    content = DEFAULT_TOC
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
    root = etree.fromstring(content.encode("utf-8"), parser=parser)
    body = root.getchildren()[1]
    nav = body.getchildren()[0]
    ol = nav.getchildren()[0]

    title_index = 0  # to determine filename
    for title, href in titles:
        title_index += 1

        new_li = etree.Element("li")
        new_a = etree.Element("a")
        new_a.attrib["href"] = href
        new_a.text = title
        new_li.append(new_a)
        ol.append(new_li)

    fcontent = Path("src/EPUB/toc.xhtml")
    with fcontent.open("w") as f:
        f.write(etree.tostring(root, encoding="utf-8", pretty_print=True).decode())


if __name__ == "__main__":
    titles = split_sections()
    write_content()
    generate_toc(titles)
