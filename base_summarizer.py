import re
import jq
import json
import summarizer_tools as st
from graphwerk import trapimsg

def summarize_trapi_response(trapi_response_msg: dict, idx_range: range) -> str:
    orig_msg = trapi_response_msg['fields']['data']['message']
    orig_kg = orig_msg['knowledge_graph']
    orig_ag = orig_msg['auxiliary_graphs']
    orig_qg = orig_msg['query_graph']
    retval = ''
    object_node_id, object_node_data = st.get_object_node_data(orig_qg, orig_kg)
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
        presum_edges = st.create_edge_presummary_raw_data(res_edges, res_nodes)
        presum_nodes = st.create_node_presummary_raw_data(res_nodes)
        per_result += create_edge_data_summary(presum_edges) + '\n'
        counter += 1

    return f"""{query_summmary}

{create_node_data_summary(presum_nodes)}

* EDGE/REASONING INFORMATION (KNOWLEDGE GRAPHS)

Each item below specifies a biological entity that is claimed to treat the disease referred to in the query, and
provides the associated reasoning/knowledge graph.

{per_result.rstrip()}
"""


def create_node_data_summary(node_presummaries: list[dict]) -> str:
    retval = """* NODE INFORMATION

   | <entity name> | <categories, comma separated> |\n\n"""
    for n in node_presummaries:
        retval += f"| {n['name']} | {", ".join(re.sub(r"^biolink:", "", a) for a in n['categories'])} |\n"
    return retval;


def create_edge_data_summary(edge_presummaries: list[dict]) -> str:
    retval = '| <subject> | <predicate> | <object> |\n'
    for e in edge_presummaries[1:]: # Try skipping the first element, which is the main "treats" edge
        retval += f"| {e['subject_name']} | {re.sub(r"^biolink:", '', e['predicate'])} | {e['object_name']} |\n"
    return retval

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
