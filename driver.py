import json
import argparse
import os
from graphwerk import trapimsg
import summarizer

def load_file(path: str) -> dict:
    with open(path, 'r') as f:
        data = json.load(f)
    return data

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Trim down TRAPI response files')
    parser.add_argument('-n', type=int, default=100, help='Number of results to include (default: 100)')
    parser.add_argument('-i', '--input', required=True, help='Input JSON file path')
    parser.add_argument('--start', type=int, help='Starting index in results array')
    parser.add_argument('--end', type=int, help='Ending index (exclusive) in results array')
    parser.add_argument('--list', type=str, help='Comma-separated list of indices, e.g. --list=9,18,202')
    args = parser.parse_args()

    # Validate arguments
    if args.end is not None and args.start is None:
        parser.error("--end cannot be specified without --start")

    if args.end is not None and args.start is not None:
        if int(args.end) < int(args.start):
            parser.error("--end must be >= --start")

    return args

# TODO: filter this range to cap at limit of len(results)
def get_index_range(args) -> tuple[int, ...] | range:
    if args.list is not None:
        return tuple(int(num) for num in args.list.strip(',').split(',') if num.strip() != '')

    if args.start is None:
        return range(0, args.n) # note: not n-1, because that's how ranges work

    if args.end is None:
        return range(args.start, args.start + args.n) # ditto
    else:
        return range(args.start, args.end + 1)

def main():
    args = parse_args()
    orig = load_file(args.input)
    idx_range = get_index_range(args)

    orig_msg = orig['fields']['data']['message']
    orig_kg = orig_msg['knowledge_graph']
    orig_ag = orig_msg['auxiliary_graphs']
    orig_qg = orig_msg['query_graph']

    res_zero = orig_msg['results'][idx_range[0]]

    res_edges = {}
    res_sgs = {}
    res_nodes = {}
    trapimsg.collect_edges_and_sgs_for_res_elem(res_zero, orig_kg, orig_ag, res_edges, res_sgs)
    trapimsg.collect_nodes_for_edge_collection(res_edges, orig_kg, res_nodes)
    object_node_id, object_node_data = summarizer.get_object_node(orig_qg, orig_kg)
    retval = {
        'nodes': res_nodes,
        'edges': res_edges
    }
    # print(json.dumps(retval))
    #print(json.dumps(res_edges))
    # print(json.dumps(res_nodes))
    # print(f"num all edges: {len(res_edges.keys())}")
    # uniq_edges = summarizer.extract_unique_edges(res_edges.values())
    #print(json.dumps(uniq_edges))
    # print(f"num uniq edges: {len(uniq_edges)}")
    subject_node = summarizer.get_object_node(orig_qg, orig_kg)
    # print(json.dumps(subject_node))
    presum_edges = summarizer.create_edge_presummary_raw_data(res_edges)
    presum_nodes = summarizer.create_node_presummary_raw_data(res_nodes, object_node_id)
    #print(json.dumps(presum_nodes))
    #print(presum_edges)
    # print(presum_nodes)
    print(summarizer.create_node_section(presum_nodes))
    print(summarizer.create_edge_section(presum_edges, res_nodes))


if __name__ == '__main__':
    main()
