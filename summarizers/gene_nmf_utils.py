

# imports
import json
import logging
import requests


# constants
URL_NMF = "https://translator.broadinstitute.org/genetics_provider/bayes_gene/pigean"
KEY_NMF_PIGEAN_FACTORS = "pigean-factor"
KEY_NMF_DATA = "data"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# methods
def get_genes_from_trapi(json_trapi_result, log=False):
    '''
    extracts a list of genes from a valid trapi response
    '''
    # initialize
    map_result = {}
    map_nodes = {}

    # get the nodes from the trapi response json
    map_nodes = get_result_nodes(json_data=json_trapi_result, log=log)

    # get gene from trapi
    map_result = {key: value.get('name', '') for key, value in map_nodes.items() 
            if "biolink:Gene" in value.get("categories", [])}
    
    # log
    if log:
        logger.info("got gene map of size: {}".format(len(map_result)))
                    
    # return
    return map_result


def call_nmf_service(url, list_genes, log=False):
    '''
    calls the gene nmf service
    '''
    # initialize
    json_nmf_result = {}

    # build the input
    json_input = {
    "p_value": "0.5",
    "max_number_gene_sets": 150,
    "gene_sets": "default",
    "enrichment_analysis": "hypergeometric",
    "generate_factor_labels": False,
    "calculate_gene_scores": True,
    "exclude_controls": True,
    "genes": list_genes}

    # call REST service
    response = requests.post(url, json=json_input)
    response.raise_for_status()
    json_nmf_result = response.json()

    # return
    return json_nmf_result


def get_genes_from_nmf(json_nmf, log=False):
    '''
    will parse a valid nmf json and return the gene list
    '''
    # initialize
    list_result = []

    # get gene list from the nmf json

    # return
    return list_result


def get_gene_set_groupings_from_nmf(json_nmf, log=False):
    '''
    will parse a valid nmf json and return a list of gene set groupings (by factor)
    '''
    # initialize
    map_factor_gene_sets = {}

    # get gene list from the nmf json
    map_factor_gene_sets = {item["factor"]: item.get("top_gene_sets", '').split(";") for item in json_nmf.get(KEY_NMF_PIGEAN_FACTORS, {}).get(KEY_NMF_DATA, [])}

    # return
    return map_factor_gene_sets


def get_result_nodes(json_data, log=False):
    '''
    extracts the node map from the result
    '''
    # initialize
    map_nodes = {}

    # get the nodes
    map_nodes = json_data.get('fields', {}).get('data', {}).get('message', {}).get('knowledge_graph', {}).get('nodes', {})

    # return
    return map_nodes


def pretty_print_json(json_data, num_lines, log=False):
    '''
    pretty print given number of lines fro debugging
    '''
    pretty_json = json.dumps(json_data, indent=2)
    lines = pretty_json.split('\n')[:num_lines]
    for line in lines:
        print(line)


def build_kg_llm_summary(name_disease, map_gene_set_groupings, log=False):
    '''
    generate the LLM text that will be returned to the LLM calling driver
    '''
    # initialize
    str_template = """
* QUERY INFORMATION

The following data is a derived from a response to the query: "What drugs may treat the disease: '{}'.

* GENE SET GROUPINGS BY FACTOR: 

Each item below specifies a latent factor grouping of biological gene sets.

{}
    """
    str_result = ""

    # generate
    str_result = str_template.format(name_disease, json.dumps(map_gene_set_groupings, indent=1))

    # return
    return str_result


def generate_kg_summary_from_trapi_result(json_trapi_result, log=False):
    '''
    generates the kg summary from the trapi result for the LLM to use
    '''
    # initialize
    str_kg_summary = ""

    # generate
    # 0 - get the disease name
    name_disease = get_disease_name_from_trapi_result(json_trapi_result=json_trapi_result)

    # 1 - parse out trapi and get genes
    map_genes = get_genes_from_trapi(json_trapi_result=json_trapi_result, log=True)
    list_genes = list(map_genes.values())

    # 2 - get gene nmf call with gene list input
    json_nmf_result = call_nmf_service(url=URL_NMF, list_genes=list_genes)

    # 3 - get lists of gene set factors (could be list of gene set lists)
    map_gene_set_groupings = get_gene_set_groupings_from_nmf(json_nmf=json_nmf_result)

    # 4 - package data into LLM query input
    str_kg_summary = build_kg_llm_summary(name_disease=name_disease, map_gene_set_groupings=map_gene_set_groupings)

    # return
    return str_kg_summary


def get_disease_name_from_trapi_result(json_trapi_result, log=False):
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
    # read the test result file
    file_path = "./data/e0b7fd22-d08c-421d-a551-ea62d1417a36.json"
    file_path = "./data/breast_cancer.json"
    print("loading file: {}".format(file_path))    
    with open(file_path) as json_data:
        json_pk = json.loads(json_data.read())

    # # pretty print
    # pretty_print_json(json_data=json_pk, num_lines=200)

    # # print the nodes json
    # json_nodes = get_result_nodes(json_data=json_pk)
    # # print(json.dumps(json_nodes, indent=2))

    # get the disease name
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

    # # build the llm input
    # str_kg_summary = build_kg_llm_summary(name_disease='Bethlem myopathy', map_gene_set_groupings=map_gene_set_groupings)
    # print(str_kg_summary)


    # get the llm input from the trapi result
    str_kg_summary = generate_kg_summary_from_trapi_result(json_trapi_result=json_pk)
    print(str_kg_summary)


