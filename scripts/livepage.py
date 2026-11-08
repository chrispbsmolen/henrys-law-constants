"""Parse a species page of the live henrys-law.org site (read-only, saved HTML)."""
import re

from htmltext import to_text


def _cells(tr):
    return [c.strip() for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S | re.I)]


def parse_species_page(text):
    page = {}
    m = re.search(r"<H1><A href=\"/henry/browse/\">.*?</H1>", text, re.S)
    crumbs = re.split(r"&rarr;", m.group(0))
    page["name_html"] = crumbs[-1].replace("</H1>", "").strip()
    page["subcategory"] = to_text(crumbs[-2])
    page["category"] = to_text(crumbs[-3])
    for label, key in (("FORMULA:", "formula_html"), ("CAS RN</a>:", "casrn"), ("InChIKey</a>:", "inchikey"),
                       ("TRIVIAL NAME", "trivial_html")):
        m = re.search(re.escape(label) + r".*?</TD>\s*<TD>(.*?)</TD>", text, re.S | re.I)
        page[key] = m.group(1).strip() if m else ""
    # data rows
    m = re.search(r"\[mol/\(m<sup>3</sup>Pa\)\]</TH>.*?</TR>(.*?)</TABLE>", text, re.S)
    rows = []
    for tr in re.findall(r"<tr style=\"background-color:#(?:eee|fff);\">(.*?)</tr>", m.group(1), re.S):
        c = _cells(tr)
        rows.append(dict(hominus=c[0], mindhr=c[1], quotation=c[2], htype=c[3],
                         note_numbers=[int(x) for x in re.findall(r"(\d+)\)", c[4])]))
    page["rows"] = rows
    # reference list: <!-- bibtexkey --> <!-- quotation --> bibliography
    refs = {}
    for key, quot, bib in re.findall(r"<LI>\s*<!-- (\S+) -->\s*<!-- (.*?) -->\s*(.*?)\s*(?=<LI>|</UL>)", text, re.S):
        refs[quot.replace("&amp;", "&")] = dict(bibtexkey=key, bibliography=bib)
    page["refs"] = refs
    # notes
    notes = {}
    for num, body in re.findall(r"<TD align=\"right\">(\d+)\)</TD>\s*<TD>(.*?)</TD>", text, re.S):
        notes[int(num)] = body.strip()
    page["notes"] = notes
    return page
