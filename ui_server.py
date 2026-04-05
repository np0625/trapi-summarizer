from fastapi import FastAPI, Request
from summarizers import ui_summarizer
from summarizers import ui_tools
from summarizers import gene_nmf_utils
import openai_lib
import llm_utils
import os
import json
from sse_starlette.sse import EventSourceResponse


client = openai_lib.OpenAIClient(os.environ['OPENAI_KEY'])

template = openai_lib.expand_yaml_template('yaml/rt3.yaml', ('instructions',))
nmf_template = openai_lib.expand_yaml_template('yaml/nmf.yaml', ('instructions',))


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "'Sup"}

@app.post("/summary")
async def create_summary(payload: dict):
    # Typing the payload as ``dict`` makes FastAPI shut up with the type checking
    summary = ui_summarizer.create_ui_summary(payload, 0)
    print(summary)
    llm_summary = await client.run_as_loop(summary, template, llm_utils.handle_fun_call)
    # print(llm_summary)
    return {"response_text": llm_summary.output_text}

@app.post("/summary-streaming")
async def create_summary_streaming(payload: dict, request: Request):
    # Typing the payload as ``dict`` makes FastAPI shut up with the type checking
    async def event_generator():
        summary = ui_summarizer.create_ui_summary(payload, 0)
        print(summary)

        try:
            async for event in client.run_as_loop_streaming(summary, template, llm_utils.handle_fun_call,
                                                            1, None, 10, 10):
                yield {"event": "data", "data": json.dumps({"event": event})}

                # Check if client disconnected
                if await request.is_disconnected():
                    break

        except Exception as e:
            # Send error as SSE event
            yield {"event": "error", "data": json.dumps({"error": str(e)})}

        # Send completion event
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

        # Extract genes and run NMF
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
