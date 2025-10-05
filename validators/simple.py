from pubmed_client import get_publication_info  # TODO: reorganize to avoid using a copy of pubmed_client.py
import os
import subprocess

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instructions.txt'), 'r') as fin:
    instructions = fin.read()

def validation_prompt(nodes_text, edge_text, biomedical_text):
    return '\n\n'.join((instructions,
                        'NODE/ENTITY INFORMATION',
                        nodes_text,
                        'EDGE INFORMATION',
                        'The item below specifies a relationship between two biological entities.',
                        edge_text,
                        'BIOMEDICAL TEXT',
                        biomedical_text))

def entity_category_curie_table(entities):
    return ' | <ENTITY NAME> | <CATEGORY> | <CURIE> |\n' + '\n'.join(' | '.join(('', name, cat, curie, '')) for name, cat, curie in entities)

def spo_table(s, p, o):
    return ' | '.join((' | <SUBJECT> | <PREDICATE> | <OBJECT> |\n', s, p, o, ''))

async def pubid_abstract(pubid):
   response = await get_publication_info([pubid], 'placeholder')
   return response['results'][pubid]['abstract']

def validation_result(biomedical_text, llm_thinking_start, llm_thinking_end, llm_output):
    start = llm_output.find(llm_thinking_start)
    assert start >= 0, ('missing thinking start', llm_output)
    start += len(llm_thinking_start)
    i = llm_output.find(llm_thinking_end, start)
    assert i >= 0, ('missing thinking end', llm_output)
    thinking = llm_output[start:i]
    i += len(llm_thinking_end)
    assert (len(llm_output) >= i+2 and llm_output[i].isdigit() and llm_output[i+1] == ' '), ('invalid validator output', llm_output[i:])
    code = int(llm_output[i])
    assert code in range(4), ('invalid validator code', llm_output[i:])
    explanation = llm_output[i+2:].rstrip()
    if code == 0 or code == 1:
        assert biomedical_text.find(explanation) >= 0, ('explanation does not appear in biomedical text', explanation)
    return code, explanation, thinking

def run_ollama(model, prompt):
    process = subprocess.run(('ollama', 'run', model), input=prompt, capture_output=True, text=True, check=True)
    return process.stdout

if __name__ == '__main__':
    import asyncio
    biomedical_text = asyncio.run(pubid_abstract('PMID:19001354'))
    prompt = validation_prompt(entity_category_curie_table((('PSEN1', 'Gene', 'NCBIGene:5663'),
                                                            ('Alzheimer disease', 'Disease, DiseaseOrPhenotypicFeature', 'MONDO:0004975'))),
                               spo_table('PSEN1', 'causes', 'Alzheimer disease'),
                               biomedical_text)
    print('prompt:', prompt)
    llm_output = run_ollama('gpt-oss:120b', prompt)
    code, explanation, thinking = validation_result(biomedical_text, 'Thinking...\n', '...done thinking.\n\n', llm_output)
    print('code:', code)
    print('explanation:', explanation)
    print('thinking:', thinking)
