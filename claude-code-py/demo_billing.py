"""Simple billing module with a bug."""


def calculate_total(items, discount=None):
    """Calculate total price for items with optional discount."""
    total = 0
    for item in items:
        total += item["price"] * item["quantity"]

    total = total - discount
    return total
