# Hydraulic Metaverses

This repository contains the LLM-agent component used in the paper
**“LLM Agent-Driven UAV Swarm for PoI Continual Monitoring in Hydraulic
Metaverses.”** It is intentionally limited to the files needed to disclose the prompts,
LLM calls, output parsing, and high-level agent protocol. The
UAV routing implementation, learning model, environment, data, and plotting code
are not included.

## Included source files

| File | Disclosed content |
|---|---|
| `main_llm.py` | Minimal excerpt containing model selection and construction, scheduler prompt, LangChain agent type, parsing-error setting, maximum iterations, and scheduler call |
| `UAVCalculator.py` | Minimal excerpt containing the active initial-count prompt, refinement prompt, output schema, LLM calls, and parsing rules |

Both Python files are minimal extractions from the paper source. Unrelated
environment, routing, training, metric, TensorBoard, and visualization code has
been removed from `main_llm.py`. Unused imports and the inactive
`UAVFinsher`/minimum-finding code have been removed from `UAVCalculator.py`.
These reductions do not change the active prompts or explicitly set LLM/agent
parameters.

The four tools are exposed through `create_tools` in their original order:
`UpdateEnvironment`, `UAVCountCalculator`, `RoutePlanner`, and `ModelUpdater`.
Each public tool delegates to a no-input callback, keeping the environment,
routing, and training internals private. `create_scheduler` registers these
tools with the structured-chat ReAct agent, and `run_scheduler` starts the loop;
tool selection and invocation then occur inside LangChain's `agent.run()`.

## Exact LLM configuration in the source

The LLM is constructed in `main_llm.py` using LangChain
`langchain_community.chat_models.ChatOpenAI` with:

- `temperature=0.3`;
- `model=agent_name`;
- API key from `OPENAI_API_KEY`;
- endpoint from `BASE_URL`.

The compared model names in the `llm_agt` branch are `gpt-3.5-turbo`, `gpt-4o`,
and `gpt-4.1`. Outside that branch, the model is `gpt-3.5-turbo`. `top_p`, maximum
output tokens, timeout, transport retry count, and model seed are not explicitly
set in the original code and therefore use the installed LangChain/provider
defaults. No package lock file or immutable model snapshot identifier was
recorded by the original implementation; this limitation should be stated in
the manuscript rather than replaced with guessed values.

The scheduler uses
`STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION`,
`handle_parsing_errors=True`, and `max_iterations=9999`.

## Prompt templates and output schemas

The scheduler prompt appears verbatim in `main_llm.py`. The following prompts
appear verbatim in `UAVCalculator.py`:

1. initial fleet-size estimation (`UAVCalculator`);
2. fleet-size refinement from deterministic routing feedback (`UAVRefiner`);

The active fleet-size calls request a JSON object with:

```json
{
  "uav_count": 4,
  "reasoning": "short natural-language explanation"
}
```

Only `uav_count` is used by the decision loop. `reasoning` is printed as part of
the raw response but is not used for routing or candidate selection.

## Parsing and post-processing in the original implementation

`extract_uav_count` performs the following operations:

1. collapses whitespace;
2. accepts JSON in a `json` Markdown fence, a plain Markdown fence, a
   triple-quote block, or unwrapped text;
3. removes text before the first `{` and after the last `}`;
4. parses with `json.loads`;
5. reads `uav_count`, with `count` accepted as a backward-compatible alias;
6. if JSON decoding fails, searches for a non-negative integer associated with
   the literal `"uav_count"` key.

The original parser does not enforce an integer type, minimum/maximum fleet
size, or consistency with the preceding route result. No additional rounding or
clipping is applied after parsing.

## Invalid or inconsistent outputs

The original application has no application-level retry or deterministic
fallback for the fleet-size calls. An exception in `UAVCalculator`,
or `UAVRefiner` is caught locally, an error is printed, and the
function implicitly returns `None`. Downstream route handling is outside the
scope of this minimal LLM-interface release. At scheduler level, LangChain is configured with
`handle_parsing_errors=True`; this applies to scheduler tool-action parsing, not
to the fleet-size JSON parser.

## Actual loop and repeated-run behavior

`main_llm.py` executes three outer loops. Their meaning depends on
`comparison_flag`:

- for `llm_ref`, loop indices 0, 1, and 2 set `refining_frequency` to 1, 2, and
  3 respectively;
- for `llm_agt`, the three loops use `gpt-3.5-turbo`, `gpt-4o`, and `gpt-4.1`,
  each with `refining_frequency=2`;
- otherwise all three loops use `gpt-3.5-turbo`, while
  `refining_frequency` comes from the configuration.

The original three outer loops are comparison conditions, not a formally seeded
independent repeated-run protocol. Environment weather generation uses a
time-derived seed when no seed is supplied. Therefore, the source does not
support a claim of exactly repeatable environment instances across those loops.
This is an implementation limitation that should be reported explicitly.
