from fastapi import FastAPI
from summarizers import ui_summarizer
import openai_lib
import llm_utils
import os


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

