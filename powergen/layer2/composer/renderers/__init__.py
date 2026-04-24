from . import bullet, card, flow, section_divider, two_column, card_grid

REGISTRY = {
    # Legacy names (kept for backward compat)
    "card": card.render,
    "bullet": bullet.render,
    "flow": flow.render,
    # v3 renderer names (used by STRUCTURE_TO_RENDERER in composer)
    "title_bullets": bullet.render,
    "two_column": two_column.render,
    "card_grid": card_grid.render,
    "section_divider": section_divider.render,
}


def get(name: str):
    if name not in REGISTRY:
        raise KeyError(f"Unknown renderer {name!r}. Registered: {list(REGISTRY)}")
    return REGISTRY[name]
