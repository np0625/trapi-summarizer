import re
from graphwerk import trapimsg

"""Get node data for the CURIE identified by the QG as the object of the query
"""
def get_object_node_data(qg: dict, kg: dict, node_name='on') -> dict:
    object_id = qg['nodes'][node_name]['ids'][0]
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
def create_edge_presummary_raw_data(edges: list[dict], node_collection: dict, pub_cutoff=10) -> list[dict]:
    uniq = extract_unique_edges(edges.values())
    return [
        {
            'subject_curie': edge['subject'],
            'predicate': edge['predicate'],
            'object_curie': edge['object'],
            'subject_name': node_collection[edge['subject']]['name'],
            'object_name': node_collection[edge['object']]['name'],
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

