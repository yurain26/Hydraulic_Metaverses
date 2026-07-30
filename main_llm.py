"""LLM scheduler excerpt used by the Hydraulic Metaverses Agent.

Only the model configuration, scheduler prompt, and scheduler-agent call are
retained from the paper implementation. Environment, routing, learning, metric,
and visualization code is intentionally excluded from this public excerpt.
"""

import os
from typing import Callable, List

from langchain.agents import AgentType, initialize_agent
from langchain.prompts import StringPromptTemplate
from langchain.tools import BaseTool
from langchain_community.chat_models import ChatOpenAI


# Exact tool order and descriptions supplied to the scheduler prompt.
TOOL_DESCRIPTIONS = {
    "UpdateEnvironment": "Update environment parameters in the smart city. ",
    "UAVCountCalculator": "Calculate optimal number of UAVs based on the updated environment parameters. ",
    "RoutePlanner": "Generate optimized flight paths for UAVs based on the calculated UAV count, and collect bridge data at this time slot. ",
    "ModelUpdater": "Update model parameters based on the collected bridge data at this time slot.",
}


class CallbackTool(BaseTool):
    """Expose a private system operation to the public scheduler as a no-input tool."""

    callback: Callable[[], str]

    def _run(self, *args, **kwargs):
        """Invoke the connected environment, calculator, router, or model callback."""
        return self.callback()


def create_tools(
    update_environment: Callable[[], str],
    calculate_uav_count: Callable[[], str],
    plan_route: Callable[[], str],
    update_model: Callable[[], str],
):
    """Create the four tools in the exact order used by the paper scheduler."""
    callbacks = {
        "UpdateEnvironment": update_environment,
        "UAVCountCalculator": calculate_uav_count,
        "RoutePlanner": plan_route,
        "ModelUpdater": update_model,
    }
    return [
        CallbackTool(
            name=name,
            description=TOOL_DESCRIPTIONS[name],
            callback=callbacks[name],
        )
        for name in TOOL_DESCRIPTIONS
    ]


def experiment_setting(comparison_flag, loop_idx, configured_frequency):
    """Return the model and refinement frequency used in the paper code."""
    agent_name = "gpt-3.5-turbo"
    refining_frequency = configured_frequency

    if comparison_flag == "llm_ref":
        refining_frequency = loop_idx + 1

    if comparison_flag == "llm_agt":
        if loop_idx == 0:
            agent_name = "gpt-3.5-turbo"
        elif loop_idx == 1:
            agent_name = "gpt-4o"
        elif loop_idx == 2:
            agent_name = "gpt-4.1"
        refining_frequency = 5

    return agent_name, refining_frequency


def create_llm(agent_name):
    """Create the LLM with the exact explicitly set inference parameters."""
    return ChatOpenAI(
        temperature=0.3,
        api_key=os.environ.get("OPENAI_API_KEY"),
        base_url=os.environ.get("BASE_URL"),
        model=agent_name,
    )


class CustomPromptTemplate(StringPromptTemplate):
    """Insert the active tool names and descriptions into the scheduler prompt."""

    template: str
    tools: List[BaseTool]
    input_variables: List[str] = ["timeslot_count", "delay_demand"]

    def format(self, **kwargs) -> str:
        """Render the scheduler prompt with runtime values and tool metadata."""
        kwargs["tool_descriptions"] = "\n".join(
            [f"{tool.name}: {tool.description}" for tool in self.tools]
        )
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
        return self.template.format(**kwargs)


# Verbatim scheduler prompt from the paper implementation.
SCHEDULER_TEMPLATE = """
        You are a scheduler in a continuous learning system for a smart city, operating across {timeslot_count} time slots, namely from 0 to {timeslot_count} - 1 time slots,
        while ensuring that each UAV's flight path meets the user's delay requirement of {delay_demand} seconds.
        At each time slot, you are responsible for observing the current environment, calculating the number of UAVs required,
        planning their flight paths, and using the collected data to continuously train a given model.

        ### Available Tools:
        {tool_descriptions}

        ### Response format:
        Action: <tool_name>
        Action Input: <parameters>

        ### Final report should include, and it is best to list the above information in a way that looks good to humans.
        1. The history of flight paths of UAVs for all time slots
        2. The history of accuray of updated model
        """


def create_scheduler(tools, llm):
    """Create the same LangChain scheduler agent used in the paper code."""
    prompt = CustomPromptTemplate(
        template=SCHEDULER_TEMPLATE,
        tools=tools,
        input_variables=[],
    )
    agent = initialize_agent(
        tools=tools,
        llm=llm,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=9999,
    )
    return agent, prompt


def run_scheduler(agent, prompt, timeslot_count, delay_demand):
    """Run the ReAct loop in which the agent selects and invokes registered tools."""
    return agent.run(
        input=prompt.format(
            timeslot_count=timeslot_count,
            delay_demand=delay_demand,
        )
    )
