import jq
import json
from . import trapi_tools as tools
from graphwerk import trapimsg
from . import utils

def summarize_trapi_response(trapi_response_msg: dict, idx_range: range, pub_cutoff=5) -> str:
    orig_msg = trapi_response_msg['fields']['data']['message']
    orig_kg = orig_msg['knowledge_graph']
    orig_ag = orig_msg['auxiliary_graphs']
    orig_qg = orig_msg['query_graph']
    retval = ''
    object_node_id, object_node_data = tools.get_object_node_data(orig_qg, orig_kg)
    query_summmary = create_query_summary(object_node_id, object_node_data)
    res_nodes = {} # The node section is universal, not per-result

    per_result = ''
    counter = 1
    for i in idx_range:
        cur_res = orig_msg['results'][i]
        subject_id = cur_res['node_bindings']['sn'][0]['id']
        subject_name = orig_kg['nodes'][subject_id]['name']
        per_result += f"** Result {counter}: {subject_name}\n"
        res_edges = {}
        res_sgs = {}
        trapimsg.collect_edges_and_sgs_for_res_elem(cur_res, orig_kg, orig_ag, res_edges, res_sgs)
        trapimsg.collect_nodes_for_edge_collection(res_edges, orig_kg, res_nodes)
        presum_edges = tools.create_edge_presummary_raw_data(res_edges, res_nodes, pub_cutoff)
        presum_nodes = tools.create_node_presummary_raw_data(res_nodes)
        per_result += utils.create_edge_data_summary(presum_edges, 1) + '\n'
        counter += 1

    return f"""{query_summmary}

{utils.create_node_data_summary(presum_nodes)}

* EDGE/REASONING INFORMATION (KNOWLEDGE GRAPHS)

Each item below specifies a biological entity that is claimed to treat the disease referred to in the query, and
provides the associated reasoning/knowledge graph.

{per_result.rstrip()}
"""


def create_query_summary(object_id: str, object_data: dict) -> str:
    jqprog = jq.compile('.attributes[] | select(.attribute_type_id == "biothings_annotations") | .value[0].disease_ontology.def')
    name = object_data['name']
    definition = jqprog.input_text(json.dumps(object_data)).first()
    if definition:
        definition = f"A brief definition of this disease: {definition}"
    retval = f"""* QUERY INFORMATION

The following data is a response to the query: "What drugs may treat the disease: '{name}'.
{definition}
"""
    return retval
