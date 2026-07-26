#!/usr/bin/env python
"""CLI mirror of driver.py, but running against Vertex-hosted models instead of
OpenAI. Same pre-summary pipeline, tool dispatch, and summary types; the only
difference is the provider/model, chosen with --provider (and optional --model).

    python vertex_driver.py --provider gemini   -i data/small.json --list 0 --template yaml/rt3.yaml --loop
    python vertex_driver.py --provider anthropic -i data/small.json --list 0 --summary-type gene --run

Requires the Vertex service-account key in the environment (GCP_SA_PRIVATE_KEY,
GCP_SA_PRIVATE_KEY_ID); see vertex_creds.py. A pure dry run (no --run/--loop/
--stream) needs no key.
"""
import json
import argparse
import asyncio
import uuid

from summarizers import trapi_summarizer
from summarizers import ui_summarizer
from summarizers import ui_tools
from summarizers import gene_nmf_utils
import ars_client
import llm_utils
import vertex_llm


def is_pk(value: str) -> bool:
    try:
        return uuid.UUID(str(value)).version == 4
    except ValueError:
        return False


def load_input(source: str) -> dict:
    path = ars_client.fetch_response(source) if is_pk(source) else source
    with open(path, 'r') as f:
        return json.load(f)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Summarize TRAPI/UI responses via Vertex models')
    parser.add_argument('--provider', choices=('gemini', 'anthropic'), required=True,
                        help='Vertex model provider')
    parser.add_argument('--model', type=str, help='Override the model id (else provider default)')
    parser.add_argument('-n', type=int, default=100, help='Number of results to include (default: 100)')
    parser.add_argument('-i', '--input', help='Input JSON file path (or a PK to fetch)')
    parser.add_argument('-f', '--input-format', choices=('trapi', 'ui'), default='trapi',
                        help='Input payload format (default: trapi)')
    parser.add_argument('--start', type=int, help='Starting index in results array')
    parser.add_argument('--end', type=int, help='Ending index (exclusive) in results array')
    parser.add_argument('--list', type=str, help='Comma-separated list of indices, e.g. --list=9,18,202')
    parser.add_argument('--template', type=str, help='YAML template for the query')
    parser.add_argument('--summary-type', choices=('general', 'gene', 'both'), default='general',
                        help='Type of summary to generate (default: general)')
    parser.add_argument('--nmf-template', type=str, default='yaml/nmf.yaml',
                        help='YAML template for gene NMF summary (default: yaml/nmf.yaml)')
    parser.add_argument('--min-genes', type=int, default=gene_nmf_utils.DEFAULT_MIN_GENES,
                        help=f'Min gene count before a low-confidence caveat (default: {gene_nmf_utils.DEFAULT_MIN_GENES})')
    parser.add_argument('--run', action='store_true', help='Single response, no tool loop')
    parser.add_argument('--loop', action='store_true', help='Run a (non-streaming) tool-calling loop')
    parser.add_argument('--stream', action='store_true', help='Stream results from a tool-calling loop')
    parser.add_argument('--chunk', type=int, default=10, help='Streaming text chunk size (default 10)')
    args = parser.parse_args()

    if args.end is not None and args.start is None:
        parser.error("--end cannot be specified without --start")
    if args.end is not None and args.start is not None and int(args.end) < int(args.start):
        parser.error("--end must be >= --start")
    return args


def get_index_range(args) -> tuple[int, ...] | range:
    if args.list is not None:
        return tuple(int(num) for num in args.list.strip(',').split(',') if num.strip() != '')
    if args.start is None:
        return range(0, args.n)
    if args.end is None:
        return range(args.start, args.start + args.n)
    return range(args.start, args.end + 1)


def shrink_ui_payload(payload: dict, selected_idx: int) -> tuple[dict, int]:
    """Shrink full UI payloads if needed, returning (payload, adjusted_idx)."""
    if 'data' in payload and 'disease' not in payload['data']:
        payload = ui_tools.shrink_payload(payload, selected_idx)
        selected_idx = 0
    return payload, selected_idx


async def execute_llm_call(client, summary_text: str, template_path: str, args, post_process=None):
    """Run an LLM call in the requested mode. If post_process is given it is
    applied to the model's output text before printing."""
    template = vertex_llm.expand_template(template_path)

    if args.run:
        result = await client.run(summary_text, template)
        print(post_process(result.output_text) if post_process else result.output_text)
    elif args.loop:
        print(summary_text)
        result = await client.run_as_loop(summary_text, template, llm_utils.handle_fun_call)
        print(post_process(result.output_text) if post_process else result.output_text)
    elif args.stream:
        print(summary_text)
        final_event = None
        async for event in client.run_as_loop_streaming(summary_text, template,
                                                        llm_utils.handle_fun_call,
                                                        1, None, 10, args.chunk):
            final_event = event
            print(event)
        if post_process and final_event:
            print(post_process(final_event.get('output_text', '')))
    else:
        # Dry run: print pre-summary and the (non-instruction) template config
        print(summary_text)
        print(json.dumps({k: v for k, v in template.items() if k != 'instructions'}, indent=2))


async def main():
    args = parse_args()
    # Client (and thus creds) only needed when we actually call the model.
    client = None
    if args.run or args.loop or args.stream:
        client = vertex_llm.make_client(args.provider, args.model)

    orig = load_input(args.input)
    idx_range = get_index_range(args)

    if args.input_format == 'trapi':
        kg_summary, res_nodes, disease_name = trapi_summarizer.summarize_trapi_response(orig, idx_range, 8)

        if args.summary_type in ('general', 'both'):
            if args.template:
                await execute_llm_call(client, kg_summary, args.template, args)
            else:
                print(kg_summary)

        if args.summary_type in ('gene', 'both'):
            gene_dict = gene_nmf_utils.extract_genes_from_trapi_nodes(res_nodes)
            nmf_result = await gene_nmf_utils.generate_nmf_presummary(
                gene_dict, disease_name, args.min_genes)
            if nmf_result:
                post = lambda html: gene_nmf_utils.wrap_nmf_response(html, nmf_result, args.min_genes)
                await execute_llm_call(client, nmf_result.presummary, args.nmf_template, args,
                                       post_process=post)
    else:
        # UI format
        selected_idxs = tuple(idx_range)
        if len(selected_idxs) != 1:
            raise ValueError("UI summaries currently support exactly one result index. "
                             "Use --list=<n> or run with -n 1.")
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
            nmf_result = await gene_nmf_utils.generate_nmf_presummary(
                gene_dict, presummary['disease_name'], args.min_genes)
            if nmf_result:
                post = lambda html: gene_nmf_utils.wrap_nmf_response(html, nmf_result, args.min_genes)
                await execute_llm_call(client, nmf_result.presummary, args.nmf_template, args,
                                       post_process=post)


if __name__ == '__main__':
    asyncio.run(main())
