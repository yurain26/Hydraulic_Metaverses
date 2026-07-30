# Hydraulic Metaverses

This repository provides the LLM-agent component used in the paper
**“LLM Agent-Driven UAV Swarm for PoI Continual Monitoring in Hydraulic
Metaverses.”** It contains the prompt templates, LLM calls, output schema,
parsing rules, tool interfaces, and agent execution protocol.

## Source files

| File | Content |
|---|---|
| `main_llm.py` | LLM configuration, scheduler prompt, tool interfaces, LangChain agent configuration, and scheduler execution |
| `UAVCalculator.py` | Initial fleet-size prompt, refinement prompt, output schema, LLM calls, and response parser |

## Agent workflow

The scheduler uses four tools in the following order:

1. `UpdateEnvironment` updates the hydraulic monitoring environment;
2. `UAVCountCalculator` estimates the required UAV fleet size;
3. `RoutePlanner` evaluates the fleet and generates UAV routes;
4. `ModelUpdater` updates the continual-learning model with the collected data.

`create_tools` exposes these operations as no-input LangChain tools.
`create_scheduler` registers them with a structured-chat ReAct agent, and
`run_scheduler` starts the decision loop through `agent.run()`.

## LLM configuration

The LLM is constructed with LangChain
`langchain_community.chat_models.ChatOpenAI`.

| Parameter | Value |
|---|---|
| Temperature | `0.3` |
| Model | `agent_name` selected by the experiment setting |
| API key | `OPENAI_API_KEY` environment variable |
| API endpoint | `BASE_URL` environment variable |
| Top-p | ChatOpenAI/provider default |
| Maximum output tokens | ChatOpenAI/provider default |
| Request timeout | ChatOpenAI/provider default |
| Transport retries | ChatOpenAI/provider default |

The model-comparison setting uses `gpt-3.5-turbo`, `gpt-4o`, and `gpt-4.1`.
The scheduler configuration is:

```text
Agent type: STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION
Parsing-error handling: enabled
Maximum scheduler iterations: 9999
Verbose execution trace: enabled
```

## Prompt templates

The complete high-level scheduler prompt is defined as `SCHEDULER_TEMPLATE` in
`main_llm.py`. The two fleet-sizing prompts are defined in `UAVCalculator.py`:

1. `UAVCalculator` estimates the initial UAV count from node, weather, UAV
   capacity, speed, and delay information;
2. `UAVRefiner` adjusts the UAV count using deterministic route-planning
   feedback.

Runtime values are inserted directly into the templates before each LLM call.

## Output schema

Both fleet-sizing calls request one JSON object:

```json
{
  "uav_count": 4,
  "reasoning": "short natural-language explanation"
}
```

`uav_count` is consumed by the decision loop. `reasoning` is retained in the
raw response for inspection and does not affect routing or solution selection.

## Parsing and post-processing

`extract_uav_count` processes an LLM response as follows:

1. normalize whitespace;
2. extract JSON from a `json` Markdown fence, plain Markdown fence,
   triple-quote block, or unwrapped response;
3. remove text before the first `{` and after the last `}`;
4. parse the object with `json.loads`;
5. read `uav_count`, with `count` accepted as a compatible alias;
6. if JSON decoding fails, recover a non-negative integer associated with the
   literal `"uav_count"` key.

The resulting UAV count is passed to the deterministic route planner for
feasibility evaluation. Route feasibility, rather than the natural-language
reasoning field, determines whether a candidate is accepted.

## Invalid and inconsistent outputs

Exceptions raised during an initial-count or refinement call are caught and
logged by the corresponding function, which returns `None`. The surrounding
decision loop treats the unsuccessful call as a failed planning attempt.
Scheduler action-format errors are handled by LangChain through
`handle_parsing_errors=True`.

Logically inconsistent fleet-size proposals cannot directly produce an accepted
solution: every proposed count is evaluated by the deterministic route planner
against the monitoring, energy, and delay requirements.

## Experiment protocol

`experiment_setting` reproduces the three-pass configuration used by the agent
experiments:

| Setting | Passes |
|---|---|
| Refinement comparison (`llm_ref`) | refinement frequencies `1`, `2`, and `3` |
| Model comparison (`llm_agt`) | `gpt-3.5-turbo`, `gpt-4o`, and `gpt-4.1`, with refinement frequency `2` |
| Default | three passes with `gpt-3.5-turbo` and the configured refinement frequency |

Each pass creates a new LLM instance and agent execution. The environment and
route planner provide the runtime state and feedback used at each time slot.
