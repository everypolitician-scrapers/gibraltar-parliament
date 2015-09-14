# -*- coding: utf-8 -*-
from datetime import datetime
import re

import bs4
import scraperwiki


def parse_date(d):
    if d == "to date":
        return None
    if len(d) == 4:
        return d
    return str(datetime.strptime(d, "%d %B %Y").date())

url = "http://www.parliament.gi/history/composition-of-parliament"
r = scraperwiki.scrape(url)
soup = bs4.BeautifulSoup(r, "html.parser")

term_re = re.compile(r"(?:Footnote:|([^ ]+ (?:House of Assembly|Gibraltar Parliament)) \((.*?) . (.*?)\))")
position_re = re.compile(r"(?:GOVERNMENT|OPPOSITION|SPEAKER|CLERK)")
name_re = re.compile(r"The Hon .*$")
name_and_role_re = re.compile(ur".*?The Hon (.*?)(?: (?:-|–) (.*))?$")
name_and_role_first_term_re = re.compile(r"(.*?)(?:, ((?:Minister|Chief Minister|Attorney General|Financial & Development Secretary|Leader).*))?$")

terms = soup.find_all(text=term_re)
id_ = 0
terms_list = []
for term in terms:
    term_name, start_date, end_date = term_re.match(term).groups()
    if not term_name:
        # this is just here to deal with the weird bit in
        # the Eighth House of Assembly
        continue
    start_date = parse_date(start_date)
    end_date = parse_date(end_date)
    id_ += 1
    terms_list.append({
        "id": id_,
        "name": term_name,
        "start_date": start_date,
        "end_date": end_date,
    })

scraperwiki.sqlite.save(["id"], terms_list, "terms")
terms_dict = {x["name"]: x for x in terms_list}

members = soup.find_all(text=name_re)

data_list = []
for member in members:
    position = member.find_previous(text=position_re)
    if position in ["SPEAKER", "CLERK"]:
        continue
    parliament = member.find_previous(text=term_re)
    if parliament.startswith("Footnote"):
        # this is just here to deal with the weird bit in
        # the Eighth House of Assembly
        continue
    term_name = term_re.match(parliament).group(1)
    term_id = terms_dict[term_name]["id"]
    name, role = name_and_role_re.match(member.strip()).groups()
    if term_name == "First House of Assembly":
        name, role = name_and_role_first_term_re.match(name).groups()
    data_list.append({
        "name": name.strip(),
        "area": None,  # we don't have this data
        "group": None,  # we don't have this data
        "term": term_id,
        "start_date": "",
        "end_date": "",
        "role": role.strip() if role else None,
        "side": position.title(),
    })

scraperwiki.sqlite.save(["name", "term"], data_list, "data")
