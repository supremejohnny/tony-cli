# Layer 2 — Schema-based template composition
#
# Architecture (three actors):
#   1. Composer LLM  — reads schema, produces plan JSON (slide_kind + fill)
#   2. Composer code — clones reusable slides / calls renderers (deterministic)
#   3. Renderers     — build generated slides from content_type + tokens
#
# See layer2/SKILL.md for the full authoring procedure and schema spec.
# See layer2/schemas/ for worked example schemas.
