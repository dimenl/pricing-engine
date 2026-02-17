import json
from pricing_engine import PricingEngine

pricing_nodes = [
    {
        "path": "/material",
        "value": "tpa",
        "display_name": "TPA Material",
        "type": "label",
        "cost": 100,
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": False,
    },
    {
        "path": "/material",
        "value": "pla",
        "display_name": "PLA Material",
        "type": "label",
        "cost": 20,
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": False,
    },
    {
        "path": "/material",
        "value": "resin",
        "display_name": "Resin Material",
        "type": "label",
        "cost": 0,
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": False,
    },
    {
        "path": "/material/resin/color",
        "value": "red",
        "display_name": "Red",
        "type": "label",
        "cost": 30,
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": False,
    },
    {
        "path": "/material/resin/color",
        "value": "blue",
        "display_name": "Blue",
        "type": "label",
        "cost": 30,
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": False,
    },
    {
        "path": "/material/pla/color",
        "value": "blue",
        "display_name": "Blue",
        "type": "label",
        "cost": 300,
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": False,
    },
    {
        "path": "/volume",
        "value": None,
        "display_name": "Volume",
        "type": "numeric",
        "cost": 10,
        "unit": "cm3",
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": True,
    },
    {
        "path": "/time_taken",
        "value": None,
        "display_name": "Time Taken",
        "type": "numeric",
        "cost": 100,
        "currency": "USD",
        "is_available": True,
        "version": 1,
        "is_hidden": True,
    },
]

pricing_strategy = {
    "version": 1,
    "required_inputs": ["/volume", "/time_taken", "/material/*/color"],
    "steps": [
        {
            "id": 1,
            "name": "Volume Cost (Explicit)",
            "mode": "price",
            "inputs": ["/volume"],
        },
        {
            "id": 2,
            "name": "Base Cost Calculation",
            "mode": "add",
            "inputs": ["/volume", "/time_taken", "/material/*/color"],
        },
        {
            "id": 3,
            "name": "Apply Markup",
            "mode": "multiply",
            "inputs": [2, "step__2"],
        },
        {
            "id": 4,
            "name": "Conditional Pricing",
            "mode": "if",
            "condition": {"left": "step__3", "operator": ">", "right": 200},
            "then": "step__3",
            "else": 0,
        },
        {
            "id": 5,
            "name": "Calculate 15% Tax",
            "mode": "percentage",
            "inputs": ["step__4", 15],
        },
        {
            "id": 6,
            "name": "Total with Tax",
            "mode": "add",
            "inputs": ["step__4", "step__5"],
        },
        {
            "id": 7,
            "name": "Apply Discount",
            "mode": "subtract",
            "inputs": ["step__6", 10],
        },
        {
            "id": 8,
            "name": "Clamp Final Price",
            "mode": "clamp",
            "value": "step__7",
            "min": 50,
            "max": 500,
        },
    ],
}

inputs = [
    {"path": "/volume", "value": 2},
    {"path": "/time_taken", "value": 1},
    {"path": "/material/resin/color", "value": "blue"},
]

# Create pricing engine instance
engine = PricingEngine()

# Calculate pricing (pass pricing_nodes as list, not dict)
try:
    result_output = engine.calculate(pricing_nodes, pricing_strategy, inputs)
except ValueError as e:
    print(f"Error: {e}")
    result_output = {"error": str(e)}

# Display result
print(json.dumps(result_output, indent=2))
