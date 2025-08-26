import re

### Contains functions used by both TRAPI format and UI format summarizers
def sanitize_categories(cats: list) -> list:
    eliminate = ('biolink:NamedThing', 'biolink:BiologicalEntity', 'biolink:ThingWithTaxon',
                   'biolink:PhysicalEssence', 'biolink:PhysicalEssenceOrOccurrent')
    return [cat for cat in cats if cat not in eliminate]


def create_node_data_summary(node_presummaries: list[dict]) -> str:
    retval = """* NODE INFORMATION

| <ENTITY NAME> | <CATEGORIES> | <CURIE> |\n"""
    for n in node_presummaries:
        retval += f"| {n['name']} | {", ".join(re.sub(r"^biolink:", "", a) for a in n['categories'])} | {n['curie']} |\n"
    return retval;


def create_edge_data_summary(edge_presummaries: list[dict], skip=0) -> str:
    retval = '| <SUBJECT> | <PREDICATE> | <OBJECT> | <PUBMED IDS> | <CLINICAL TRIAL IDS> |\n'
    for e in edge_presummaries[skip:]: # (Sometimes) try skipping the first element, which is the main "treats" edge
        retval += f"| {e['subject_name']} | {re.sub(r"^biolink:", '', e['predicate'])} | {e['object_name']} | "
        retval += ",".join(e['pub_ids']) + " | " + ",".join(e['ct_ids']) + " |\n"
    return retval
