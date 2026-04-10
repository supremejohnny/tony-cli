from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="powergen",
        description="PowerGen — AI presentation generator",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM client (no API calls, for testing)",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-6",
        metavar="MODEL",
        help="Anthropic model to use (default: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--no-vision",
        action="store_true",
        help="Skip image/vision processing during distillation (reduces API cost)",
    )

    sub = parser.add_subparsers(dest="cmd")

    create_p = sub.add_parser("create", help="Generate a presentation plan")
    create_p.add_argument("topic", help="Topic or description of the presentation")

    revise_p = sub.add_parser("revise", help="Revise the current plan with feedback")
    revise_p.add_argument("feedback", help="What to change in the plan")

    sub.add_parser("approve", help="Approve plan and build slide spec")

    render_p = sub.add_parser("render", help="Render the approved spec to .pptx")
    render_p.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Output .pptx path (default: <title>.pptx in current directory)",
    )

    template_p = sub.add_parser("template", help="Fill a .pptx template with AI-generated content")
    template_p.add_argument("brief", help="Description of the content to generate")
    template_p.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Output .pptx path (default: <template>-filled.pptx)",
    )

    distill_p = sub.add_parser("distill", help="Distill workspace files into .powergen_distill/")
    distill_p.add_argument(
        "--force",
        action="store_true",
        help="Re-distill even if a file has not changed",
    )
    distill_p.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        metavar="MODEL",
        help="Model for distillation (default: claude-haiku-4-5-20251001)",
    )

    fill_p = sub.add_parser("fill", help="Fill a template using the Pattern Catalog (Phase 2+3 pipeline)")
    fill_p.add_argument("brief", help="Description of the content to generate")
    fill_p.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Output .pptx path (default: <template>-filled.pptx)",
    )
    fill_p.add_argument(
        "--plan-only",
        action="store_true",
        help="Print the content plan JSON and exit without writing a .pptx",
    )

    catalog_p = sub.add_parser("catalog", help="Analyze template PPTX and generate pattern catalog into .powergen_catalog/")
    catalog_p.add_argument(
        "--force",
        action="store_true",
        help="Re-catalog even if the template has not changed",
    )
    catalog_p.add_argument(
        "--model",
        default="claude-haiku-4-5-20251001",
        metavar="MODEL",
        help="Model for catalog analysis (default: claude-haiku-4-5-20251001)",
    )

    sub.add_parser("status", help="Show current project stage")
    sub.add_parser("reset", help="Reset project state to INIT")

    args = parser.parse_args(argv)

    from .mock_client import make_llm_client
    from .state import ProjectState, StateError
    from .workspace import scan_workspace

    state = ProjectState.load(Path.cwd())
    workspace = scan_workspace()
    client = make_llm_client(mock=args.mock, model=args.model)

    try:
        if args.cmd == "create":
            from .planner import generate_plan
            print("Generating plan…")
            plan = generate_plan(args.topic, workspace, client, state)
            print(f"\nPlan ready — {len(plan.slide_summaries)} slides")
            print(f"Overview: {plan.overview}")
            if plan.open_questions:
                print("Open questions:")
                for q in plan.open_questions:
                    print(f"  · {q}")

        elif args.cmd == "revise":
            from .planner import revise_plan
            print("Revising plan…")
            plan = revise_plan(args.feedback, workspace, client, state)
            print(f"\nRevised — now {len(plan.slide_summaries)} slides")

        elif args.cmd == "approve":
            from .spec_builder import build_spec
            if state.plan is None:
                print("Error: no plan yet. Run 'powergen create <topic>' first.", file=sys.stderr)
                return 1
            print("[1/2] Locking plan…")
            print("[2/2] Building slide spec…")
            spec = build_spec(state.plan, workspace, client)
            state.advance_to_approved(spec)
            print(f"\nApproved — {len(spec.slides)} slides ready to render")
            print(f"Title: {spec.title}")

        elif args.cmd == "render":
            from .renderer import render_presentation
            if state.spec is None:
                print("Error: no approved spec. Run 'powergen approve' first.", file=sys.stderr)
                return 1
            template_path = None
            if state.spec.theme_reference:
                candidate = Path.cwd() / state.spec.theme_reference
                if candidate.exists():
                    template_path = candidate
            output_path = Path(args.output) if args.output else None
            out = render_presentation(state.spec, output_path=output_path, template_path=template_path)
            state.advance_to_rendered(str(out))
            print(f"\nRendered: {out}")

        elif args.cmd == "template":
            from .distiller import run_distill
            from .template_filler import fill_template, pick_template
            if not workspace.templates:
                print("Error: no .pptx template found in the working directory.", file=sys.stderr)
                return 1
            distill_dir = Path.cwd() / ".powergen_distill"
            distill_dir.mkdir(exist_ok=True)
            distill_client = make_llm_client(mock=args.mock, model="claude-haiku-4-5-20251001")
            print("[distill] Updating knowledge index...")
            run_distill(workspace, distill_client, distill_dir, enable_vision=not args.no_vision)
            template_info = pick_template(workspace.templates, args.brief)
            template_path = template_info.path
            print(f"Template: {template_path.name}")
            print("[1/3] Analysing template structure…")
            print("[2/3] Generating content mapping…")
            print("[3/3] Applying replacements…")
            output_path = Path(args.output) if args.output else None
            out = fill_template(
                brief=args.brief,
                template_path=template_path,
                output_path=output_path,
                client=client,
                workspace=workspace,
            )
            print(f"\nDone: {out}")

        elif args.cmd == "distill":
            from .distiller import run_distill
            distill_client = make_llm_client(mock=args.mock, model=args.model)
            distill_dir = Path.cwd() / ".powergen_distill"
            distill_dir.mkdir(exist_ok=True)
            run_distill(workspace, distill_client, distill_dir, force=getattr(args, "force", False), enable_vision=not args.no_vision)

        elif args.cmd == "fill":
            from .catalog_planner import run_catalog_plan
            from .catalog_filler import fill_from_plan
            if not workspace.templates:
                print("Error: no .pptx template found in the working directory.", file=sys.stderr)
                return 1
            from .template_filler import pick_template
            template_info = pick_template(workspace.templates, args.brief)
            template_path = template_info.path
            catalog_dir = Path.cwd() / ".powergen_catalog"
            catalog_path = catalog_dir / (template_path.stem + ".catalog.json")
            if not catalog_path.exists():
                print(
                    f"Error: catalog not found for '{template_path.name}'.\n"
                    "Run 'powergen catalog' first.",
                    file=sys.stderr,
                )
                return 1
            distill_dir = Path.cwd() / ".powergen_distill"
            print(f"Template: {template_path.name}")
            print("[1/2] Planning slide content…")
            plan = run_catalog_plan(
                brief=args.brief,
                catalog_path=catalog_path,
                client=client,
                distill_dir=distill_dir if distill_dir.exists() else None,
            )
            print(f"      {len(plan)} slide(s) planned.")
            if args.plan_only:
                import json as _json
                print(_json.dumps(plan, indent=2, ensure_ascii=False))
                return 0
            print("[2/2] Filling template…")
            output_path = Path(args.output) if args.output else None
            if output_path is None:
                output_path = template_path.parent / (template_path.stem + "-filled.pptx")
            out = fill_from_plan(
                plan=plan,
                template_path=template_path,
                catalog_path=catalog_path,
                output_path=output_path,
            )
            print(f"\nDone: {out}")

        elif args.cmd == "catalog":
            from .catalog import run_catalog
            catalog_client = make_llm_client(mock=args.mock, model=args.model)
            catalog_dir = Path.cwd() / ".powergen_catalog"
            run_catalog(workspace, catalog_client, catalog_dir, force=getattr(args, "force", False))

        elif args.cmd == "status":
            print(f"Stage: {state.stage.value}")
            if state.plan:
                print(f"Slides planned: {len(state.plan.slide_summaries)}")
            if state.spec:
                print(f"Slides in spec: {len(state.spec.slides)}")
                print(f"Title: {state.spec.title}")
            if state.output_path:
                print(f"Output: {state.output_path}")

        elif args.cmd == "reset":
            state.reset()
            print("Project reset to INIT.")

        else:
            # No subcommand → interactive REPL
            from .repl import run_repl
            run_repl(state, client, workspace)

    except StateError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 0

    return 0
