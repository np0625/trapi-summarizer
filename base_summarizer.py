import re
import jq
import json

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
"""

def create_node_data_summary(node_presummaries: list[dict]) -> str:
    retval = """Here are the biological entities involved.

Reference this information when constructing the summary. Supplement this information
with your own training data when producing the summary /if/ it will help in producing a better summary,
but take GREAT care to remain within known verified scientific facts. Do not speculate or use
popular knowledge if you do not have scientific-grade sources. Note: all categories belong to the Biolink data model.\n

The data is presented in the form:
   | <entity name> | <categories> | <description if available> |\n\n"""
    for n in node_presummaries:
        retval += f"| {n['name']} | {", ".join(re.sub(r"^biolink:", "", a) for a in n['categories'])} | {n['description']} |\n"
    retval += '-' * 70
    return retval


def create_edge_data_summary(edge_presummaries: list[dict]) -> str:
    retval = '| subject | predicate | object |\n'
    for e in edge_presummaries:
        retval += f"| {e['subject_name']} | {re.sub(r"^biolink:", '', e['predicate'])} | {e['object_name']} |\n"
    retval += '-' * 70
    return retval

def create_query_summary(object_id: str, object_data: dict) -> str:
    jqprog = jq.compile('.attributes[] | select(.attribute_type_id == "biothings_annotations") | .value[0].disease_ontology.def')
    name = object_data['name']
    definition = jqprog.input_text(json.dumps(object_data)).first()
    if definition:
        definition = f"A brief definition of this disease: {definition}"
    retval = f"""The following data is a response to the query: "What drugs may treat the disease: '{name}'.
{definition}

The data is organized as a list of results. Each result identifies the particular drug or molecule that may treat the disease, along
with reasoning to support this conclusion. The reasoning is presented as sequences of triples,  that indicates relationships
between biological entities that ultimately prove or support the primary query referenced above. Follow the
relationships with great care, remembering that they may not be presented in any particular order. You must
determine and understand the transitive relationships between the individual triples in order to grok the
overall line of reasoning, so that you can eventually summarize it. Note: all predicates belong to the Biolink data model.

Each result's graph of relationships is presented in this form:
    | <subject> | <predicate> | <object> |\n\n

Carefully study this data, then provide a summary as defined in the project-wide instructions.
"""
    return retval
