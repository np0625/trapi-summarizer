import ui_tools
import utils

def create_ui_summary(payload, idx):
    presummary = ui_tools.create_ui_presummary(payload, idx)
    node_summary = utils.create_node_data_summary(presummary['nodes'])
    edge_summary = utils.create_edge_data_summary(presummary['edges'], 1)

    return f"""{create_query_summary(payload)}

{node_summary}


* EDGE/REASONING INFORMATION (KNOWLEDGE GRAPHS)

Each item below specifies a biological entity that is claimed to treat the disease referred to in the query, and
provides the associated reasoning/knowledge graph.

{edge_summary}

"""

def create_query_summary(payload):
    disease_curie = payload['disease']
    disease_name = payload['data']['nodes'][disease_curie]['names'][0]
    disease_def = payload['data']['nodes'][disease_curie]['descriptions'][0]
    if disease_def:
        disease_def = f"A brief definition of this disease: {disease_def}"
    retval = f"""* QUERY INFORMATION

The following data is a response to the query: "What drugs may treat the disease: '{disease_name}'".
{disease_def}
"""
    return retval

if __name__ == "__main__":
    import sys
    import json
    with open(sys.argv[1], 'r') as f:
        infile =json.load(f)
    idx = int(sys.argv[2])
    infile['disease'] = 'MONDO:0005147'
    print(create_ui_summary(infile, idx))
