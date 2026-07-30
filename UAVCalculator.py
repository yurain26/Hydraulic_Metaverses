import json
import re


def extract_uav_count(response_text: str) -> int:
    """
    Extracts the 'uav_count' value from a JSON string in various formats.
    
    Handles:
    - JSON wrapped in ```json ... ``` code blocks
    - JSON wrapped in triple backticks without language specifier
    - JSON wrapped in triple quotes
    - Loose JSON strings without code blocks
    - Various whitespace and formatting differences
    
    Args:
        response_text (str): String containing JSON data
        
    Returns:
        int: The value of 'uav_count'
        
    Raises:
        ValueError: If parsing fails or 'uav_count' not found
    """
    # Normalize input: remove extra spaces and newlines
    normalized_text = re.sub(r'\s+', ' ', response_text).strip()
    
    # Pattern 1: Match ```json ... ``` blocks
    json_block_match = re.search(r'```json(.*?)```', normalized_text, re.DOTALL)
    if not json_block_match:
        # Pattern 2: Match ``` ... ``` blocks (no language)
        json_block_match = re.search(r'```(.*?)```', normalized_text, re.DOTALL)
    
    # Pattern 3: Match """ ... """ blocks
    if not json_block_match:
        json_block_match = re.search(r'"""(.*?)"""', normalized_text, re.DOTALL)
    
    # Extract JSON string from found block or use full text
    json_str = json_block_match.group(1).strip() if json_block_match else normalized_text
    
    # Final cleanup: remove any remaining non-JSON characters
    json_str = re.sub(r'^[^{]*', '', json_str)  # Remove prefix before {
    json_str = re.sub(r'[^}]*$', '', json_str)  # Remove suffix after }
    
    try:
        data = json.loads(json_str)
        if 'uav_count' in data:
            return data['uav_count']
        elif 'count' in data:  # Handle alternative key names
            return data['count']
        else:
            raise ValueError("'uav_count' key not found in JSON")
    except json.JSONDecodeError as e:
        # Attempt manual extraction as fallback
        count_match = re.search(r'"uav_count"\s*:\s*(\d+)', json_str)
        if count_match:
            return int(count_match.group(1))
        raise ValueError(f"Invalid JSON format: {str(e)}")
    except Exception as e:
        raise ValueError(f"Extraction failed: {str(e)}")


def UAVCalculator(llm, env):
    """Ask the LLM for an initial UAV count based on the current environment."""
    all_environment_information = env._get_network_info()

    prompt = f"""
        ### UAV Fleet Optimization Calculator
        You are an expert UAV fleet planner. Determine the optimal number of UAVs 
        needed to inspect all bridges while balancing:
        - Task completion (all bridges must be monitored)
        - Enenrgy efficiency (minimize wasted UAV capacity)
        - Delay ensurence (the delay of each UAV fleet meet user delay demand)

        ### Current Environment Analysis
        1. Smart city environment with weather:
        - Bridges and AP information: {all_environment_information['nodes']}
        - Weather zones: {all_environment_information['weather_regions']}
        2. UAV specifications:
        - Speed: {all_environment_information['uav_speed']} m/s
        - Energy capacity: {all_environment_information['uav_capacity']} J
        - Delay demand : {all_environment_information['delay_demand']} s
        
        ### Decision Process
        - Analyze the environment and historical data
        - Provide final UAV count within constraints

        Return ONLY this JSON (NO other text, NO explanations):
        {{
            "uav_count": <minimal integer satisfying all constraints>,
            "reasoning": "<50-word max explanation>"
        }}
        """

    messages = [{"role": "user", "content": prompt}]

    try:
        response = llm.invoke(messages)
        print(response.content)
        return extract_uav_count(response.content)
    except Exception as e:
        print(f"The call to the llm function during UAVCalculator failed: {e}")


def UAVRefiner(llm, feedback):
    """Ask the LLM to refine the UAV count using route-planning feedback."""
    prompt = f"""
        ### UAV Fleet Optimization Calculator
        You are an UAV quantity optimizer. Analyze the feedback to adjust UAV count using these strict rules:

        ### Key Parameters
        - `SCALING_FACTOR = 0.5` (since values are normalized 0-1)
        - Values may exceed 1.0 in failure scenarios
        - Current UAV count = first integer in feedback

        ### Data Extraction Rules
        - **Feedback**:
        - `current_count` = first integer in feedback
        - **Success Feedback**:
        - `E_remain` = float after "remaining available energy... is"
        - `D_remain` = float after "remaining available travel delay... is"
        - **Failure Feedback**:
        - `E_excess` = float after "average excess energy consumption of"
        - `D_excess` = float after "average excess travel delay of"
        
        ### Feedback Interpretation
        1. **Success Scenario** (if "successful" in feedback):
        - Extract: 
            - Remaining energy ratio (`E_remain`)
            - Remaining delay ratio (`D_remain`)
        - Action: **Reduce** UAV count
        - Adjustment: 
            ```python
            reduction = ceil((E_remain + D_remain) * SCALING_FACTOR)
            new_count = max(1, current_count - reduction)
            ```

        2. **Failure Scenario** (if "failed" in feedback):
        - Extract:
            - Excess energy ratio (`E_excess`)
            - Excess delay ratio (`D_excess`)
        - Action: **Increase** UAV count
        - Adjustment:
            ```python
            increase = ceil((E_excess + D_excess) * SCALING_FACTOR)
            new_count = current_count + increase
            ```

        ### Optimization Constraints
        - Minimum UAV count = 2
        - Use exact values from feedback (ignore counts)
        - Apply ceiling function to adjustments
        - Round final count to nearest integer

        ### Output Format
        Return ONLY pure JSON:
        {{
            "uav_count": <optimized integer>,
            "reasoning": "<20-word explanation>"
        }}

        ### Current Feedback
        {feedback}
        """

    messages = [{"role": "user", "content": prompt}]

    try:
        response = llm.invoke(messages)
        print(response.content)
        return extract_uav_count(response.content)
    except Exception as e:
        print(f"The call to the llm function during UAVCalculator failed: {e}")
