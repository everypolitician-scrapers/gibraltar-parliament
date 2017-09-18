# -*- coding: utf-8 -*-
from datetime import datetime
import re

import bs4
import scraperwiki


def parse_date(d):
    if d == "date":
        return None
    if len(d) == 4:
        return d
    return str(datetime.strptime(d, "%d %B %Y").date())

def merge_members(data_list):
    # strip out middle initials
    abbreviate = lambda x: re.sub(r"^(.+? )(?:[A-Z] )+", r"\1", x)

    if 'data' in scraperwiki.sqlite.show_tables():
        output_list = scraperwiki.sqlite.select("* FROM `data`")
        for y in output_list:
            y['short_name'] = abbreviate(y['name'])
    else:
        output_list = []
    initial_len = len(output_list)

    id_ = 0
    for x in data_list:
        x = dict(x)
        x['short_name'] = abbreviate(x['name'])
        for y in reversed(output_list):
            if x['name'] == y['name']:
                x['id'] = y['id']
                output_list.append(x)
                break
            if x['short_name'] == y['short_name']:
                if x['short_name'] == x['name'] or y['short_name'] == y['name']:
                    print "{x_name} (term {x_term}) is probably the same person as {y_name} (term {y_term})".format(
                        x_name=x['name'],
                        x_term=x['term'],
                        y_name=y['name'],
                        y_term=y['term'],
                    )
                    x['id'] = y['id']
                    x['name'] = y['name']
                    output_list.append(x)
                    break
        if 'id' not in x:
            id_ += 1
            x['id'] = id_
            output_list.append(x)

    for y in output_list:
        del y['short_name']

    return output_list[initial_len:]

url = "http://www.parliament.gi/history/composition-of-parliament"
r = scraperwiki.scrape(url)
soup = bs4.BeautifulSoup(r, "html.parser")

suffixes = ["CBE", "CMG", "ED", "JP", "MA", "MBE", "MVO", "OBE", "QC", "RD"]
name_and_suffixes_re = re.compile(r"^(.*?),?((?: (?:{}),?)*)$".format('|'.join(''.join(y + '\.?' for y in x) for x in suffixes)))

prefixes = ["Dr\.?", "Lt\.? Col\.?", "Lt-Col", "Major", "Miss", "Mrs", "Ms", "Sir"]
name_and_prefixes_re = re.compile(r"^(?:({}) )?(.*)$".format('|'.join(prefixes)))

term_re = re.compile(r"^(?:Footnote:|([^ ]+ (?:House of Assembly|Gibraltar Parliament)) \((.*?) (?:.|to) (.*?)\))")
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
        member = member.replace(u'\xa0', ' ').strip()
        name, role = name_and_role_re.search(member).groups()
    name, honorific_suffix = name_and_suffixes_re.search(name).groups()
    honorific_suffix = honorific_suffix.strip().replace(',', '').replace('.', '')
    honorific_prefix, name = name_and_prefixes_re.search(name).groups()
    # strip dots out of all names. Sorry
    name = name.replace('.', '')
    # we mostly do this for JJ Bossano, whose name appears
    # various different ways
    name = re.sub(r"^([A-Z])([A-Z]) ", r"\1 \2 ", name)
    data_list.append({
        "name": name.title(),
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

data_list = merge_members(data_list)

scraperwiki.sqlite.save(["id", "term"], data_list, "data")
