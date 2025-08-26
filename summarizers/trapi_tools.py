import re
import jq
from graphwerk import trapimsg
import jq_tools
from . import common_utils as cu

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
    retval = jq_tools.try_first('.attributes[] | select(.attribute_type_id == "biolink:publications") | .value', edge, [])
    return retval[:cutoff]

def extract_clinical_trials(edge: dict, cutoff=100):
    cts = jq_tools.try_all('.attributes[] | select(.attribute_type_id == "biolink:supporting_study") | .value', edge, [])
    retval = [ct for ct in cts if re.match(r'^NCT[0-9]+$', str(ct))][:cutoff]
    return retval

"""Given the list of all edge data corresponding to the targeted results, return
only the unique triples and the precise fields that will be used to generate textual summaries.
"""
def create_edge_presummary_raw_data(edges: list[dict], node_collection: dict, pub_cutoff=5) -> list[dict]:
    uniq = extract_unique_edges(edges.values())
    return [
        {
            'subject_curie': edge['subject'],
            'predicate': edge['predicate'],
            'object_curie': edge['object'],
            'subject_name': node_collection[edge['subject']]['name'],
            'object_name': node_collection[edge['object']]['name'],
            'pub_ids': extract_edge_publications(edge, pub_cutoff),
            'ct_ids': extract_clinical_trials(edge)
        }
        for edge in uniq
    ]

def create_node_presummary_raw_data(nodes: list[dict], category_cutoff=5) -> list[dict]:
    return [
        {
            'name': val['name'],
            'categories': cu.sanitize_categories(val.get('categories', []))[:category_cutoff],
            'curie': key
        } for key, val in nodes.items()
    ]

