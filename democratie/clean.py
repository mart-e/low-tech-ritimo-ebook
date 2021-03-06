#!/usr/bin/env python

from pathlib import Path
from lxml import etree

PARSER = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")

# where we want to cut in sections
CLASS_SECTION = ["para2"] #["para14", "para26"]
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
    root = etree.fromstring(content.encode("utf-8"), parser=PARSER)
    for child in root.getchildren():
        if child.tag.rpartition("}")[2] != "body":
            continue
        return root, child

def replace_body(root, new_body):
    for child in root.getchildren():
        if child.tag.rpartition("}")[2] != "body":
            continue
        body = child
        break
    root.replace(body, new_body)
    return root


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
    new_sections = Path("src/OEBPS/new_sections")
    if not new_sections.exists():
        new_sections.mkdir()
        psrc = Path("src/OEBPS/sections/cover.xhtml")
        pdst = Path("src/OEBPS/new_sections/cover.xhtml")
        pdst.touch()
        with psrc.open() as src:
            with pdst.open("w") as dst:
                dst.write(src.read())

    for filename in sorted(Path("src/OEBPS/sections/").glob("section*.xhtml")):
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
                    "src/OEBPS/new_sections/section%s.xhtml"
                    % str(sec_index).rjust(4, "0")
                )
                path.touch()
                print(
                    "WRITE TO FILE",
                    "src/OEBPS/new_sections/section%s.xhtml"
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
    path = Path("src/OEBPS/new_sections/section%s.xhtml" % str(sec_index).rjust(4, "0"))
    path.touch()
    print(
        "WRITE TO FILE",
        "src/OEBPS/new_sections/section%s.xhtml" % str(sec_index).rjust(4, "0"),
    )
    with path.open("w") as f:
        # save everything computed so far
        f.write(etree.tostring(new_section, encoding="utf-8").decode())

    old_sections = Path("src/OEBPS/sections")
    old_sections.rename("src/OEBPS/old_sections")
    new_sections.rename("src/OEBPS/sections")

    return section_titles


def write_content():
    fcontent = Path("src/OEBPS/content.opf")
    with fcontent.open() as f:
        content = f.read()

    parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
    root = etree.fromstring(content.encode("utf-8"), parser=parser)
    for child in root.getchildren():

        if child.tag.rpartition("}")[2] == "manifest":
            all_sections = set(
                p.name for p in Path("src/OEBPS/sections/").glob("section*.xhtml")
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
                for p in Path("src/OEBPS/sections/").glob("section*.xhtml")
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
    # fcontent = Path("src/OEBPS/toc.xhtml")
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

    fcontent = Path("src/OEBPS/toc.xhtml")
    with fcontent.open("w") as f:
        f.write(etree.tostring(root, encoding="utf-8", pretty_print=True).decode())

def merge_tag(root):
    previous_node = False
    previous_tag = False
    previous_class = False
    new_root = etree.Element(root.tag, root.attrib)
    for p in root.getchildren():
        current_tag = p.tag.rpartition("}")[2]
        current_class = p.attrib.get("class")
        if (
            # has sementic meaning, do not merge
            (current_tag != "span") or
            # not the same, don't merge
            (previous_tag != current_tag or previous_class != current_class)
            ):
            if p.getchildren():
                # recursively merge tags
                p = merge_tag(p)
            new_root.append(p)
            previous_node, previous_tag, previous_class = p, current_tag, current_class
        else:
            # add content of current into previous
            # "foo<p>bar</p>baz" -> p.text="foo", p.child.text = "bar", p.child.tail = "baz"
            if p.text:
                if previous_node.getchildren():
                    # need to add at the end of last child
                    last_child = previous_node.getchildren()[-1]
                    last_child.tail = (last_child.tail or '') + p.text
                else:
                    # has no children, add to content
                    previous_node.text += p.text
            for child in p.getchildren():
                if child.getchildren():
                    # recursively merge tags
                    child = merge_tag(child)
                previous_node.append(child)
    return new_root



def merge_duplicated_tags():
    """ if two same tags with same class follow each other, merge them"""
    parser = etree.XMLParser(ns_clean=True, recover=True, encoding="utf-8")
    for filename in sorted(Path("src/OEBPS/sections/").glob("section*.xhtml")):
        print("MERGING", filename)
        with filename.open() as f:
            fcontent = f.read()
        root, body = get_body(fcontent)

        new_body = merge_tag(body)
        replace_body(root, new_body)

        # move to another repository for comparison
        new_filename = filename.parent.parent / "new_sections" / filename.name
        with new_filename.open("w") as f:
            # save everything computed so far
            f.write(etree.tostring(root, encoding="utf-8").decode())


if __name__ == "__main__":
    merge_duplicated_tags()
    # titles = split_sections()
    # write_content()
    # generate_toc(titles)
