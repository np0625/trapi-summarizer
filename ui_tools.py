import jq
import json
import sys
import utils

_result_fields = ('id', 'subject', 'drug_name', 'paths')
_result_jq_expr = jq.compile(f"{{ {','.join(_result_fields)} }}")

_node_fields = ('types')
_node_jq_expr = jq.compile(f"{{ {','.join(_node_fields)} }}")

_edge_fields = ('support', 'subject', 'predicate', 'object', 'publications')
_edge_jq_expr = jq.compile(f"{{ {','.join(_edge_fields)} }}")


with open(sys.argv[1], 'r') as f:
    infile =json.load(f)

idx = int(sys.argv[2])

def shrink_ui_payload(payload, idx):
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
    for p_id in paths:
        collect_edges_for_path(p_id, orig_paths, orig_edges, edge_collection)
    result_elem['edges'] = edge_collection
    result_elem['nodes'] = collect_nodes_for_edge_collection(orig_nodes, edge_collection, node_collection)
    return result_elem

def collect_edges_for_path(path_id, orig_paths, orig_edges, edge_collection=[]):
    sg = orig_paths[path_id]['subgraph']
    for edge_id in sg[1::2]: # Every other element starting at idx=1 gives you just the edges
        edge_info = _edge_jq_expr.input_value(orig_edges[edge_id]).first()
        edge_collection.append(edge_info)
        for p_id in edge_info['support']:
            collect_edges_for_path(p_id, orig_paths, orig_edges, edge_collection)
    return edge_collection

def collect_nodes_for_edge_collection(orig_nodes, edge_collection, node_collection=[], category_cutoff=5):
    curies = set()
    for e in edge_collection:
        subject_curie = e['subject']
        object_curie = e['object']
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

print(json.dumps((shrink_ui_payload(infile, idx))))

