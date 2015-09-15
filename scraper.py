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

suffixes = ["CBE", "CMG", "ED", "JP", "MA", "MBE", "MVO", "OBE", "QC", "RD"]
name_and_suffixes_re = re.compile('^(.*?),?((?: (?:{}),?)*)$'.format('|'.join(''.join(y + '\.?' for y in x) for x in suffixes)))

prefixes = ["Dr\.?", "Lt\.? Col\.?", "Lt-Col", "Major", "Miss", "Mrs", "Sir"]
name_and_prefixes_re = re.compile('^(?:({}) )?(.*)$'.format('|'.join(prefixes)))

term_re = re.compile(r"^(?:Footnote:|([^ ]+ (?:House of Assembly|Gibraltar Parliament)) \((.*?) . (.*?)\))")
position_re = re.compile(r"(?:GOVERNMENT|OPPOSITION|SPEAKER|CLERK)")
name_re = re.compile(r"The Hon .*$")
name_and_role_re = re.compile(ur"^The Hon (.*?)(?: (?:-|–) (.*))?$")
name_and_role_first_term_re = re.compile(r"^The Hon (.*?)(?:, ((?:Minister|Chief Minister|Attorney General|Financial & Development Secretary|Leader).*))?$")

terms = soup.find_all(text=term_re)
id_ = 0
terms_list = []
for term in terms:
    term_name, start_date, end_date = term_re.search(term).groups()
    if not term_name:
        # this is just here to deal with the weird bit in
        # the Eighth House of Assembly
        continue
    start_date = parse_date(start_date)
    end_date = parse_date(end_date)
    if term_name == "Tenth Gibraltar Parliament":
        # this is to deal with the name change from
        # House of Assembly to Gibraltar Parliament
        terms_list[-1]["end_date"] = end_date
        continue
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

counter = 0
member_dict = {}
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
    if parliament.startswith("Tenth Gibraltar Parliament"):
        # this is to deal with the name change from
        # House of Assembly to Gibraltar Parliament
        continue
    term_name = term_re.search(parliament).group(1)
    term_id = terms_dict[term_name]["id"]
    if term_name == "First House of Assembly":
        # The name and role are split by a comma in the first assembly.
        name, role = name_and_role_first_term_re.search(member.strip()).groups()
    else:
        name, role = name_and_role_re.search(member.strip()).groups()
    name, honorific_suffix = name_and_suffixes_re.search(name).groups()
    honorific_suffix = honorific_suffix.strip().replace(',', '').replace('.', '')
    honorific_prefix, name = name_and_prefixes_re.search(name).groups()
    # strip dots out of all names; titlecase. Sorry
    name = name.replace('.', '').title()
    # we mostly do this for JJ Bossano, whose name appears various different ways
    name = re.sub(r"^([A-Z])([A-Z]) ", r"\1 \2 ", name)
    # strip out middle initials
    simple_name = re.sub(r"^(.+? )(?:[A-Z] )+", r"\1", name)
    if simple_name in member_dict:
        # We guess two people are the same if their names appear to match...
        id_, stored_name = member_dict[simple_name]
        if len(stored_name) == len(name) and name != stored_name:
            # but not if they have mismatching middle initials
            counter += 1
            id_ = counter
            member_dict[simple_name] = id_, name
    else:
        counter += 1
        id_ = counter
        member_dict[simple_name] = id_, name
    data_list.append({
        "id": id_,
        "name": name,
        "area": None,  # we don't have this data
        "group": None,  # we don't have this data
        "term": term_id,
        "start_date": "",
        "end_date": "",
        "honorific_prefix": honorific_prefix,
        "honorific_suffix": honorific_suffix,
        "role": role.strip() if role else None,
        "side": position.title(),
    })

scraperwiki.sqlite.save(["id", "term"], data_list, "data")
