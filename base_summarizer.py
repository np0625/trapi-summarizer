import re

def create_node_data_summary(node_presummaries: list[dict]) -> str:
    retval = """
Here are the biological entities involved.

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
    retval = """
Here is the per-result reasoning data, in the form of sequences of triples,  that indicates relationships
between biological entities that ultimately prove or support the primary query referenced above. Follow the
relationships with great care, remembering that they may not be presented in any particular order. You must
determine and understand the transitive relationships between the individual triples in order to grok the
overall line of reasoning, so that you can eventually summarize it. Note: all predicates belong to the Biolink data model.

Each result's graph of relationships is presented in this form:
    | <subject> | <predicate> | <object> |\n\n"""
    for e in edge_presummaries:
        retval += f"| {e['subject_name']} | {re.sub(r"^biolink:", '', e['predicate'])} | {e['object_name']} |\n"
    retval += '-' * 70
    return retval

def create_query_summary():
    pass