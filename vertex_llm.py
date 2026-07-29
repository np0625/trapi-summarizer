"""Vertex LLM adapters — Gemini and Anthropic-on-Vertex — that mirror the
interface of ``openai_lib`` so the existing summarizer pipeline, tool dispatch,
and SSE streaming contract are reused unchanged. Only the model provider differs.

Streaming yields the SAME dict shapes as openai_lib's run_as_loop_streaming:
    {"type": "message"|"reasoning", "output_text": str, "n_chunks": int, "done": bool}
    {"type": "function_call_outputs", "outputs": [...]}
``run_as_loop`` / ``run`` return a LoopResult with an ``.output_text`` attribute.

Templates are the existing flat YAML templates (model/reasoning/tools/instructions
at top level). The ``model`` field is OpenAI-specific and is IGNORED here — the
Vertex model comes from the client (CLI/default). ``reasoning`` presence turns on
the provider's "thinking"; ``tools`` (OpenAI function blocks) are translated to
each provider's tool format; ``instructions`` becomes the system prompt.
"""
import os
import json
from dataclasses import dataclass

import yaml

import vertex_creds


# ---------- flat template loading (self-contained; !file support) ----------

class _FileLoader(yaml.SafeLoader):
    pass


def _file_constructor(loader, node):
    rel = loader.construct_scalar(node)
    with open(os.path.join(loader.base_dir, rel), encoding="utf-8") as f:
        return f.read()


_FileLoader.add_constructor("!file", _file_constructor)


def expand_template(path: str) -> dict:
    """Load a flat YAML template, expanding !file references (like openai_lib)."""
    base_dir = os.path.dirname(os.path.abspath(path))
    with open(path, encoding="utf-8") as f:
        loader = _FileLoader(f)
        loader.base_dir = base_dir
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()


# ---------- tool-schema translation (OpenAI function block -> provider) ----------

_GEMINI_DROP = ("additionalProperties", "strict", "$schema")   # not accepted by Gemini Schema
_ANTHROPIC_DROP = ("strict",)                                   # not a JSON-schema keyword


def _clean_schema(schema, drop):
    if isinstance(schema, dict):
        return {k: _clean_schema(v, drop) for k, v in schema.items() if k not in drop}
    if isinstance(schema, list):
        return [_clean_schema(v, drop) for v in schema]
    return schema


def openai_tools_to_gemini(tools):
    from google.genai import types as gt
    decls = []
    for t in tools or []:
        if t.get("type") != "function":
            continue
        decls.append(gt.FunctionDeclaration(
            name=t["name"],
            description=t.get("description", ""),
            parameters=_clean_schema(t.get("parameters", {}), _GEMINI_DROP)))
    return [gt.Tool(function_declarations=decls)] if decls else None


def openai_tools_to_anthropic(tools):
    out = []
    for t in tools or []:
        if t.get("type") != "function":
            continue
        out.append({
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": _clean_schema(t.get("parameters", {}), _ANTHROPIC_DROP),
        })
    return out or None


def _as_text(x):
    return x if isinstance(x, str) else json.dumps(x)


@dataclass
class LoopResult:
    output_text: str
    id: str | None = None


# ---------- Gemini (google-genai on Vertex) ----------

class GeminiClient:
    def __init__(self, model="gemini-2.5-pro", location=None):
        from google import genai
        creds, project = vertex_creds.load_credentials()
        self.model = model
        self._client = genai.Client(vertexai=True, project=project,
                                    location=location or vertex_creds.LOCATION,
                                    credentials=creds)

    def _config(self, template):
        from google.genai import types as gt
        kwargs = {}
        if template.get("instructions"):
            kwargs["system_instruction"] = template["instructions"]
        tools = openai_tools_to_gemini(template.get("tools"))
        if tools:
            kwargs["tools"] = tools
        if "reasoning" in template:
            kwargs["thinking_config"] = gt.ThinkingConfig(include_thoughts=True)
        return gt.GenerateContentConfig(**kwargs)

    @staticmethod
    def _answer_text(resp):
        parts = (resp.candidates[0].content.parts if resp.candidates else None) or []
        return "".join(p.text for p in parts if p.text and not getattr(p, "thought", False))

    def _user(self, text):
        from google.genai import types as gt
        return gt.Content(role="user", parts=[gt.Part(text=text)])

    async def run(self, orig_input, template):
        """Single call, no tool loop (mirrors driver.py --run)."""
        resp = await self._client.aio.models.generate_content(
            model=self.model, contents=[self._user(_as_text(orig_input))],
            config=self._config(template))
        return LoopResult(output_text=self._answer_text(resp))

    async def run_as_loop(self, orig_input, template, funcaller, max_turns=10):
        from google.genai import types as gt
        config = self._config(template)
        contents = [self._user(_as_text(orig_input))]
        for _ in range(max_turns):
            resp = await self._client.aio.models.generate_content(
                model=self.model, contents=contents, config=config)
            parts = (resp.candidates[0].content.parts if resp.candidates else None) or []
            calls = [p.function_call for p in parts if p.function_call]
            if not calls:
                return LoopResult(output_text=self._answer_text(resp))
            contents.append(gt.Content(role="model",
                                       parts=[gt.Part(function_call=fc) for fc in calls]))
            responses = []
            for fc in calls:
                result = await funcaller(fc.name, json.dumps(dict(fc.args or {})))
                responses.append(gt.Part.from_function_response(
                    name=fc.name, response={"result": result}))
            contents.append(gt.Content(role="user", parts=responses))
        raise Exception(f"Tool calling loop exceeded max turns: {max_turns}")

    async def run_as_loop_streaming(self, orig_input, template, funcaller,
                                    turn=1, previous_response_id=None,
                                    max_turns=10, text_chunk=10):
        from google.genai import types as gt
        config = self._config(template)
        contents = [self._user(_as_text(orig_input))]
        for _turn in range(max_turns):
            reason = {"type": "reasoning", "output_text": "", "n_chunks": 0, "done": False}
            answer = {"type": "message", "output_text": "", "n_chunks": 0, "done": False}
            calls = []
            stream = await self._client.aio.models.generate_content_stream(
                model=self.model, contents=contents, config=config)
            async for chunk in stream:
                cand = (chunk.candidates or [None])[0]
                if not cand or not cand.content or not cand.content.parts:
                    continue
                for p in cand.content.parts:
                    if p.function_call:
                        calls.append(p.function_call)
                    elif p.text and getattr(p, "thought", False):
                        reason["output_text"] += p.text
                        reason["n_chunks"] += 1
                        if reason["n_chunks"] % text_chunk == 0:
                            yield reason
                    elif p.text:
                        answer["output_text"] += p.text
                        answer["n_chunks"] += 1
                        if answer["n_chunks"] % text_chunk == 0:
                            yield answer
            if reason["output_text"]:
                reason["done"] = True
                yield reason
            if answer["output_text"]:
                answer["done"] = True
                yield answer
            if not calls:
                return
            contents.append(gt.Content(role="model",
                                       parts=[gt.Part(function_call=fc) for fc in calls]))
            responses, outputs = [], []
            for fc in calls:
                result = await funcaller(fc.name, json.dumps(dict(fc.args or {})))
                outputs.append({"type": "function_call_output",
                                "call_id": fc.name, "output": result})
                responses.append(gt.Part.from_function_response(
                    name=fc.name, response={"result": result}))
            contents.append(gt.Content(role="user", parts=responses))
            yield {"type": "function_call_outputs", "outputs": outputs}
        raise Exception(f"Tool calling loop exceeded max turns: {max_turns}")


# ---------- Anthropic (claude on Vertex) ----------
# Verified working on claude-opus-4-6 (thinking + tools + streaming). Uses adaptive
# thinking; older-generation models (e.g. sonnet-4-5) would instead need
# {"type": "enabled", "budget_tokens": ...} and are not targeted here.

def _anthropic_text(msg):
    return "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")


class AnthropicVertexClient:
    def __init__(self, model="claude-opus-4-6", location=None,
                 max_tokens=32000, timeout=1200.0):
        from anthropic import AsyncAnthropicVertex
        creds, project = vertex_creds.load_credentials()
        self.model = model
        self.max_tokens = max_tokens
        # An explicit timeout is required for non-streaming run()/run_as_loop():
        # the SDK otherwise refuses non-streaming requests whose max_tokens *could*
        # exceed a ~10-min completion (3600*max_tokens/128000 > 600s, i.e. max_tokens
        # > ~21.3k). Setting client.timeout bypasses that guard.
        self._client = AsyncAnthropicVertex(region=location or vertex_creds.LOCATION,
                                            project_id=project, credentials=creds,
                                            timeout=timeout)

    def _kwargs(self, template):
        kw = {"model": self.model, "max_tokens": self.max_tokens}
        if template.get ("instructions"):
            kw["system"] = template["instructions"]
        tools = openai_tools_to_anthropic(template.get("tools"))
        if tools:
            kw["tools"] = tools
        if "reasoning" in template:
            # Adaptive thinking (4.6+ generation, e.g. claude-opus-4-6). display=
            # "summarized" so thinking summaries stream as reasoning events.
            kw["thinking"] = {"type": "adaptive", "display": "summarized"}
        return kw

    async def run(self, orig_input, template):
        msg = await self._client.messages.create(
            messages=[{"role": "user", "content": _as_text(orig_input)}],
            **self._kwargs(template))
        return LoopResult(output_text=_anthropic_text(msg))

    async def run_as_loop(self, orig_input, template, funcaller, max_turns=10):
        kw = self._kwargs(template)
        messages = [{"role": "user", "content": _as_text(orig_input)}]
        for _ in range(max_turns):
            msg = await self._client.messages.create(messages=messages, **kw)
            if msg.stop_reason != "tool_use":
                return LoopResult(output_text=_anthropic_text(msg))
            messages.append({"role": "assistant", "content": msg.content})
            tool_results = []
            for block in msg.content:
                if getattr(block, "type", None) == "tool_use":
                    result = await funcaller(block.name, json.dumps(block.input))
                    tool_results.append({"type": "tool_result",
                                         "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": tool_results})
        raise Exception(f"Tool calling loop exceeded max turns: {max_turns}")

    async def run_as_loop_streaming(self, orig_input, template, funcaller,
                                    turn=1, previous_response_id=None,
                                    max_turns=10, text_chunk=10):
        kw = self._kwargs(template)
        messages = [{"role": "user", "content": _as_text(orig_input)}]
        for _turn in range(max_turns):
            reason = {"type": "reasoning", "output_text": "", "n_chunks": 0, "done": False}
            answer = {"type": "message", "output_text": "", "n_chunks": 0, "done": False}
            async with self._client.messages.stream(messages=messages, **kw) as stream:
                async for event in stream:
                    if event.type != "content_block_delta":
                        continue
                    d = event.delta
                    if getattr(d, "type", None) == "thinking_delta":
                        reason["output_text"] += d.thinking
                        reason["n_chunks"] += 1
                        if reason["n_chunks"] % text_chunk == 0:
                            yield reason
                    elif getattr(d, "type", None) == "text_delta":
                        answer["output_text"] += d.text
                        answer["n_chunks"] += 1
                        if answer["n_chunks"] % text_chunk == 0:
                            yield answer
                final = await stream.get_final_message()
            if reason["output_text"]:
                reason["done"] = True
                yield reason
            if answer["output_text"]:
                answer["done"] = True
                yield answer
            if final.stop_reason != "tool_use":
                return
            messages.append({"role": "assistant", "content": final.content})
            tool_results, outputs = [], []
            for block in final.content:
                if getattr(block, "type", None) == "tool_use":
                    result = await funcaller(block.name, json.dumps(block.input))
                    outputs.append({"type": "function_call_output",
                                    "call_id": block.id, "output": result})
                    tool_results.append({"type": "tool_result",
                                         "tool_use_id": block.id, "content": result})
            messages.append({"role": "user", "content": tool_results})
            yield {"type": "function_call_outputs", "outputs": outputs}
        raise Exception(f"Tool calling loop exceeded max turns: {max_turns}")


# ---------- factory ----------

def make_client(provider, model=None, **kwargs):
    if provider == "gemini":
        return GeminiClient(model=model or "gemini-2.5-pro", **kwargs)
    if provider == "anthropic":
        return AnthropicVertexClient(model=model or "claude-opus-4-6", **kwargs)
    raise ValueError(f"unknown provider: {provider!r} (expected 'gemini' or 'anthropic')")
