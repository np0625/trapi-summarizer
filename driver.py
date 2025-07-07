import json
import argparse
import os
from graphwerk import trapimsg
import summarizer_tools as st
import base_summarizer as summarizer
import openai_lib
import sys
from pubmed_client import get_publication_info

def load_trapi_response(path: str) -> dict:
    with open(path, 'r') as f:
        data = json.load(f)
    return data

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Trim down TRAPI response files')
    parser.add_argument('-n', type=int, default=100, help='Number of results to include (default: 100)')
    parser.add_argument('-i', '--input', help='Input JSON file path of a TRAPI response')
    parser.add_argument('--start', type=int, help='Starting index in results array')
    parser.add_argument('--end', type=int, help='Ending index (exclusive) in results array')
    parser.add_argument('--list', type=str, help='Comma-separated list of indices, e.g. --list=9,18,202')
    parser.add_argument('--template', type=str, help='YAML template for OpenAI query')
    parser.add_argument('--run', type=bool, default=False, help='Run the query indicated by the template and input file')
    parser.add_argument('--loop', type=bool, default=False, help='Run the query indicated by the template and input file')
    parser.add_argument('--standalone', type=str, help='Execute an API query entirely from the provided yaml file')
    args = parser.parse_args()

    # Validate arguments
    if args.end is not None and args.start is None:
        parser.error("--end cannot be specified without --start")

    if args.end is not None and args.start is not None:
        if int(args.end) < int(args.start):
            parser.error("--end must be >= --start")

    return args

# TODO: filter this range to cap at limit of len(results)
def get_index_range(args) -> tuple[int, ...] | range:
    if args.list is not None:
        return tuple(int(num) for num in args.list.strip(',').split(',') if num.strip() != '')

    if args.start is None:
        return range(0, args.n) # note: not n-1, because that's how ranges work

    if args.end is None:
        return range(args.start, args.start + args.n) # ditto
    else:
        return range(args.start, args.end + 1)

def handle_fun_call(fun_name: str, args=str):
    retval = ''
    if fun_name == 'get_publication_info':
        arg_dict = json.loads(args)
        pub_ids = arg_dict['pubids'].split(',')
        retval = json.dumps(get_publication_info(pub_ids, arg_dict['request_id']))
    else:
        print(f"WARNING: did not recognize #{fun_name} as a valid tool to call")

    return retval

def run_as_loop(client, kg_summary: str, template_data: dict) -> None:
    prev_resp_id = None
    input=kg_summary
    complete = False
    count = 1
    while not complete:
        print(f"Around the loop: {count}")
        resp = client.responses.create(**template_data['params'],
                                       instructions=template_data['instructions'],
                                       previous_response_id=prev_resp_id,
                                       input=input)
        print(resp)
        for elem in resp.output:
            print(elem)
            if elem.type == 'function_call':
                fun_call_res = handle_fun_call(elem.name, elem.arguments)
                # The server already has the function_call in its stored history (we pass
                # previous_response_id), so we must send *only* the companion output item. Resending the
                # original element would duplicate its id and trigger a 400 error.
                input = [{
                    'type': 'function_call_output',
                    'call_id': elem.call_id,
                    'output': fun_call_res
                }]
                print(input)
            elif elem.type == 'message':
                complete = True
                print(resp.output_text) # SDK-only convenience property that aggregates all type=output_text elems from the output array
            else:
                print("Looping over elems...")
        prev_resp_id = resp.id
        count += 1


def main():
    client = openai_lib.OpenAIClient(os.environ['OPENAI_KEY'])
    args = parse_args()
    if (args.standalone):
        expanded = openai_lib.expand_yaml_template(args.standalone, ('model', 'instructions', 'input'))
        print(expanded)
        resp = client.responses.create(**expanded)
        print(resp)
        sys.exit(0)

    orig = load_trapi_response(args.input)
    idx_range = get_index_range(args)
    kg_summary = summarizer.summarize_trapi_response(orig, idx_range, 8)

    if (args.template):
        template = openai_lib.expand_yaml_template(args.template, ('instructions',))

    if (args.run):
        resp = client._client.responses.create(**template['params'],
                                               instructions=template['instructions'],
                                               input=kg_summary)
        print(resp)
    elif (args.loop):
        resp = client.run_as_loop(kg_summary, template, handle_fun_call)
        print(resp)
    else:
        print(kg_summary)
        print(json.dumps(template, indent=2))


if __name__ == '__main__':
    main()
