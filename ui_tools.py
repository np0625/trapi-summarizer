import jq
import json
import sys

_result_fields = ('id', 'subject', 'drug_name', 'paths')
_result_jq_expr = jq.compile(f"{{ {','.join(_result_fields)} }}")

_node_fields = ('curies', 'names', 'types')
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
    for p_id in paths:
        sg = orig_paths[p_id]['subgraph']
        print(sg)
        for edge_id in sg[1::2]: # Every other element starting at idx=1 gives you just the edges
            print(json.dumps(_edge_jq_expr.input_value(orig_edges[edge_id]).first()))
    return result_elem

def collect_edges_for_path(path_id, paths, edges):
    pass

print(json.dumps((shrink_ui_payload(infile, idx))))

