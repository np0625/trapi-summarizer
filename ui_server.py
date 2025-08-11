from fastapi import FastAPI, Request
from summarizers import ui_summarizer
import openai_lib
import llm_utils
import os
import json
from sse_starlette.sse import EventSourceResponse


client = openai_lib.OpenAIClient(os.environ['OPENAI_KEY'])

template = openai_lib.expand_yaml_template('yaml/reasoner-tools.yaml', ('instructions',))


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "'Sup"}

@app.post("/summary")
async def create_summary(payload: dict):
    # Typing the payload as ``dict`` makes FastAPI shut up with the type checking
    summary = ui_summarizer.create_ui_summary(payload, 0)
    print(summary)
    llm_summary = client.run_as_loop(summary, template, llm_utils.handle_fun_call)
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

