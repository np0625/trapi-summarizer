import re
import jq
import json
import summarizer_tools as st
from graphwerk import trapimsg

def create_response(trapi_response_msg: dict, idx_range: range) -> str:
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
        per_result += f"### Result {counter}: {subject_name}\n"
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

## Section 2: Knowledge Graph, or Edge Information

Each item below specifies a biological entity that is claimed to treat the disease referred to in the query.

{per_result}
"""



def system_instructions():
    return """You are an expert at understanding and summarizing biomedical information and reasoning data. You are able
to supplement the provided information with your own knowledge if strictly necessary and safe to do so. You must be
exceedingly careful to only include information that is guaranteed to be correct. Your audience is composed of highly
knowledgeable researchers (PhDs) in the biomedical space.

Examine the data provided in order to create sophisticated, scientifically sound summaries that will capture the
salient points of the results in an accurate manner.

Each data set will be in answer to specific question, such as "What drugs may treat disease X?". This question will be
provided to you up front, followed by the per-result specifics. Use all the data provided to determine relationships and
patterns in the query results, then summarize them in a manner appropriate for the expert biomedical audience
mentioned above.

Work hard to find interesting patterns, mechanisms, commonalities, and so on -- anything that is supportable and will
tell a researcher what is interesting and salient about the group of results.
"""

def create_node_data_summary(node_presummaries: list[dict]) -> str:
    retval = """## Section 1: Node information

Here are the biological entities involved. Reference this information when constructing the summary. Supplement this information
with your own training data when producing the summary /if/ it will help in producing a better summary,
but take GREAT care to remain within known verified scientific facts. Do not speculate or use
popular knowledge if you do not have scientific-grade sources. Note: all categories belong to the Biolink data model.\n

The data is presented in the form:
   | <entity name> | <categories, comma separated> |\n\n"""
    for n in node_presummaries:
        retval += f"| {n['name']} | {", ".join(re.sub(r"^biolink:", "", a) for a in n['categories'])} |\n"
    return retval;


def create_edge_data_summary(edge_presummaries: list[dict]) -> str:
    retval = '| subject | predicate | object |\n'
    for e in edge_presummaries[1:]: # Try skipping the first element, which is the main "treats" edge
        retval += f"| {e['subject_name']} | {re.sub(r"^biolink:", '', e['predicate'])} | {e['object_name']} |\n"
    return retval

def create_query_summary(object_id: str, object_data: dict) -> str:
    jqprog = jq.compile('.attributes[] | select(.attribute_type_id == "biothings_annotations") | .value[0].disease_ontology.def')
    name = object_data['name']
    definition = jqprog.input_text(json.dumps(object_data)).first()
    if definition:
        definition = f"A brief definition of this disease: {definition}"
    retval = f"""# Introduction

The following data is a response to the query: "What drugs may treat the disease: '{name}'.
{definition}

The data is organized into two large sections. The first section is a glossary of each biomedical entity involved and its biolink categories.
Use these as reference material when constructing your summary, particularly to disambiguate terms if necessary. Feel free to
supplement entity information with your own knowledge.

The second section is a list of the "knowledge graphs" of individual results in the response. Each result identifies
the particular drug or molecule that may treat the disease, along with reasoning to support this conclusion. The reasoning
is presented as sequences of triples,  that indicates relationships between biological entities that ultimately prove or
support the primary query referenced above. Follow the relationships with great care, remembering that they may not be presented
in any particular order. You must determine and understand the transitive relationships between the individual triples in order
to grasp the overall line of reasoning, so that you can eventually summarize it. Note: all predicates belong to the Biolink data model.

Each result's graph of relationships is presented in this form:
    | <subject> | <predicate> | <object> |

So in conclusion, carefully study all this data, then provide a summary as defined in the project-wide instructions.
"""
    return retval
