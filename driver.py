import json
import argparse
import os
from graphwerk import trapimsg
from summarizers import trapi_summarizer as summarizer
import openai_lib
import sys
import ars_client
import uuid
import llm_utils
import asyncio

def is_pk(value: str) -> bool:
    try:
        return uuid.UUID(str(value)).version == 4
    except ValueError:
        return False

def load_trapi_response(source: str) -> dict:
    if is_pk(source):
        path = ars_client.fetch_response(source)
    else:
        path = source
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
    parser.add_argument('--run', action='store_true', help='Run the query indicated by the template and input file')
    parser.add_argument('--loop', action='store_true', help='Run the query indicated by the template and input file in a tool-calling loop')
    parser.add_argument('--stream', action='store_true', help='Stream results from the query indicated by the template and input file (also runs as a tool-calling loop)')
    parser.add_argument('--chunk', type=int, default=10, help='Number of tokens of textual output to collect from the model output stream before pushing to the caller')
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


async def main():
    client = openai_lib.OpenAIClient(os.environ['OPENAI_KEY'])
    args = parse_args()
    if (args.standalone):
        expanded = openai_lib.expand_yaml_template(args.standalone, ('model', 'instructions', 'input'))
        print(expanded)
        resp = await client.responses.create(**expanded)
        print(resp)
        sys.exit(0)

    orig = load_trapi_response(args.input)
    idx_range = get_index_range(args)
    kg_summary = summarizer.summarize_trapi_response(orig, idx_range, 8)

    if (args.template):
        template = openai_lib.expand_yaml_template(args.template, ('instructions',))

    if (args.run):
        resp = await client.responses.create(**template['params'],
                                               instructions=template['instructions'],
                                               input=kg_summary)
        print(resp)
    elif (args.loop):
        print(kg_summary)
        resp = await client.run_as_loop(kg_summary, template, llm_utils.handle_fun_call)
        print(resp)
    elif (args.stream):
        print(kg_summary)
        async for event in client.run_as_loop_streaming(kg_summary, template, llm_utils.handle_fun_call,
                                                        1, None, 10, args.chunk):
            print(event)
    else:
        print(kg_summary)
        print(json.dumps(template, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
