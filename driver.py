import json
import argparse
import os
from graphwerk import trapimsg
from summarizers import trapi_summarizer
from summarizers import ui_summarizer
from summarizers import ui_tools
from summarizers import gene_nmf_utils
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

def load_input(source: str) -> dict:
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
    parser.add_argument('-i', '--input', help='Input JSON file path')
    parser.add_argument('-f', '--input-format', choices=('trapi', 'ui'), default='trapi',
                        help='Input payload format (default: trapi)')
    parser.add_argument('--start', type=int, help='Starting index in results array')
    parser.add_argument('--end', type=int, help='Ending index (exclusive) in results array')
    parser.add_argument('--list', type=str, help='Comma-separated list of indices, e.g. --list=9,18,202')
    parser.add_argument('--template', type=str, help='YAML template for OpenAI query')
    parser.add_argument('--summary-type', choices=('general', 'gene', 'both'), default='general',
                        help='Type of summary to generate (default: general)')
    parser.add_argument('--nmf-template', type=str, default='yaml/nmf.yaml',
                        help='YAML template for gene NMF summary (default: yaml/nmf.yaml)')
    parser.add_argument('--min-genes', type=int, default=gene_nmf_utils.DEFAULT_MIN_GENES,
                        help=f'Minimum gene count before a low-confidence caveat is injected (default: {gene_nmf_utils.DEFAULT_MIN_GENES})')
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

def shrink_ui_payload(payload: dict, selected_idx: int) -> tuple[dict, int]:
    """Shrink full UI payloads if needed, returning (payload, adjusted_idx)."""
    if 'data' in payload and 'disease' not in payload['data']:
        payload = ui_tools.shrink_payload(payload, selected_idx)
        selected_idx = 0
    return payload, selected_idx


async def execute_llm_call(client, summary_text: str, template_path: str, args):
    """Run an LLM call using the specified template and execution mode."""
    template = openai_lib.expand_yaml_template(template_path, ('instructions',))

    if args.run:
        resp = await client.responses.create(**template['params'],
                                               instructions=template['instructions'],
                                               input=summary_text)
        print(resp)
    elif args.loop:
        print(summary_text)
        resp = await client.run_as_loop(summary_text, template, llm_utils.handle_fun_call)
        print(resp)
    elif args.stream:
        print(summary_text)
        async for event in client.run_as_loop_streaming(summary_text, template, llm_utils.handle_fun_call,
                                                        1, None, 10, args.chunk):
            print(event)
    else:
        # Dry run: print pre-summary and template
        print(summary_text)
        print(json.dumps(template, indent=2))


async def main():
    client = openai_lib.OpenAIClient(os.environ['OPENAI_KEY'])
    args = parse_args()
    if args.standalone:
        expanded = openai_lib.expand_yaml_template(args.standalone, ('model', 'instructions', 'input'))
        print(expanded)
        resp = await client.responses.create(**expanded)
        print(resp)
        sys.exit(0)

    orig = load_input(args.input)
    idx_range = get_index_range(args)

    if args.input_format == 'trapi':
        # Collect once: traversal + formatting + node collection
        kg_summary, res_nodes, disease_name = trapi_summarizer.summarize_trapi_response(orig, idx_range, 8)

        if args.summary_type in ('general', 'both'):
            if args.template:
                await execute_llm_call(client, kg_summary, args.template, args)
            else:
                print(kg_summary)

        if args.summary_type in ('gene', 'both'):
            gene_dict = gene_nmf_utils.extract_genes_from_trapi_nodes(res_nodes)
            nmf_summary = await gene_nmf_utils.generate_nmf_presummary(
                gene_dict, disease_name, args.min_genes)
            await execute_llm_call(client, nmf_summary, args.nmf_template, args)

    else:
        # UI format
        selected_idxs = tuple(idx_range)
        if len(selected_idxs) != 1:
            raise ValueError(
                "UI summaries currently support exactly one result index. "
                "Use --list=<n> or run with -n 1."
            )
        # Collect once: shrink + presummary
        payload, adjusted_idx = shrink_ui_payload(orig, selected_idxs[0])
        presummary = ui_tools.create_ui_presummary(payload, adjusted_idx)

        if args.summary_type in ('general', 'both'):
            kg_summary = ui_summarizer.format_ui_summary(presummary, payload)
            if args.template:
                await execute_llm_call(client, kg_summary, args.template, args)
            else:
                print(kg_summary)

        if args.summary_type in ('gene', 'both'):
            gene_dict = gene_nmf_utils.extract_genes_from_ui_nodes(presummary['nodes'])
            nmf_summary = await gene_nmf_utils.generate_nmf_presummary(
                gene_dict, presummary['disease_name'], args.min_genes)
            await execute_llm_call(client, nmf_summary, args.nmf_template, args)


if __name__ == '__main__':
    asyncio.run(main())
