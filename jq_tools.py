import jq
import json

def try_seq(exprs: list, val: dict, default=None):
    for e in exprs:
        prog = jq.compile(e)
        try:
            if (res := prog.input_value(val).first()):
                return res
        except Exception:
            continue

    return default

def try_first(prog, arg, default=None):
    try:
        return jq.first(prog, arg)
    except Exception:
        return default

if __name__ == "__main__":
    d0 = {'name': 'Wilson disease', 'categories': ['biolink:NamedThing', 'biolink:ThingWithTaxon', 'biolink:BiologicalEntity', 'biolink:DiseaseOrPhenotypicFeature', 'biolink:Disease', 'biolink:Entity', 'biolink:PhenotypicFeature'], 'attributes': [{'value': [{'query': 'MONDO:0010200', '_id': 'MONDO:0010200', '_score': 9.906915, 'disease_ontology': {'_license': 'https://github.com/DiseaseOntology/HumanDiseaseOntology/blob/master/DO_LICENSE.txt', 'def': '"A metal metabolism disease that is characterized by excess copper stored in various body tissues, particularly the liver, brain, and corneas of the eyes." [url:https\\://pubmed.ncbi.nlm.nih.gov/32279718/, url:https\\://www.genome.gov/Genetic-Disorders/Wilson-Disease]', 'doid': 'DOID:893', 'name': 'Wilson disease', 'synonyms': {'exact': ['Cerebral pseudosclerosis', 'hepatolenticular degeneration', 'Westphal pseudosclerosis', 'Westphal-Strumpell syndrome', "Wilson's disease"]}, 'xrefs': {'gard': '7893', 'icd10': 'E83.01', 'mesh': 'D006527', 'mim': '277900', 'ncit': 'C84756', 'snomedct_us_2023_03_01': '88518009', 'umls_cui': 'C0019202'}}, 'mondo': {'mondo': 'MONDO:0010200', 'synonym': {'exact': ['cerebral pseudosclerosis', 'hepatolenticular degeneration', 'Westphal pseudosclerosis', 'Westphal-Strumpell syndrome', 'Wilson disease', "Wilson's disease"], 'related': ['hepatolenticular Degeneration', 'WD', 'Wnd']}, 'xrefs': {'doid': ['DOID:893'], 'gard': ['7893'], 'icd10cm': ['E83.01'], 'icd11': ['468161208'], 'meddra': ['10019819'], 'medgen': ['42426'], 'mesh': ['D006527'], 'nando': ['1200655', '2200579'], 'ncit': ['C84756'], 'nord': ['1856'], 'omim': ['277900'], 'orphanet': ['905'], 'sctid': ['88518009'], 'umls': ['C0019202']}}, 'umls': {'_license': 'https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/release/license_agreement.html', 'umls': 'C0019202'}}], 'value_url': None, 'attributes': None, 'description': None, 'value_type_id': None, 'attribute_source': None, 'attribute_type_id': 'biothings_annotations', 'original_attribute_name': None}], 'is_set': False}
    j0 = json.dumps(d0)
    # print(j0)

    jbig = {}
    with open('./data/big-j.json', 'r') as f:
        jbig = json.load(f)

    p0 = jq.compile(".")
    pattr = jq.compile('.attributes[] | select(.attribute_type_id == "biothings_annotations") | .value[]')
    # print(pattr.input_value(jbig).text())
    r = try_seq(('.attridfbutes',
                 '.attributes[] | select(.attribute_type_id == "biothings_annotations") | .value[] | length'),
                 jbig, "hi")
    print(r)
