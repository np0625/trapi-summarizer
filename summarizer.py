import re
from graphwerk import trapimsg

"""Get node data for the CURIE identified by the QG as the object of the query
"""
def get_object_node(qg: dict, kg: dict) -> dict:
    object_id = qg['nodes']['on']['ids'][0]
    return (object_id, kg['nodes'][object_id])

"""While edge_ids in a KG are unique, the subject-object-predicate triple often is not.
There may be good reasons for this that we eventually need to pay attention to: we may
need to use a more complex definition of uniqueness. But for MVP, let's go with
SPO-uniqueness
"""
def extract_unique_edges(edges: list[dict]) -> list[dict]:
    seen = set()
    uniq = []
    for e in edges:
        triple = (e['subject'], e['predicate'], e['object'])
        if triple not in seen:
            seen.add(triple)
            uniq.append(e)
    return uniq


"""If the edge has supporting publications in its attributes, grab them.
# Note: there is no way to tell which pubs are more important; so we just grab the first N
"""
def extract_edge_publications(edge: dict, cutoff):
    pubs = [
        a['value'] for a in edge.get('attributes', [])
        if a['attribute_type_id'] == 'biolink:publications'
    ]
    if len(pubs) > 0:
        return pubs[0][:cutoff] # [0] because the value is itself an array
    else:
        return []

"""Given the list of all edge data corresponding to the targeted results, return
only the unique triples and the precise fields that will be used to generate textual summaries.
"""
def create_edge_presummary_raw_data(edges: list[dict], pub_cutoff=10) -> list[dict]:
    uniq = extract_unique_edges(edges.values())
    return [
        {
            'subject': edge['subject'],
            'predicate': edge['predicate'],
            'object': edge['object'],
            'pub_ids': extract_edge_publications(edge, pub_cutoff)
        }
        for edge in uniq
    ]

def create_node_presummary_raw_data(nodes: list[dict], object_node: str, category_cutoff=5) -> list[dict]:
    retval = []
    for key, val in nodes.items():
        if key == object_node:
            continue
        elem = {
            'name': val['name'],
            'categories': val.get('categories', [])[:category_cutoff],
            'description': ''
        }
        descr = next((a['value'] for a in val.get('attributes', []) if a['attribute_type_id'] == 'biolink:description'), None)
        if descr:
            elem['description'] = descr
        else:
            biothings_annotations = next((a['value'] for a in val.get('attributes', []) if a['attribute_type_id'] == 'biothings_annotations'), None)
            if biothings_annotations:
                descr = biothings_annotations[0].get('unii', {}).get('ncit_description', None)
                if descr:
                    elem['description'] = descr
        retval.append(elem)
    return retval

def create_node_section(node_presummaries: list[dict]) -> str:
    retval = """
Here are the biological entities involved.

Reference this information when constructing the summary. Supplement this information
with your own training data when producing the summary /if/ it will help in producing a better summary,
but take GREAT care to remain within known verified scientific facts. Do not speculate or use
popular knowledge if you do not have scientific-grade sources. Note: all categories belong to the Biolink data model.\n

The data is presented in the form:
   | <entity name> | <categories> | <description if available> |\n\n"""
    for n in node_presummaries:
        retval += f"| {n['name']} | {", ".join(re.sub(r"^biolink:", "", a) for a in n['categories'])} | {n['description']} |\n"
    retval += '-' * 70
    return retval


def create_edge_section(edge_presummaries: list[dict], node_collection: dict) -> str:
    retval = """
Here is the per-result reasoning data, in the form of sequences of triples,  that indicates relationships
between biological entities that ultimately prove or support the primary query referenced above. Follow the
relationships with great care, remembering that they may not be presented in any particular order. You must
determine and understand the transitive relationships between the individual triples in order to grok the
overall line of reasoning, so that you can eventually summarize it. Note: all predicates belong to the Biolink data model.

Each result's graph of relationships is presented in this form:
    | <subject> | <predicate> | <object> |\n\n"""
    for e in edge_presummaries:
        retval += f"| {node_collection[e['subject']]['name']} | {re.sub(r"^biolink:", '', e['predicate'])} | {node_collection[e['object']]['name']} |\n"
    retval += '-' * 70
    return retval