use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Value type used throughout the pricing engine
pub type Value = f64;

/// Pricing node configuration used by the pricing engine
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PricingNode {
    pub path: String,
    #[serde(rename = "type")]
    pub node_type: String, // "numeric" or "label"
    pub cost: Value,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub value: Option<serde_json::Value>, // None for numeric, Some(value) for label
}

/// User input for pricing calculation
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Input {
    pub path: String,
    pub value: serde_json::Value,
}

/// Condition specification for conditional steps
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Condition {
    pub left: serde_json::Value,
    pub operator: String,
    pub right: serde_json::Value,
}

/// Step configuration for pricing strategy
#[derive(Debug, Clone, Deserialize, Serialize)]
#[serde(tag = "mode")]
pub enum Step {
    #[serde(rename = "add")]
    Add {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
    },
    #[serde(rename = "subtract")]
    Subtract {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
    },
    #[serde(rename = "multiply")]
    Multiply {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
    },
    #[serde(rename = "divide")]
    Divide {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
    },
    #[serde(rename = "min")]
    Min {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
    },
    #[serde(rename = "max")]
    Max {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
    },
    #[serde(rename = "percentage")]
    Percentage {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
        #[serde(skip_serializing_if = "Option::is_none")]
        percent: Option<Value>,
    },
    #[serde(rename = "round")]
    Round {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        inputs: Vec<serde_json::Value>,
        #[serde(skip_serializing_if = "Option::is_none")]
        decimals: Option<i32>,
    },
    #[serde(rename = "clamp")]
    Clamp {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        value: serde_json::Value,
        min: serde_json::Value,
        max: serde_json::Value,
    },
    #[serde(rename = "if")]
    If {
        id: i32,
        #[serde(skip_serializing_if = "Option::is_none")]
        name: Option<String>,
        condition: Condition,
        then: serde_json::Value,
        #[serde(rename = "else", skip_serializing_if = "Option::is_none")]
        else_: Option<serde_json::Value>,
    },
}

impl Step {
    pub fn id(&self) -> i32 {
        match self {
            Step::Add { id, .. } => *id,
            Step::Subtract { id, .. } => *id,
            Step::Multiply { id, .. } => *id,
            Step::Divide { id, .. } => *id,
            Step::Min { id, .. } => *id,
            Step::Max { id, .. } => *id,
            Step::Percentage { id, .. } => *id,
            Step::Round { id, .. } => *id,
            Step::Clamp { id, .. } => *id,
            Step::If { id, .. } => *id,
        }
    }

    pub fn name(&self) -> String {
        match self {
            Step::Add { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Subtract { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Multiply { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Divide { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Min { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Max { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Percentage { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Round { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::Clamp { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
            Step::If { id, name, .. } => name.clone().unwrap_or_else(|| format!("Step {}", id)),
        }
    }
}

/// Pricing strategy configuration
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct PricingStrategy {
    pub version: i32,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub required_inputs: Option<Vec<String>>,
    pub steps: Vec<Step>,
}

/// Breakdown entry in the calculation result
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct BreakdownEntry {
    pub step_id: i32,
    pub name: String,
    pub operation: String,
    pub description: String,
    pub inputs: Vec<Value>,
    pub calculation: String,
    pub result: Value,
}

/// Result of pricing calculation
#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct CalculationResult {
    pub final_price: Value,
    pub breakdown: Vec<BreakdownEntry>,
}

/// The main pricing engine
pub struct PricingEngine {
    regex_cache: HashMap<String, Regex>,
}

impl PricingEngine {
    /// Create a new pricing engine instance
    pub fn new() -> Self {
        PricingEngine {
            regex_cache: HashMap::new(),
        }
    }

    /// Calculate pricing based on nodes, strategy, and user inputs
    pub fn calculate(
        &mut self,
        pricing_nodes: Vec<PricingNode>,
        pricing_strategy: PricingStrategy,
        inputs: Vec<Input>,
    ) -> Result<CalculationResult, String> {
        // Create indexes for faster lookups
        let (nodes_by_path, label_nodes, numeric_nodes) = self.index_nodes_by_path(&pricing_nodes);

        // Validate required inputs
        self.validate_required_inputs(&pricing_strategy, &inputs)?;

        // Calculate final input costs
        let final_cost_by_path = self.calculate_input_costs(
            &inputs,
            &nodes_by_path,
            &label_nodes,
            &numeric_nodes,
        )?;

        // Apply pricing strategy steps
        let mut step_values: HashMap<i32, Value> = HashMap::new();
        let mut breakdown: Vec<BreakdownEntry> = Vec::new();

        for step in &pricing_strategy.steps {
            let (result, breakdown_entry) =
                self.process_step(step, &step_values, &final_cost_by_path)?;
            step_values.insert(step.id(), result);
            breakdown.push(breakdown_entry);
        }

        // Get final price (last step's value)
        let final_price = if let Some(last_step) = pricing_strategy.steps.last() {
            *step_values.get(&last_step.id()).unwrap_or(&0.0)
        } else {
            0.0
        };

        Ok(CalculationResult {
            final_price,
            breakdown,
        })
    }

    /// Create indexes for faster node lookups
    fn index_nodes_by_path(
        &self,
        pricing_nodes: &[PricingNode],
    ) -> (
        HashMap<String, Vec<PricingNode>>,
        HashMap<(String, String), PricingNode>,
        HashMap<String, PricingNode>,
    ) {
        let mut nodes_by_path: HashMap<String, Vec<PricingNode>> = HashMap::new();
        let mut label_nodes: HashMap<(String, String), PricingNode> = HashMap::new();
        let mut numeric_nodes: HashMap<String, PricingNode> = HashMap::new();

        for node in pricing_nodes {
            nodes_by_path
                .entry(node.path.clone())
                .or_insert_with(Vec::new)
                .push(node.clone());

            if node.node_type == "numeric" {
                numeric_nodes.insert(node.path.clone(), node.clone());
            } else if let Some(value) = &node.value {
                let value_str = match value {
                    serde_json::Value::String(s) => s.clone(),
                    serde_json::Value::Number(n) => n.to_string(),
                    serde_json::Value::Bool(b) => b.to_string(),
                    _ => value.to_string(),
                };
                label_nodes.insert((node.path.clone(), value_str), node.clone());
            }
        }

        (nodes_by_path, label_nodes, numeric_nodes)
    }

    /// Validate that all required inputs are present
    fn validate_required_inputs(
        &mut self,
        pricing_strategy: &PricingStrategy,
        inputs: &[Input],
    ) -> Result<(), String> {
        if let Some(required_inputs) = &pricing_strategy.required_inputs {
            let input_paths: Vec<String> = inputs.iter().map(|i| i.path.clone()).collect();

            for required_pattern in required_inputs {
                let regex = self.get_regex(required_pattern);
                let matched = input_paths.iter().any(|path| regex.is_match(path));

                if !matched {
                    return Err(format!(
                        "Required input '{}' is missing. Provided inputs: {:?}",
                        required_pattern, input_paths
                    ));
                }
            }
        }
        Ok(())
    }

    /// Calculate the cost for each input based on pricing nodes
    fn calculate_input_costs(
        &self,
        inputs: &[Input],
        nodes_by_path: &HashMap<String, Vec<PricingNode>>,
        label_nodes: &HashMap<(String, String), PricingNode>,
        numeric_nodes: &HashMap<String, PricingNode>,
    ) -> Result<HashMap<String, Value>, String> {
        let mut final_cost_by_path: HashMap<String, Value> = HashMap::new();

        for inp in inputs {
            let path = &inp.path;
            if final_cost_by_path.contains_key(path) {
                return Err(format!(
                    "Duplicate input for path '{}'. Each path must be unique.",
                    path
                ));
            }

            let input_value_str = match &inp.value {
                serde_json::Value::String(s) => s.clone(),
                serde_json::Value::Number(n) => n.to_string(),
                serde_json::Value::Bool(b) => b.to_string(),
                serde_json::Value::Null => "null".to_string(),
                _ => inp.value.to_string(),
            };

            // Try label node first
            let matching_node = label_nodes
                .get(&(path.clone(), input_value_str.clone()))
                .or_else(|| numeric_nodes.get(path));

            if let Some(node) = matching_node {
                if node.node_type == "numeric" {
                    if let Some(num) = inp.value.as_f64() {
                        final_cost_by_path.insert(path.clone(), num * node.cost);
                    } else {
                        return Err(format!(
                            "Invalid numeric input '{}' for path '{}'.",
                            inp.value, path
                        ));
                    }
                } else {
                    final_cost_by_path.insert(path.clone(), node.cost);
                }
            } else {
                if !nodes_by_path.contains_key(path) {
                    let available_paths: Vec<&String> = nodes_by_path.keys().collect();
                    return Err(format!(
                        "No pricing node found for path '{}'. Available paths: {:?}",
                        path, available_paths
                    ));
                } else {
                    let available_values: Vec<String> = nodes_by_path
                        .get(path)
                        .unwrap()
                        .iter()
                        .filter(|n| n.node_type == "label")
                        .filter_map(|n| n.value.as_ref().map(|v| v.to_string()))
                        .collect();
                    return Err(format!(
                        "Invalid value '{}' for path '{}'. Available values: {:?}",
                        inp.value, path, available_values
                    ));
                }
            }
        }

        Ok(final_cost_by_path)
    }

    /// Resolve a value that can be a step reference, path, wildcard pattern, or literal
    fn resolve_value(
        &mut self,
        value: &serde_json::Value,
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<Vec<Value>, String> {
        if let Some(s) = value.as_str() {
            if s.starts_with("step__") {
                let step_id = s[6..]
                    .parse::<i32>()
                    .map_err(|_| format!("Invalid step reference: {}", s))?;
                Ok(vec![*step_values.get(&step_id).unwrap_or(&0.0)])
            } else if s.contains('*') {
                self.resolve_wildcard_pattern(s, final_cost_by_path)
            } else {
                Ok(vec![*final_cost_by_path.get(s).unwrap_or(&0.0)])
            }
        } else if let Some(num) = value.as_f64() {
            Ok(vec![num])
        } else if let Some(num) = value.as_i64() {
            Ok(vec![num as f64])
        } else {
            Ok(vec![0.0])
        }
    }

    /// Get or compile a regex pattern for wildcards
    fn get_regex(&mut self, pattern: &str) -> Regex {
        if let Some(regex) = self.regex_cache.get(pattern) {
            regex.clone()
        } else {
            let regex_str = format!("^{}$", pattern.replace('*', "[^/]+"));
            let regex = Regex::new(&regex_str).unwrap();
            self.regex_cache.insert(pattern.to_string(), regex.clone());
            regex
        }
    }

    /// Resolve a wildcard pattern to all matching values
    fn resolve_wildcard_pattern(
        &mut self,
        pattern: &str,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<Vec<Value>, String> {
        let regex = self.get_regex(pattern);
        let matching_values: Vec<Value> = final_cost_by_path
            .iter()
            .filter(|(path, _)| regex.is_match(path))
            .map(|(_, &cost)| cost)
            .collect();

        if matching_values.is_empty() {
            let available_paths: Vec<&String> = final_cost_by_path.keys().collect();
            return Err(format!(
                "No inputs found matching wildcard pattern '{}'. Available paths: {:?}",
                pattern, available_paths
            ));
        }

        Ok(matching_values)
    }

    /// Process a single pricing strategy step
    fn process_step(
        &mut self,
        step: &Step,
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        match step {
            Step::Add { id, name, inputs } => {
                self.process_add(*id, name.as_deref(), inputs, step_values, final_cost_by_path)
            }
            Step::Subtract { id, name, inputs } => self.process_subtract(
                *id,
                name.as_deref(),
                inputs,
                step_values,
                final_cost_by_path,
            ),
            Step::Multiply { id, name, inputs } => self.process_multiply(
                *id,
                name.as_deref(),
                inputs,
                step_values,
                final_cost_by_path,
            ),
            Step::Divide { id, name, inputs } => {
                self.process_divide(*id, name.as_deref(), inputs, step_values, final_cost_by_path)
            }
            Step::Min { id, name, inputs } => {
                self.process_min(*id, name.as_deref(), inputs, step_values, final_cost_by_path)
            }
            Step::Max { id, name, inputs } => {
                self.process_max(*id, name.as_deref(), inputs, step_values, final_cost_by_path)
            }
            Step::Percentage {
                id,
                name,
                inputs,
                percent,
            } => self.process_percentage(
                *id,
                name.as_deref(),
                inputs,
                *percent,
                step_values,
                final_cost_by_path,
            ),
            Step::Round {
                id,
                name,
                inputs,
                decimals,
            } => self.process_round(
                *id,
                name.as_deref(),
                inputs,
                *decimals,
                step_values,
                final_cost_by_path,
            ),
            Step::Clamp {
                id,
                name,
                value,
                min,
                max,
            } => self.process_clamp(
                *id,
                name.as_deref(),
                value,
                min,
                max,
                step_values,
                final_cost_by_path,
            ),
            Step::If {
                id,
                name,
                condition,
                then,
                else_,
            } => self.process_if(
                *id,
                name.as_deref(),
                condition,
                then,
                else_.as_ref(),
                step_values,
                final_cost_by_path,
            ),
        }
    }

    fn resolve_inputs(
        &mut self,
        inputs: &[serde_json::Value],
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<Vec<Value>, String> {
        let mut resolved: Vec<Value> = Vec::new();
        for item in inputs {
            let vals = self.resolve_value(item, step_values, final_cost_by_path)?;
            resolved.extend(vals);
        }
        Ok(resolved)
    }

    /// Process addition operation
    fn process_add(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        if resolved_inputs.is_empty() {
            return Err(format!("{}: add requires at least one input", step_name));
        }

        let result: Value = resolved_inputs.iter().sum();
        let calculation = resolved_inputs
            .iter()
            .map(|v| format!("{:.2}", v))
            .collect::<Vec<_>>()
            .join(" + ");

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Addition".to_string(),
                description: format!("Sum of {} values", resolved_inputs.len()),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process subtraction operation
    fn process_subtract(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        if resolved_inputs.is_empty() {
            return Err(format!("{}: subtract requires at least one input", step_name));
        }

        let mut result = resolved_inputs[0];
        for &val in &resolved_inputs[1..] {
            result -= val;
        }

        let calculation = resolved_inputs
            .iter()
            .map(|v| format!("{:.2}", v))
            .collect::<Vec<_>>()
            .join(" - ");

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Subtraction".to_string(),
                description: format!(
                    "Subtract {} value(s) from base",
                    resolved_inputs.len() - 1
                ),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process multiplication operation
    fn process_multiply(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        if resolved_inputs.is_empty() {
            return Err(format!("{}: multiply requires at least one input", step_name));
        }

        let mut result = 1.0;
        for &val in &resolved_inputs {
            result *= val;
        }

        let calculation = resolved_inputs
            .iter()
            .map(|v| format!("{:.2}", v))
            .collect::<Vec<_>>()
            .join(" × ");

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Multiplication".to_string(),
                description: format!("Product of {} values", resolved_inputs.len()),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process division operation
    fn process_divide(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        if resolved_inputs.len() < 2 {
            return Err(format!("{}: divide requires at least two inputs", step_name));
        }

        let mut result = resolved_inputs[0];
        for &val in &resolved_inputs[1..] {
            if val == 0.0 {
                return Err(format!("{}: division by zero", step_name));
            }
            result /= val;
        }

        let calculation = resolved_inputs
            .iter()
            .map(|v| format!("{:.2}", v))
            .collect::<Vec<_>>()
            .join(" ÷ ");

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Division".to_string(),
                description: format!(
                    "Divide {} by {} value(s)",
                    resolved_inputs[0],
                    resolved_inputs.len() - 1
                ),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process minimum operation
    fn process_min(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        if resolved_inputs.is_empty() {
            return Err(format!("{}: min requires at least one input", step_name));
        }

        let result = resolved_inputs
            .iter()
            .cloned()
            .fold(f64::INFINITY, f64::min);
        let calculation = format!(
            "min({})",
            resolved_inputs
                .iter()
                .map(|v| format!("{:.2}", v))
                .collect::<Vec<_>>()
                .join(", ")
        );

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Minimum".to_string(),
                description: format!("Minimum of {} values", resolved_inputs.len()),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process maximum operation
    fn process_max(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        if resolved_inputs.is_empty() {
            return Err(format!("{}: max requires at least one input", step_name));
        }

        let result = resolved_inputs
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let calculation = format!(
            "max({})",
            resolved_inputs
                .iter()
                .map(|v| format!("{:.2}", v))
                .collect::<Vec<_>>()
                .join(", ")
        );

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Maximum".to_string(),
                description: format!("Maximum of {} values", resolved_inputs.len()),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process percentage calculation
    fn process_percentage(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        percent: Option<Value>,
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        let calc_percent = if resolved_inputs.len() == 1 {
            percent.ok_or_else(|| {
                format!(
                    "{}: percentage requires percent in step or two inputs",
                    step_name
                )
            })?
        } else if resolved_inputs.len() == 2 {
            resolved_inputs[1]
        } else {
            return Err(format!(
                "{}: percentage allows only one or two inputs",
                step_name
            ));
        };

        if calc_percent < 0.0 {
            return Err(format!(
                "{}: percentage cannot be negative ({})",
                step_name, calc_percent
            ));
        }

        let result = (resolved_inputs[0] * calc_percent) / 100.0;
        let calculation = format!("{:.2} × {}%", resolved_inputs[0], calc_percent);

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Percentage".to_string(),
                description: format!("{}% of {}", calc_percent, resolved_inputs[0]),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process round to decimal places operation
    fn process_round(
        &mut self,
        id: i32,
        name: Option<&str>,
        inputs: &[serde_json::Value],
        decimals: Option<i32>,
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));
        let resolved_inputs = self.resolve_inputs(inputs, step_values, final_cost_by_path)?;

        let (value, dec) = if resolved_inputs.len() == 1 {
            let d = decimals.ok_or_else(|| {
                format!(
                    "{}: round requires decimals in step or two inputs",
                    step_name
                )
            })?;
            (resolved_inputs[0], d)
        } else if resolved_inputs.len() == 2 {
            (resolved_inputs[0], resolved_inputs[1] as i32)
        } else {
            return Err(format!(
                "{}: round allows only one or two inputs",
                step_name
            ));
        };

        let multiplier = 10_f64.powi(dec);
        let result = (value * multiplier).round() / multiplier;
        let calculation = format!("round({}, {})", value, dec);

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Round".to_string(),
                description: format!("Round {} to {} decimal places", value, dec),
                inputs: resolved_inputs,
                calculation,
                result,
            },
        ))
    }

    /// Process clamp operation
    fn process_clamp(
        &mut self,
        id: i32,
        name: Option<&str>,
        value: &serde_json::Value,
        min: &serde_json::Value,
        max: &serde_json::Value,
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));

        let val = self.resolve_value(value, step_values, final_cost_by_path)?[0];
        let min_val = self.resolve_value(min, step_values, final_cost_by_path)?[0];
        let max_val = self.resolve_value(max, step_values, final_cost_by_path)?[0];

        if min_val > max_val {
            return Err(format!(
                "{}: min value ({}) cannot be greater than max value ({})",
                step_name, min_val, max_val
            ));
        }

        let result = val.max(min_val).min(max_val);

        let clamped = if val < min_val {
            format!("clamped to minimum ({})", min_val)
        } else if val > max_val {
            format!("clamped to maximum ({})", max_val)
        } else {
            "not clamped".to_string()
        };

        let calculation = format!("clamp({:.2}, {:.2}, {:.2})", val, min_val, max_val);

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Clamp".to_string(),
                description: format!(
                    "Clamp {} between {} and {} - {}",
                    val, min_val, max_val, clamped
                ),
                inputs: vec![val, min_val, max_val],
                calculation,
                result,
            },
        ))
    }

    /// Process conditional (if) operation
    fn process_if(
        &mut self,
        id: i32,
        name: Option<&str>,
        condition: &Condition,
        then: &serde_json::Value,
        else_: Option<&serde_json::Value>,
        step_values: &HashMap<i32, Value>,
        final_cost_by_path: &HashMap<String, Value>,
    ) -> Result<(Value, BreakdownEntry), String> {
        let step_name = name.map(|s| s.to_string()).unwrap_or_else(|| format!("Step {}", id));

        let left_val = self.resolve_value(&condition.left, step_values, final_cost_by_path)?[0];
        let right_val = self.resolve_value(&condition.right, step_values, final_cost_by_path)?[0];

        let condition_result = match condition.operator.as_str() {
            ">" => left_val > right_val,
            "<" => left_val < right_val,
            ">=" => left_val >= right_val,
            "<=" => left_val <= right_val,
            "==" => left_val == right_val,
            "!=" => left_val != right_val,
            _ => {
                return Err(format!(
                    "{}: unsupported operator '{}'",
                    step_name, condition.operator
                ))
            }
        };

        let then_val = self.resolve_value(then, step_values, final_cost_by_path)?[0];
        let else_val = if let Some(e) = else_ {
            self.resolve_value(e, step_values, final_cost_by_path)?[0]
        } else {
            0.0
        };

        let result = if condition_result { then_val } else { else_val };

        let calculation = format!(
            "{:.2} {} {:.2} → {} → {:.2}",
            left_val,
            condition.operator,
            right_val,
            if condition_result { "TRUE" } else { "FALSE" },
            result
        );

        Ok((
            result,
            BreakdownEntry {
                step_id: id,
                name: step_name.to_string(),
                operation: "Conditional".to_string(),
                description: format!(
                    "If {} {} {} then {} else {}",
                    left_val, condition.operator, right_val, then_val, else_val
                ),
                inputs: vec![left_val, right_val, then_val, else_val],
                calculation,
                result,
            },
        ))
    }
}

impl Default for PricingEngine {
    fn default() -> Self {
        Self::new()
    }
}
