from . import bullet, card, flow

REGISTRY = {
    "card": card.render,
    "bullet": bullet.render,
    "flow": flow.render,
}


def get(content_type):
    """Return the render function for a registered content_type, or raise KeyError."""
    if content_type not in REGISTRY:
        raise KeyError(f"Unknown content_type {content_type!r}. Registered: {list(REGISTRY)}")
    return REGISTRY[content_type]
