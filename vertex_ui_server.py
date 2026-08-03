#!/usr/bin/env python
"""FastAPI server mirroring ui_server.py but backed by Vertex-hosted models.
The provider is chosen at startup with --provider; the endpoints, payloads, and
SSE event contract are identical to ui_server.py, so this is a drop-in swap.

    python vertex_server.py --provider gemini [--model ...] [--host 0.0.0.0] [--port 8000]

Requires the Vertex service-account key in the environment (GCP_SA_PRIVATE_KEY,
GCP_SA_PRIVATE_KEY_ID); see vertex_creds.py.
"""
import argparse
import json

from fastapi import FastAPI, Request
from sse_starlette.sse import EventSourceResponse

from summarizers import ui_summarizer
from summarizers import ui_tools
from summarizers import gene_nmf_utils
import llm_utils
import vertex_llm


def create_app(provider: str, model: str | None = None) -> FastAPI:
    client = vertex_llm.make_client(provider, model)
    template = vertex_llm.expand_template('yaml/rt3.yaml')
    nmf_template = vertex_llm.expand_template('yaml/nmf.yaml')

    app = FastAPI()

    @app.get("/")
    async def root():
        return {"message": "'Sup", "provider": provider, "model": client.model}

    @app.post("/summary")
    async def create_summary(payload: dict):
        summary = ui_summarizer.create_ui_summary(payload, 0)
        print(summary)
        result = await client.run_as_loop(summary, template, llm_utils.handle_fun_call)
        return {"response_text": result.output_text}

    @app.post("/summary-streaming")
    async def create_summary_streaming(payload: dict, request: Request):
        async def event_generator():
            summary = ui_summarizer.create_ui_summary(payload, 0)
            print(summary)
            try:
                async for event in client.run_as_loop_streaming(
                        summary, template, llm_utils.handle_fun_call, 1, None, 10, 10):
                    yield {"event": "data", "data": json.dumps({"event": event})}
                    if await request.is_disconnected():
                        break
            except Exception as e:
                yield {"event": "error", "data": json.dumps({"error": str(e)})}
            yield {"event": "complete", "data": json.dumps({"complete": True})}

        return EventSourceResponse(event_generator())

    @app.post("/gene-summary-streaming")
    async def create_gene_summary_streaming(payload: dict, request: Request):
        async def event_generator():
            # Shrink + presummary
            if 'data' in payload and 'disease' not in payload.get('data', {}):
                shrunk = ui_tools.shrink_payload(payload, 0)
                presummary = ui_tools.create_ui_presummary(shrunk, 0)
            else:
                presummary = ui_tools.create_ui_presummary(payload, 0)

            gene_dict = gene_nmf_utils.extract_genes_from_ui_nodes(presummary['nodes'])
            nmf_result = await gene_nmf_utils.generate_nmf_presummary(
                gene_dict, presummary['disease_name'])

            if nmf_result is None:
                yield {"event": "error", "data": json.dumps({"error": "No genes found in result"})}
                yield {"event": "complete", "data": json.dumps({"complete": True})}
                return

            try:
                final_event = None
                async for event in client.run_as_loop_streaming(
                        nmf_result.presummary, nmf_template, llm_utils.handle_fun_call,
                        1, None, 10, 10):
                    final_event = event
                    yield {"event": "data", "data": json.dumps({"event": event})}
                    if await request.is_disconnected():
                        break

                # Post-process: wrap with warning banner + factor listing
                if final_event:
                    wrapped = gene_nmf_utils.wrap_nmf_response(
                        final_event.get('output_text', ''), nmf_result,
                        gene_nmf_utils.DEFAULT_MIN_GENES)
                    yield {"event": "wrapped", "data": json.dumps({"response_text": wrapped})}
            except Exception as e:
                yield {"event": "error", "data": json.dumps({"error": str(e)})}
            yield {"event": "complete", "data": json.dumps({"complete": True})}

        return EventSourceResponse(event_generator())

    return app


def main():
    p = argparse.ArgumentParser(description="Vertex-backed summary server (mirror of ui_server.py)")
    p.add_argument('--provider', choices=('gemini', 'anthropic'), required=True,
                   help='Vertex model provider selected at startup')
    p.add_argument('--model', type=str, help='Override model id (else provider default)')
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8000)
    args = p.parse_args()

    import uvicorn
    uvicorn.run(create_app(args.provider, args.model), host=args.host, port=args.port)


if __name__ == '__main__':
    main()
