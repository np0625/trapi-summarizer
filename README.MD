# What this module does

This module produces AI-generated summaries of portions of TRAPI response messages. At present it only targets OpenAI's Responses API.

It takes as input a TRAPI response message and a set of indices that indicate which elements of the `results` array to include in the summary.

It produces a markdown-based preliminary file that collects the relevant data from the entire response message (particularly from the knowledge graph); and passes that preliminary summary to OpenAI along with instructions on how to produce a good summary.

To use this module, you must provide your own OpenAI API key.

## How to install

- Create the dirs `dependencies` and `data` by hand in the project's top level dir
- Obtain the `graphwerks` and `openai_lib` packages by asking the author (these will be published on PyPI at some point)
  and place them in `dependencies/`
- `$ make install`

## How to use

- `$ export OPENAI_KEY='<your openai key>'`
  - Note that to use o3, you must have verified your account
- `$ python driver.py -i <pk | path to file> --list N1,N2,N3 --template <path to yaml config> [--loop | --run]`
  - `-i <pk | path to file>`: If the PK of a pre-run query is provided, it will first be downloaded to a file
    in `data/`. If a file name is provided, it must be valid JSON conforming to a TRAPI Response message.
  - `--list n1[,n2,n3]`: 0-based indices of elements of the TRAPI `response` array to summarize.
  - `--template <yaml file>`: A file providing parameters for the OpenAI Responses API call. See `yaml/` for examples
  - `--run`: Provide this when your API call doesn't use tools and will produce a single response
  - `--loop`: Provide this when your API call contains a tool-calling loop (non-streaming)
  - `--stream`: Provide this to retrieve streaming results from a tool-calling loop
  - `--chunk N`: Number of tokens of streaming textual output to collect before yielding output to the caller (default 10)

If you provide none of `--loop`, `--run`, or `--stream`, the program will print the query request payload and exit without
submitting it to OpenAI.
