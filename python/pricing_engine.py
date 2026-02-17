import re
from typing import List, Optional, Union, Tuple, TypedDict, NotRequired, Any


# Type Definitions
class PricingNode(TypedDict):
    """Pricing node configuration used by the pricing engine.

    Only includes fields that are actually used by the PricingEngine class.
    Additional fields like display_name, is_available, version, is_hidden, currency
    may exist but are not used in calculations.
    """

    path: str
    type: str  # "numeric" or "label"
    cost: Union[int, float]
    unit: NotRequired[str]
    currency: NotRequired[str]
    value: NotRequired[
        Optional[Union[str, int, float]]
    ]  # Required for label type, None for numeric


class Input(TypedDict):
    """User input for pricing calculation."""

    path: str
    value: Optional[Union[str, int, float]]


class Condition(TypedDict):
    """Condition specification for conditional steps."""

    left: Union[str, int, float]
    operator: str  # One of: >, <, >=, <=, ==, !=
    right: Union[str, int, float]


class BaseStep(TypedDict):
    """Base step configuration shared by all step types."""

    id: int
    mode: str
    name: NotRequired[str]
    is_hidden: NotRequired[bool]


class AddStep(BaseStep):
    """Addition step configuration."""

    inputs: List[Union[str, int, float]]


class SubtractStep(BaseStep):
    """Subtraction step configuration."""

    inputs: List[Union[str, int, float]]


class MultiplyStep(BaseStep):
    """Multiplication step configuration."""

    inputs: List[Union[str, int, float]]


class DivideStep(BaseStep):
    """Division step configuration."""

    inputs: List[Union[str, int, float]]


class MinStep(BaseStep):
    """Minimum step configuration."""

    inputs: List[Union[str, int, float]]


class MaxStep(BaseStep):
    """Maximum step configuration."""

    inputs: List[Union[str, int, float]]


class PercentageStep(BaseStep):
    """Percentage calculation step configuration."""

    inputs: List[Union[str, int, float]]
    percent: NotRequired[Union[int, float]]


class RoundStep(BaseStep):
    """Rounding step configuration."""

    inputs: List[Union[str, int, float]]
    decimals: NotRequired[int]


class ClampStep(BaseStep):
    """Clamp step configuration."""

    value: Union[str, int, float]
    min: Union[str, int, float]
    max: Union[str, int, float]


class IfStep(BaseStep):
    """Conditional step configuration."""

    condition: Condition
    then: Union[str, int, float]
    else_: NotRequired[Union[str, int, float]]  # Using else_ to avoid Python keyword


# Union of all step types
Step = Union[
    AddStep,
    SubtractStep,
    MultiplyStep,
    DivideStep,
    MinStep,
    MaxStep,
    PercentageStep,
    RoundStep,
    ClampStep,
    IfStep,
]


class PricingStrategy(TypedDict):
    """Pricing strategy configuration."""

    version: int
    required_inputs: NotRequired[List[str]]
    steps: List[Step]


class BreakdownEntry(TypedDict):
    """Breakdown entry in the calculation result."""

    step_id: int
    name: str
    operation: str
    description: str
    inputs: List[Union[int, float]]
    calculation: str
    result: Union[int, float]


class CalculationResult(TypedDict):
    """Result of pricing calculation."""

    final_price: Union[int, float]
    breakdown: List[BreakdownEntry]


class PricingEngine:
    """
    A production-ready pricing calculation engine that processes complex pricing strategies.

    The engine supports multiple operation modes including arithmetic operations (add, subtract,
    multiply, divide), aggregations (min, max), transformations (percentage, round, clamp),
    and conditional logic (if statements).

    Features:
        - Wildcard pattern matching for flexible input matching (e.g., /material/*/color)
        - Step-based calculation with breakdown tracking
        - Comprehensive error messages with validation
        - O(1) node lookups using optimized indexing
        - Regex caching for efficient pattern matching

    Example:
        >>> engine = PricingEngine()
        >>> pricing_nodes = [
        ...     {"path": "/material", "value": "pla", "type": "label", "cost": 20},
        ...     {"path": "/volume", "value": None, "type": "numeric", "cost": 10}
        ... ]
        >>> pricing_strategy = {
        ...     "version": 1,
        ...     "required_inputs": ["/volume", "/material"],
        ...     "steps": [
        ...         {"id": 1, "name": "Base Cost", "mode": "add", "inputs": ["/volume", "/material"]},
        ...         {"id": 2, "name": "Apply Tax", "mode": "percentage", "inputs": ["step__1", 10]}
        ...     ]
        ... }
        >>> inputs = [{"path": "/volume", "value": 5}, {"path": "/material", "value": "pla"}]
        >>> result = engine.calculate(pricing_nodes, pricing_strategy, inputs)
        >>> print(result["final_price"])  # (5*10 + 20) * 10% = 7.0
        7.0

    Supported Operations:
        - **add**: Sum all inputs
        - **subtract**: Subtract inputs from first value
        - **multiply**: Multiply all inputs
        - **divide**: Divide first value by remaining inputs
        - **min**: Return minimum value
        - **max**: Return maximum value
        - **percentage**: Calculate percentage of a value
        - **round**: Round to specified decimal places
        - **clamp**: Constrain value between min and max
        - **if**: Conditional operation with then/else branches
    """

    # Operator mapping for conditions
    OPERATORS: dict[str, callable] = {
        ">": lambda a, b: a > b,
        "<": lambda a, b: a < b,
        ">=": lambda a, b: a >= b,
        "<=": lambda a, b: a <= b,
        "==": lambda a, b: a == b,
        "!=": lambda a, b: a != b,
    }

    def __init__(self, calc_rounding_decimals: int = 2) -> None:
        """Initialize the pricing engine.

        Args:
           calc_rounding_decimals: Number of decimal places for rounding in breakdown.
                                   Set to -1 to disable rounding. Default is 2.
        """
        self.calc_rounding_decimals = calc_rounding_decimals
        """Initialize the pricing engine with an empty regex cache for wildcard pattern matching."""
        self._regex_cache: dict[str, re.Pattern] = {}

    def _format_number(self, value: Union[int, float]) -> str:
        """Format a number for display in calculation breakdown.

        Args:
            value: The number to format

        Returns:
            Formatted string representation
        """
        if self.calc_rounding_decimals == -1:
            return str(value)
        return str(round(value, self.calc_rounding_decimals))

    def calculate(
        self,
        pricing_nodes: Union[List[PricingNode], dict],
        pricing_strategy: PricingStrategy,
        inputs: List[Input],
    ) -> CalculationResult:
        """
        Calculate pricing based on nodes, strategy, and user inputs.

        This is the main entry point for pricing calculations. It validates inputs,
        processes each step in the strategy, and returns a detailed breakdown.

        Args:
            pricing_nodes: List of pricing node configurations or dict mapping paths to nodes.
                Each node defines a cost for a specific path and value combination.
            pricing_strategy: Strategy configuration containing:
                - version: Strategy version number
                - required_inputs: Optional list of required input paths (supports wildcards)
                - steps: List of calculation steps to execute in order
            inputs: List of user inputs, each containing:
                - path: The configuration path (e.g., "/material" or "/volume")
                - value: The selected/provided value for that path

        Returns:
            A dictionary containing:
                - final_price: The final calculated price (result of the last step)
                - breakdown: List of breakdown entries, one per step, showing:
                    - step_id: The step identifier
                    - name: Human-readable step name
                    - operation: Type of operation performed
                    - description: Detailed description
                    - inputs: List of resolved input values
                    - calculation: String representation of the calculation
                    - result: Result of this step

        Raises:
            ValueError: If required inputs are missing, invalid values provided,
                       duplicate inputs detected, or calculation errors occur.

        Example:
            >>> nodes = [{"path": "/volume", "value": None, "type": "numeric", "cost": 10}]
            >>> strategy = {
            ...     "version": 1,
            ...     "steps": [{"id": 1, "mode": "add", "inputs": ["/volume"]}]
            ... }
            >>> inputs = [{"path": "/volume", "value": 5}]
            >>> result = engine.calculate(nodes, strategy, inputs)
            >>> result["final_price"]
            50
        """
        # Store pricing nodes as list for lookups
        if isinstance(pricing_nodes, list):
            self.pricing_nodes_list = pricing_nodes
        else:
            # If dict is provided, convert to list
            self.pricing_nodes_list = list(pricing_nodes.values())

        # OPTIMIZATION: Create indexes for faster lookups
        self._index_nodes_by_path()

        # Validate required inputs
        self._validate_required_inputs(pricing_strategy, inputs)

        # Calculate final input costs
        final_cost_by_path = self._calculate_input_costs(inputs)

        # Apply pricing strategy steps
        step_values = {}
        breakdown = []

        # Create map of raw input values for reference in steps (e.g. price mode)
        input_values = {i["path"]: i.get("value") for i in inputs}

        for step in pricing_strategy["steps"]:
            result, breakdown_entry = self._process_step(
                step, step_values, final_cost_by_path, input_values
            )
            step_values[step["id"]] = result
            if not step.get("is_hidden", False):
                breakdown.append(breakdown_entry)

        # Get final price (last step's value)
        # BUGFIX: Use the last step's actual ID instead of len(step_values)
        if pricing_strategy["steps"]:
            last_step_id = pricing_strategy["steps"][-1]["id"]
            final_price = step_values.get(last_step_id)
        else:
            final_price = 0

        return {"final_price": final_price, "breakdown": breakdown}

    def _index_nodes_by_path(self) -> None:
        """Create indexes for faster node lookups. O(n) preprocessing for O(1) lookups.

        Builds three optimized indexes:
            - nodes_by_path: All nodes grouped by path (for error reporting)
            - label_nodes: (path, value) -> node mapping for label-type nodes
            - numeric_nodes: path -> node mapping for numeric-type nodes
        """
        # OPTIMIZATION: Build specialized indexes
        self.nodes_by_path: dict[
            str, List[PricingNode]
        ] = {}  # path -> [nodes] for error reporting
        self.label_nodes: dict[
            tuple[str, Optional[Union[str, int, float]]], PricingNode
        ] = {}  # (path, value) -> node for O(1) label lookup
        self.numeric_nodes: dict[
            str, PricingNode
        ] = {}  # path -> node for O(1) numeric lookup

        for node in self.pricing_nodes_list:
            path = node["path"]
            # Build path index
            if path not in self.nodes_by_path:
                self.nodes_by_path[path] = []
            self.nodes_by_path[path].append(node)

            # Build specialized indexes
            if node["type"] == "numeric":
                self.numeric_nodes[path] = node
            else:  # label type
                value = node.get("value")
                self.label_nodes[(path, value)] = node

    def _validate_required_inputs(
        self, pricing_strategy: PricingStrategy, inputs: List[Input]
    ) -> None:
        """Validate that all required inputs are present, supporting wildcard patterns.

        Args:
            pricing_strategy: The pricing strategy containing required_inputs list
            inputs: The list of user-provided inputs

        Raises:
            ValueError: If any required input pattern is not matched by provided inputs
        """
        required_inputs = pricing_strategy.get("required_inputs", [])
        if not required_inputs:
            return

        input_paths = {inp["path"] for inp in inputs}

        for required_pattern in required_inputs:
            # OPTIMIZATION: Use cached regex
            regex = self._get_regex(required_pattern)
            matched = any(regex.match(path) for path in input_paths)

            if not matched:
                raise ValueError(
                    f"Required input '{required_pattern}' is missing. "
                    f"Provided inputs: {sorted(input_paths)}"
                )

    def _calculate_input_costs(
        self, inputs: List[Input]
    ) -> dict[str, Union[int, float]]:
        """Calculate the cost for each input based on pricing nodes.

        Args:
            inputs: List of user inputs with paths and values

        Returns:
            Dictionary mapping paths to their calculated costs

        Raises:
            ValueError: If duplicate inputs found, node not found, or invalid values provided
        """
        final_cost_by_path: dict[str, Union[int, float]] = {}

        for inp in inputs:
            path = inp["path"]
            input_value = inp.get("value")
            if path in final_cost_by_path:
                raise ValueError(
                    f"Duplicate input for path '{path}'. Each path must be unique."
                )

            # OPTIMIZATION: O(1) lookup using path+value indexing
            # Try label node first (path, value)
            matching_node = self.label_nodes.get((path, input_value))

            # If not found, try numeric node (path only)
            if not matching_node:
                matching_node = self.numeric_nodes.get(path)

            if not matching_node:
                # Node not found - provide helpful error
                if path not in self.nodes_by_path:
                    raise ValueError(
                        f"No pricing node found for path '{path}'. "
                        f"Available paths: {sorted(self.nodes_by_path.keys())}"
                    )
                else:
                    # Path exists but value doesn't match
                    available_values = [
                        n["value"]
                        for n in self.nodes_by_path[path]
                        if n["type"] == "label"
                    ]
                    raise ValueError(
                        f"Invalid value '{input_value}' for path '{path}'. "
                        f"Available values: {available_values}"
                    )

            # Calculate cost based on node type
            if matching_node["type"] == "numeric":
                if not isinstance(input_value, (int, float)):
                    raise ValueError(
                        f"Invalid numeric input '{input_value}' for path '{path}'."
                    )
                final_cost_by_path[path] = input_value * matching_node["cost"]
            else:
                final_cost_by_path[path] = matching_node["cost"]

        return final_cost_by_path

    def _resolve_value(
        self,
        value: Union[str, int, float],
        step_values: dict[int, Union[int, float]],
        final_cost_by_path: dict[str, Union[int, float]],
    ) -> Union[int, float, List[Union[int, float]]]:
        """Resolve a value that can be a step reference, path, wildcard pattern, or literal.

        Args:
            value: The value to resolve (can be "step__N", "/path", "/path/*/subpath", or literal number)
            step_values: Dictionary of previously calculated step results
            final_cost_by_path: Dictionary of calculated costs by path

        Returns:
            Resolved value (number or list of numbers for wildcards)
        """
        if isinstance(value, str) and value.startswith("step__"):
            step_id = int(value.split("__")[1])
            return step_values.get(step_id, 0)
        elif isinstance(value, str) and "*" in value:
            # Wildcard pattern - return all matching values
            return self._resolve_wildcard_pattern(value, final_cost_by_path)
        elif isinstance(value, str):
            return final_cost_by_path.get(value, 0)
        else:
            return value

    def _get_regex(self, pattern: str) -> re.Pattern:
        """Get or compile a regex pattern for wildcards. OPTIMIZATION: Caches compiled patterns.

        Args:
            pattern: Wildcard pattern (e.g., "/material/*/color")

        Returns:
            Compiled regex pattern
        """
        if pattern not in self._regex_cache:
            regex_str = "^" + pattern.replace("*", "[^/]+") + "$"
            self._regex_cache[pattern] = re.compile(regex_str)
        return self._regex_cache[pattern]

    def _resolve_wildcard_pattern(
        self, pattern: str, final_cost_by_path: dict[str, Union[int, float]]
    ) -> Union[int, float, List[Union[int, float]]]:
        """Resolve a wildcard pattern to all matching values from final_cost_by_path.

        Args:
            pattern: Wildcard pattern to match (e.g., "/material/*/color")
            final_cost_by_path: Dictionary of costs by path

        Returns:
            Single value if one match, list of values if multiple matches

        Raises:
            ValueError: If no paths match the pattern
        """
        # OPTIMIZATION: Use cached regex
        regex = self._get_regex(pattern)

        # Find all matching paths
        matching_values = [
            cost for path, cost in final_cost_by_path.items() if regex.match(path)
        ]

        if not matching_values:
            raise ValueError(
                f"No inputs found matching wildcard pattern '{pattern}'. "
                f"Available paths: {sorted(final_cost_by_path.keys())}"
            )

        # Return list of values if multiple, single value if one
        return matching_values if len(matching_values) > 1 else matching_values[0]

    def _process_step(
        self,
        step: Step,
        step_values: dict[int, Union[int, float]],
        final_cost_by_path: dict[str, Union[int, float]],
        input_values: dict[str, Any],
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process a single pricing strategy step and return result and breakdown entry.

        Args:
            step: The step configuration
            step_values: Dictionary of previously calculated step results
            final_cost_by_path: Dictionary of calculated costs by path

        Returns:
            Tuple of (result_value, breakdown_entry)

        Raises:
            ValueError: If unknown mode or invalid step configuration
        """
        mode = step["mode"]
        step_name = step.get("name", f"Step {step['id']}")

        # Resolve inputs for modes that use them
        resolved_inputs: List[Union[int, float]] = []
        for item in step.get("inputs", []):
            resolved = self._resolve_value(item, step_values, final_cost_by_path)
            # If resolved value is a list (from wildcard), extend instead of append
            if isinstance(resolved, list):
                resolved_inputs.extend(resolved)
            else:
                resolved_inputs.append(resolved)

        # Process based on mode
        if mode == "add":
            return self._process_add(step, step_name, resolved_inputs)
        elif mode == "subtract":
            return self._process_subtract(step, step_name, resolved_inputs)
        elif mode == "multiply":
            return self._process_multiply(step, step_name, resolved_inputs)
        elif mode == "divide":
            return self._process_divide(step, step_name, resolved_inputs)
        elif mode == "min":
            return self._process_min(step, step_name, resolved_inputs)
        elif mode == "max":
            return self._process_max(step, step_name, resolved_inputs)
        elif mode == "percentage":
            return self._process_percentage(step, step_name, resolved_inputs)
        elif mode == "round":
            return self._process_round(step, step_name, resolved_inputs)
        elif mode == "clamp":
            return self._process_clamp(step, step_name, step_values, final_cost_by_path)
        elif mode == "if":
            return self._process_if(step, step_name, step_values, final_cost_by_path)
        elif mode == "price":
            return self._process_price(step, step_name, input_values)
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _process_add(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process addition operation.

        Args:
            step: The step configuration
            step_name: Human-readable name for the step
            resolved_inputs: List of resolved numeric values to add

        Returns:
            Tuple of (sum_result, breakdown_entry)

        Raises:
            ValueError: If no inputs provided
        """
        if not resolved_inputs:
            raise ValueError(f"{step_name}: add requires at least one input")
        result = sum(resolved_inputs)
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Addition",
            "description": f"Sum of {len(resolved_inputs)} values",
            "inputs": resolved_inputs,
            "calculation": " + ".join(self._format_number(v) for v in resolved_inputs),
            "result": result,
        }
        return result, breakdown

    def _process_subtract(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process subtraction operation.

        Args:
            step: The step configuration
            step_name: Human-readable name for the step
            resolved_inputs: List of values, first value minus all remaining values

        Returns:
            Tuple of (result, breakdown_entry)

        Raises:
            ValueError: If no inputs provided
        """
        if not resolved_inputs:
            raise ValueError(f"{step_name}: subtract requires at least one input")
        result = resolved_inputs[0]
        for val in resolved_inputs[1:]:
            result -= val
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Subtraction",
            "description": f"Subtract {len(resolved_inputs) - 1} value(s) from base",
            "inputs": resolved_inputs,
            "calculation": " - ".join(self._format_number(v) for v in resolved_inputs),
            "result": result,
        }
        return result, breakdown

    def _process_multiply(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process multiplication operation.

        Args:
            step: The step configuration
            step_name: Human-readable name for the step
            resolved_inputs: List of values to multiply together

        Returns:
            Tuple of (product_result, breakdown_entry)

        Raises:
            ValueError: If no inputs provided
        """
        if not resolved_inputs:
            raise ValueError(f"{step_name}: multiply requires at least one input")
        result = 1
        for val in resolved_inputs:
            result *= val
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Multiplication",
            "description": f"Product of {len(resolved_inputs)} values",
            "inputs": resolved_inputs,
            "calculation": " × ".join(self._format_number(v) for v in resolved_inputs),
            "result": result,
        }
        return result, breakdown

    def _process_divide(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process division operation.

        Args:
            step: The step configuration
            step_name: Human-readable name for the step
            resolved_inputs: List of values, first divided by all remaining values

        Returns:
            Tuple of (result, breakdown_entry)

        Raises:
            ValueError: If less than two inputs provided or division by zero
        """
        if len(resolved_inputs) < 2:
            raise ValueError(f"{step_name}: divide requires at least two inputs")
        result = resolved_inputs[0]
        for val in resolved_inputs[1:]:
            if val == 0:
                raise ValueError(f"{step_name}: division by zero")
            result /= val
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Division",
            "description": f"Divide {resolved_inputs[0]} by {len(resolved_inputs) - 1} value(s)",
            "inputs": resolved_inputs,
            "calculation": " ÷ ".join(self._format_number(v) for v in resolved_inputs),
            "result": result,
        }
        return result, breakdown

    def _process_min(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process minimum operation.

        Args:
            step: The step configuration
            step_name: Human-readable name for the step
            resolved_inputs: List of values to find minimum from

        Returns:
            Tuple of (minimum_value, breakdown_entry)

        Raises:
            ValueError: If no inputs provided
        """
        if not resolved_inputs:
            raise ValueError(f"{step_name}: min requires at least one input")
        result = min(resolved_inputs)
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Minimum",
            "description": f"Minimum of {len(resolved_inputs)} values",
            "inputs": resolved_inputs,
            "calculation": f"min({', '.join(self._format_number(v) for v in resolved_inputs)})",
            "result": result,
        }
        return result, breakdown

    def _process_max(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process maximum operation.

        Args:
            step: The step configuration
            step_name: Human-readable name for the step
            resolved_inputs: List of values to find maximum from

        Returns:
            Tuple of (maximum_value, breakdown_entry)

        Raises:
            ValueError: If no inputs provided
        """
        if not resolved_inputs:
            raise ValueError(f"{step_name}: max requires at least one input")
        result = max(resolved_inputs)
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Maximum",
            "description": f"Maximum of {len(resolved_inputs)} values",
            "inputs": resolved_inputs,
            "calculation": f"max({', '.join(self._format_number(v) for v in resolved_inputs)})",
            "result": result,
        }
        return result, breakdown

    def _process_percentage(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process percentage calculation.

        Args:
            step: The step configuration (may include 'percent' field)
            step_name: Human-readable name for the step
            resolved_inputs: One value (base) or two values (base, percentage)

        Returns:
            Tuple of (percentage_result, breakdown_entry)

        Raises:
            ValueError: If invalid number of inputs, missing percent, non-numeric percent, or negative percent
        """
        if len(resolved_inputs) == 1:
            percent = step.get("percent")
            if percent is None:
                raise ValueError(
                    f"{step_name}: percentage requires percent in step or two inputs"
                )
            calc_percent = percent
        elif len(resolved_inputs) == 2:
            calc_percent = resolved_inputs[1]
        else:
            raise ValueError(f"{step_name}: percentage allows only one or two inputs")

        # Validate percentage value
        if not isinstance(calc_percent, (int, float)):
            raise ValueError(f"{step_name}: percentage must be a numeric value")
        if calc_percent < 0:
            raise ValueError(
                f"{step_name}: percentage cannot be negative ({calc_percent})"
            )

        result = (resolved_inputs[0] * calc_percent) / 100
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Percentage",
            "description": f"{calc_percent}% of {resolved_inputs[0]}",
            "inputs": resolved_inputs,
            "calculation": f"{self._format_number(resolved_inputs[0])} × {calc_percent}%",
            "result": result,
        }
        return result, breakdown

    def _process_round(
        self, step: Step, step_name: str, resolved_inputs: List[Union[int, float]]
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process round to decimal places operation.

        Args:
            step: The step configuration (may include 'decimals' field)
            step_name: Human-readable name for the step
            resolved_inputs: One value (number to round) or two values (number, decimal places)

        Returns:
            Tuple of (rounded_value, breakdown_entry)

        Raises:
            ValueError: If invalid number of inputs or missing decimals field
        """
        if len(resolved_inputs) == 1:
            decimals = step.get("decimals")
            if decimals is None:
                raise ValueError(
                    f"{step_name}: round requires decimals in step or two inputs"
                )
            value = resolved_inputs[0]
        elif len(resolved_inputs) == 2:
            value = resolved_inputs[0]
            decimals = resolved_inputs[1]
        else:
            raise ValueError(f"{step_name}: round allows only one or two inputs")
        result = round(value, int(decimals))
        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Round",
            "description": f"Round {value} to {int(decimals)} decimal places",
            "inputs": resolved_inputs,
            "calculation": f"round({value}, {int(decimals)})",
            "result": result,
        }
        return result, breakdown

    def _process_clamp(
        self,
        step: Step,
        step_name: str,
        step_values: dict[int, Union[int, float]],
        final_cost_by_path: dict[str, Union[int, float]],
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process clamp operation.

        Args:
            step: The step configuration with value, min, and max fields
            step_name: Human-readable name for the step
            step_values: Dictionary of previously calculated step results
            final_cost_by_path: Dictionary of calculated costs by path

        Returns:
            Tuple of (clamped_value, breakdown_entry)

        Raises:
            ValueError: If min value is greater than max value
        """
        value = self._resolve_value(
            step.get("value", 0), step_values, final_cost_by_path
        )
        min_val = self._resolve_value(
            step.get("min", 0), step_values, final_cost_by_path
        )
        max_val = self._resolve_value(
            step.get("max", 0), step_values, final_cost_by_path
        )

        # Validate clamp parameters
        if min_val > max_val:
            raise ValueError(
                f"{step_name}: min value ({min_val}) cannot be greater than max value ({max_val})"
            )

        result = max(min_val, min(max_val, value))

        clamped = "not clamped"
        if value < min_val:
            clamped = f"clamped to minimum ({min_val})"
        elif value > max_val:
            clamped = f"clamped to maximum ({max_val})"

        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Clamp",
            "description": f"Clamp {value} between {min_val} and {max_val} - {clamped}",
            "inputs": [value, min_val, max_val],
            "calculation": f"clamp({self._format_number(value)}, {self._format_number(min_val)}, {self._format_number(max_val)})",
            "result": result,
        }
        return result, breakdown

    def _process_if(
        self,
        step: Step,
        step_name: str,
        step_values: dict[int, Union[int, float]],
        final_cost_by_path: dict[str, Union[int, float]],
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process conditional (if) operation.

        Args:
            step: The step configuration with condition, then, and else fields
            step_name: Human-readable name for the step
            step_values: Dictionary of previously calculated step results
            final_cost_by_path: Dictionary of calculated costs by path

        Returns:
            Tuple of (conditional_result, breakdown_entry)

        Raises:
            ValueError: If unsupported operator is used
        """
        condition = step.get("condition", {})

        # Resolve condition values
        left_val = self._resolve_value(
            condition.get("left"), step_values, final_cost_by_path
        )
        right_val = self._resolve_value(
            condition.get("right"), step_values, final_cost_by_path
        )

        # Evaluate condition using operator mapping
        operator = condition.get("operator", "==")
        if operator not in self.OPERATORS:
            raise ValueError(f"{step_name}: unsupported operator '{operator}'")
        condition_result = self.OPERATORS[operator](left_val, right_val)

        # Resolve then/else values
        then_val = self._resolve_value(
            step.get("then", 0), step_values, final_cost_by_path
        )
        else_val = self._resolve_value(
            step.get("else", 0), step_values, final_cost_by_path
        )

        # Set result based on condition
        result = then_val if condition_result else else_val

        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Conditional",
            "description": f"If {left_val} {operator} {right_val} then {then_val} else {else_val}",
            "inputs": [left_val, right_val, then_val, else_val],
            "calculation": f"{self._format_number(left_val)} {operator} {self._format_number(right_val)} → {'TRUE' if condition_result else 'FALSE'} → {self._format_number(result)}",
            "result": result,
        }
        return result, breakdown

    def _process_price(
        self,
        step: Step,
        step_name: str,
        input_values: dict[str, Any],
    ) -> Tuple[Union[int, float], BreakdownEntry]:
        """Process price operation (explicit input * cost calculation).

        Args:
            step: The step configuration
            step_name: Human-readable name for the step
            input_values: Dictionary of raw input values by path

        Returns:
            Tuple of (calculated_cost, breakdown_entry)

        Raises:
            ValueError: If input path not found or node missing
        """
        inputs_list = step.get("inputs", [])
        if not inputs_list:
            raise ValueError(f"{step_name}: price mode requires one input path")

        target_path = inputs_list[0]
        if not isinstance(target_path, str):
            raise ValueError(f"{step_name}: price mode input must be a path string")

        # Handle wildcards if present (though typically price mode targets specific inputs)
        # For now, let's assume direct path or resolve wildcard to single path if needed?
        # The user req says "take only the pricing node".
        # Let's support checks.

        # We need the node and the input value.
        # Check if we have an input for this path
        if target_path not in input_values and "*" not in target_path:
            # It might be an optional input that wasn't provided?
            # Or it implies we should look up the node even if no input?
            # Usually "price" implies calculating cost of an INPUT.
            # If input is missing, maybe cost is 0?
            # For now, let's assume it must exist or we error/return 0.
            if target_path in self.numeric_nodes or any(
                target_path == k[0] for k in self.label_nodes
            ):
                # Node exists but no input value provided.
                # If numeric, value is effectively 0 or None?
                # Let's assume 0 for check.
                raw_value = 0
            else:
                raise ValueError(f"{step_name}: Input '{target_path}' not found")
        else:
            raw_value = input_values.get(target_path)

        # Find the pricing node
        # Try numeric first
        calculation_desc = ""
        result = 0

        # Re-implementing the logic cleanly to handle both lookups and formatting
        # Numeric lookup
        node_numeric = self.numeric_nodes.get(target_path)
        # Label lookup
        node_label = self.label_nodes.get((target_path, raw_value))

        node = node_numeric or node_label

        if not node:
            raise ValueError(f"{step_name}: No pricing node found for '{target_path}'")

        cost_per_unit = node["cost"]
        unit = node.get("unit", "")
        currency = node.get("currency", "")

        if node["type"] == "numeric":
            if not isinstance(raw_value, (int, float)):
                if raw_value is None:
                    raw_value = 0
                elif not isinstance(raw_value, (int, float)):
                    raise ValueError(
                        f"{step_name}: Invalid numeric value '{raw_value}'"
                    )
            result = raw_value * cost_per_unit
            # Format: "2 cm3 * 20 INR" or "2 * 20"
            part1 = f"{self._format_number(raw_value)} {unit}".strip()
            part2 = f"{self._format_number(cost_per_unit)} {currency}".strip()
            calculation_desc = f"{part1} * {part2}"
        else:
            # Label
            result = cost_per_unit
            part2 = f"{self._format_number(cost_per_unit)} {currency}".strip()
            calculation_desc = f"{part2} (fixed cost)"

        breakdown = {
            "step_id": step["id"],
            "name": step_name,
            "operation": "Price Calculation",
            "description": f"Calculate cost for {target_path}",
            "inputs": [raw_value],
            "calculation": calculation_desc,
            "result": result,
        }
        return result, breakdown
