import jq
from . import utils

_result_fields = ('id', 'subject', 'drug_name', 'paths')
_result_jq_expr = jq.compile(f"{{ {','.join(_result_fields)} }}")

_node_fields = ('types')
_node_jq_expr = jq.compile(f"{{ {','.join(_node_fields)} }}")

_edge_fields = ('support', 'subject', 'predicate', 'object', 'publications')
_edge_jq_expr = jq.compile(f"{{ {','.join(_edge_fields)} }}")



# Note: for now this assumes creating a single element summary.
# This is different from the trapi_summarizer which can summarize a range of result elements
def create_ui_presummary(payload, idx):
    retval = {}
    data = payload['data']
    orig_results = data['results']
    orig_paths = data['paths']
    orig_nodes = data['nodes']
    orig_edges = data['edges']
    result_elem = _result_jq_expr.input_value(orig_results[idx]).first()
    paths = result_elem['paths']
    edge_collection = []
    node_collection = []
    # The ordering of the following 3 operations is important:
    # First collect all the edges, storing the curies for subject/object in the [subject|object]_name field
    # Then collect all the node info for those subjects/objects
    # THEN replace the curies with their names in the edge data
    for p_id in paths:
        collect_edges_for_path(p_id, orig_paths, orig_edges, edge_collection)
    result_elem['nodes'] = collect_nodes_for_edge_collection(orig_nodes, edge_collection, node_collection)
    replace_curies_with_names(edge_collection, orig_nodes)
    result_elem['edges'] = edge_collection
    return result_elem

def flatten_publication_info(pubinfo: dict) -> list:
    retval = []
    for publist in pubinfo.values():
        for item in publist:
            retval.append(item['id'])
    return retval

def collect_edges_for_path(path_id, orig_paths, orig_edges, edge_collection=[], pub_cutoff=5):
    sg = orig_paths[path_id]['subgraph']
    for edge_id in sg[1::2]: # Every other element starting at idx=1 gives you just the edges
        edge_info = _edge_jq_expr.input_value(orig_edges[edge_id]).first()
        edge_collection.append({
            'subject_name': edge_info['subject'],
            'object_name': edge_info['object'],
            'predicate': edge_info['predicate'],
            'pub_ids': flatten_publication_info(edge_info['publications'])[:pub_cutoff]
        })
        for p_id in edge_info['support']:
            collect_edges_for_path(p_id, orig_paths, orig_edges, edge_collection)
    return edge_collection

def collect_nodes_for_edge_collection(orig_nodes, edge_collection, node_collection=[], category_cutoff=5):
    curies = set()
    for e in edge_collection:
        subject_curie = e['subject_name']
        object_curie = e['object_name']
        curies.add(subject_curie)
        curies.add(object_curie)

    for c in curies:
        orig_node = orig_nodes[c]
        new_node = {
            'categories': utils.sanitize_categories(orig_node.get('types', []))[:category_cutoff],
            'name': orig_node['names'][0],
            'curie': c
        }
        node_collection.append(new_node)
    return node_collection

def replace_curies_with_names(edge_collection, orig_nodes):
    for e in edge_collection:
        e['subject_name'] = orig_nodes[e['subject_name']]['names'][0]
        e['object_name'] = orig_nodes[e['object_name']]['names'][0]

if __name__ == "__main__":
    import json
    import sys
    with open(sys.argv[1], 'r') as f:
        infile =json.load(f)
    idx = int(sys.argv[2])
    infile['disease'] = 'MONDO:0005147'
    print(json.dumps((create_ui_presummary(infile, idx))))

