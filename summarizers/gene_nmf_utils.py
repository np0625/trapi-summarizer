

# imports
import json
import logging

# constants
URL_NMF = ""
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


def call_nmf_service(list_genes, log=False):
    '''
    calls the gene nmf service
    '''
    # initialize
    json_result = {}

    # call REST service

    # get data

    # return
    return json_result


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
    list_result = []

    # get gene list from the nmf json

    # return
    return list_result


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


# main
if __name__ == "__main__":
    '''
    main area for tests of the above mehods
    can be moved to pytest class later
    '''
    # read the test result file
    file_path = "./data/e0b7fd22-d08c-421d-a551-ea62d1417a36.json"
    print("loading file: {}".format(file_path))    
    with open(file_path) as json_data:
        json_pk = json.loads(json_data.read())

    # pretty print
    # pretty_print_json(json_data=json_pk, num_lines=100)

    # print the nodes json
    json_nodes = get_result_nodes(json_data=json_pk)
    # print(json.dumps(json_nodes, indent=2))

    # get the gene map
    map_genes = get_genes_from_trapi(json_trapi_result=json_pk, log=True)
    pretty_print_json(json_data=map_genes, num_lines=1000)


