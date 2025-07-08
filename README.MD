# What this module does

This module produces AI-generated summaries of portions of TRAPI response messages

It takes as input a TRAPI response message and a set of indices that indicate which elements of the `results` array to include in the summary.

It produces a markdown-based preliminary file that collects the relevant data from the entire response message (particularly from the knowledge graph); and passes that preliminary summary to OpenAI along with instructions on how to produce a good summary.

To use this module, you must provide your own OpenAI API key.

## How to install

- `$ make install` or create the dirs `dependencies` and `data` by hand in the project's top level dir
- Obtain the graphwerks and openai_lib packages by asking the author (these will be published on PyPI at some point)
  and place them in dependencies
- `$ make install`

