import json
import gene_info_client
import jq

# constants
KEY_NMF_PIGEAN_FACTORS = "pigean-factor"
KEY_NMF_DATA = "data"

def get_genes_from_trapi(trapi_response_message):
    # Extracts a list of genes from a trapi response
    nodes = jq.compile('.fields.data.message.knowledge_graph.nodes').input_value(trapi_response_message).first()
    genes = {key: value.get('name', '') for key, value in nodes.items()
             if "biolink:Gene" in value.get("categories", [])}
    return genes


# nmf: json response from API
def get_groupings_from_nmf(nmf, target: str) -> dict:
    retval = {item["factor"]: item.get(target, '').split(";") for item in nmf.get(KEY_NMF_PIGEAN_FACTORS, {}).get(KEY_NMF_DATA, [])}
    return retval


def build_kg_llm_summary(name_disease, gene_set_groupings: dict, gene_groupings: dict) -> str:
    # generate the LLM text that will be returned to the LLM calling driver

    str_template = """
* QUERY INFORMATION

The following data is a derived from a response to the query: "What drugs may treat the disease: '{}'.

* GENE SET GROUPINGS BY FACTOR:

Each item below specifies a latent factor grouping of biological gene sets.

{}

* GENE GROUPINGS BY FACTOR:

Each item below specifies a latent factor grouping of genes.

{}

    """
    str_result = ""

    # generate
    str_result = str_template.format(name_disease,
                                     json.dumps(gene_set_groupings, indent=1),
                                     json.dumps(gene_groupings, indent=1))

    # return
    return str_result


async def generate_kg_summary_from_trapi_result(json_trapi_result):
    '''
    generates the kg summary from the trapi result for the LLM to use
    '''
    # initialize
    str_kg_summary = ""

    # generate
    # 0 - get the disease name
    name_disease = get_disease_name_from_trapi_result(json_trapi_result=json_trapi_result)

    # 1 - parse out trapi and get genes
    genes = get_genes_from_trapi(json_trapi_result)
    list_genes = list(genes.values())
    # 2 - get gene nmf call with gene list input
    nmf_result = await gene_info_client.get_nmf_analysis(list_genes, 40)
    # 3 - get lists of gene set factors (could be list of gene set lists)
    gene_set_groupings = get_groupings_from_nmf(nmf_result, 'top_gene_sets')
    # 4 - get lists of gene factors (could be list of gene set lists)
    gene_groupings = get_groupings_from_nmf(nmf_result, 'top_genes')
    # 5 - package data into LLM query input
    str_kg_summary = build_kg_llm_summary(name_disease, gene_set_groupings, gene_groupings)

    # return
    return str_kg_summary


def get_disease_name_from_trapi_result(json_trapi_result):
    '''
    extract the disease name from the trapi query result
    '''
    # initialize
    first_disease_name = ""

    # get the nodes map
    map_nodes = json_trapi_result.get('fields', {}).get('data', {}).get('message', {}).get('knowledge_graph', {}).get('nodes', {})

    # get the first diease
    for key, value in map_nodes.items():
        if "biolink:Disease" in value.get("categories", []):
            first_disease_name = value["name"]
            break

    # return
    return first_disease_name


# main
if __name__ == "__main__":
    '''
    main area for tests of the above mehods
    can be moved to pytest class later
    '''
    import argparse
    parser = argparse.ArgumentParser(description='Test this puppy')

    parser.add_argument('-i', '--input', help='Input JSON file path of a TRAPI response')
    args = parser.parse_args()

    print("loading file: {}".format(args.input))
    with open(args.input) as json_data:
        json_pk = json.loads(json_data.read())

    # # pretty print
    # pretty_print_json(json_data=json_pk, num_lines=200)

    # # print the nodes json
    # json_nodes = get_result_nodes(json_data=json_pk)
    # # print(json.dumps(json_nodes, indent=2))

    # # get the disease name
    # name_disease = get_disease_name_from_trapi_result(json_trapi_result=json_pk)
    # print("Got disease: {}".format(name_disease))

    # # get the gene map
    # map_genes = get_genes_from_trapi(json_trapi_result=json_pk, log=True)
    # # pretty_print_json(json_data=map_genes, num_lines=1000)
    # list_genes = list(map_genes.values())
    # # print(json.dumps(list_genes, indent=2))

    # # test the NMF service
    # json_nmf_result = call_nmf_service(url=URL_NMF, list_genes=list_genes)
    # # print(json.dumps(json_nmf_result, indent=2))

    # # extract the gene set groupings
    # map_gene_set_groupings = get_gene_set_groupings_from_nmf(json_nmf=json_nmf_result)
    # # print(json.dumps(map_gene_set_groupings, indent=2))

    # # extract the gene groupings
    # map_gene_groupings = get_gene_groupings_from_nmf(json_nmf=json_nmf_result)
    # print(json.dumps(map_gene_groupings, indent=2))

    # # build the llm input
    # str_kg_summary = build_kg_llm_summary(name_disease='Bethlem myopathy', map_gene_set_groupings=map_gene_set_groupings)
    # print(str_kg_summary)


    # get the llm input from the trapi result
    import asyncio
    str_kg_summary = asyncio.run(generate_kg_summary_from_trapi_result(json_trapi_result=json_pk))
    print(str_kg_summary)


