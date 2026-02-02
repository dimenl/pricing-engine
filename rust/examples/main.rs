use pricing_engine::*;
use serde_json::json;

fn main() {
    // Define pricing nodes (same as Python main.py)
    let pricing_nodes = vec![
        PricingNode {
            path: "/material".to_string(),
            node_type: "label".to_string(),
            cost: 100.0,
            value: Some(json!("tpa")),
        },
        PricingNode {
            path: "/material".to_string(),
            node_type: "label".to_string(),
            cost: 20.0,
            value: Some(json!("pla")),
        },
        PricingNode {
            path: "/material".to_string(),
            node_type: "label".to_string(),
            cost: 0.0,
            value: Some(json!("resin")),
        },
        PricingNode {
            path: "/material/resin/color".to_string(),
            node_type: "label".to_string(),
            cost: 30.0,
            value: Some(json!("red")),
        },
        PricingNode {
            path: "/material/resin/color".to_string(),
            node_type: "label".to_string(),
            cost: 30.0,
            value: Some(json!("blue")),
        },
        PricingNode {
            path: "/material/pla/color".to_string(),
            node_type: "label".to_string(),
            cost: 300.0,
            value: Some(json!("blue")),
        },
        PricingNode {
            path: "/volume".to_string(),
            node_type: "numeric".to_string(),
            cost: 10.0,
            value: None,
        },
        PricingNode {
            path: "/time_taken".to_string(),
            node_type: "numeric".to_string(),
            cost: 100.0,
            value: None,
        },
    ];

    // Define pricing strategy (same as Python main.py)
    let pricing_strategy_json = json!({
        "version": 1,
        "required_inputs": ["/volume", "/time_taken", "/material/*/color"],
        "steps": [
            {
                "id": 1,
                "name": "Base Cost Calculation",
                "mode": "add",
                "inputs": ["/volume", "/time_taken", "/material/*/color"]
            },
            {
                "id": 2,
                "name": "Apply Markup",
                "mode": "multiply",
                "inputs": [2, "step__1"]
            },
            {
                "id": 3,
                "name": "Conditional Pricing",
                "mode": "if",
                "condition": {
                    "left": "step__2",
                    "operator": ">",
                    "right": 200
                },
                "then": "step__2",
                "else": 0
            },
            {
                "id": 4,
                "name": "Calculate 15% Tax",
                "mode": "percentage",
                "inputs": ["step__3", 15]
            },
            {
                "id": 5,
                "name": "Total with Tax",
                "mode": "add",
                "inputs": ["step__3", "step__4"]
            },
            {
                "id": 6,
                "name": "Apply Discount",
                "mode": "subtract",
                "inputs": ["step__5", 10]
            },
            {
                "id": 7,
                "name": "Clamp Final Price",
                "mode": "clamp",
                "value": "step__6",
                "min": 50,
                "max": 500
            }
        ]
    });

    let pricing_strategy: PricingStrategy =
        serde_json::from_value(pricing_strategy_json).expect("Failed to parse pricing strategy");

    // Define inputs (same as Python main.py)
    let inputs = vec![
        Input {
            path: "/volume".to_string(),
            value: json!(2),
        },
        Input {
            path: "/time_taken".to_string(),
            value: json!(1),
        },
        Input {
            path: "/material/resin/color".to_string(),
            value: json!("blue"),
        },
    ];

    // Create pricing engine instance
    let mut engine = PricingEngine::new();

    // Calculate pricing
    match engine.calculate(pricing_nodes, pricing_strategy, inputs) {
        Ok(result) => {
            println!("{}", serde_json::to_string_pretty(&result).unwrap());
        }
        Err(e) => {
            eprintln!("Error: {}", e);
            println!("{{\"error\": \"{}\"}}", e);
        }
    }
}
