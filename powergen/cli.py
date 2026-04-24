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
    template_p.add_argument("--pptx", default=None, metavar="FILE", help="Path to the .pptx template")
    template_p.add_argument("--topic", default=None, metavar="TOPIC", help="Topic or content description")
    template_p.add_argument(
        "--output", "-o",
        default=None,
        metavar="FILE",
        help="Output .pptx path (default: <template>-filled.pptx)",
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
            from .layer2.composer import run as layer2_run, default_output_path
            if not args.pptx:
                print("Error: --pptx <file> is required.", file=sys.stderr)
                return 1
            if not args.topic:
                print("Error: --topic <description> is required.", file=sys.stderr)
                return 1
            template_path = Path(args.pptx)
            if not template_path.exists():
                print(f"Error: template not found: {template_path}", file=sys.stderr)
                return 1
            output_path = Path(args.output) if args.output else default_output_path(template_path)
            print(f"Template: {template_path.name}")
            out = layer2_run(
                template_path=template_path,
                topic=args.topic,
                output_path=output_path,
                client=client,
                mock=args.mock,
            )
            print(f"\nDone: {out}")

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
