from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Sequence

from faers_agent.agent import ClaudeFAERSAgent


def load_env_file(path: str = ".env") -> dict[str, str]:
    env: dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return env

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key:
            env[key] = value
    return env


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FAERS inverse-signal detector")
    parser.add_argument("--disease", required=False, help="Disease label, e.g. alzheimer")
    parser.add_argument(
        "--drugs",
        nargs="+",
        required=False,
        help="Candidate generic drug names, e.g. metformin atorvastatin",
    )
    parser.add_argument(
        "--events",
        nargs="*",
        default=None,
        help="Optional explicit MedDRA PT list. Overrides disease mapping.",
    )
    parser.add_argument("--api-key", default=None, help="OpenFDA API key (optional)")
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument(
        "--correction",
        choices=["none", "bonferroni", "fdr"],
        default="none",
    )
    parser.add_argument("--max-concurrent", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--json", action="store_true", help="Print full JSON output")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--suggest-events-for",
        default=None,
        help="Fetch top MedDRA PT events from OpenFDA for a drug.",
    )
    parser.add_argument(
        "--suggest-limit",
        type=int,
        default=10,
        help="Number of suggested event terms to fetch (max 1000).",
    )
    parser.add_argument(
        "--use-suggested-events",
        action="store_true",
        help="Use suggested OpenFDA event terms as --events for FAERS computation.",
    )
    return parser.parse_args()


def summarize(result: dict, drugs: Sequence[str]) -> str:
    lines = []
    lines.append(f"Disease: {result['disease']}")
    lines.append(f"Events: {', '.join(result['events'])}")
    lines.append(f"Total FAERS reports: {result['total_faers']}")
    lines.append(
        f"Tests: {result['tests_run']} (correction={result['correction_method']}, "
        f"alpha={result['alpha']}, corrected_alpha={result['corrected_alpha']})"
    )

    by_drug = {item["drug"]: item for item in result["strongest_by_drug"]}
    lines.append("\nBest signal per drug:")
    for drug in drugs:
        item = by_drug.get(drug)
        if not item:
            lines.append(f"- {drug}: no result")
            continue
        if item["insufficient_data"]:
            lines.append(
                f"- {drug} x {item['event']}: insufficient data "
                f"(a={item['a']}, b={item['b']}, c={item['c']}, d={item['d']})"
            )
            continue
        lines.append(
            "- {drug} x {event}: ror={ror:.4f}, ci=[{lo:.4f},{hi:.4f}], inverse={inv}, "
            "score={score:.2f}, n={n}, a={a}, b={b}, c={c}, d={d}".format(
                drug=drug,
                event=item["event"],
                ror=item["ror"],
                lo=item["ci_lower"],
                hi=item["ci_upper"],
                inv=item["is_inverse_signal"],
                score=item["normalized_score"],
                n=item["report_count"],
                a=item["a"],
                b=item["b"],
                c=item["c"],
                d=item["d"],
            )
        )

    inverse = result["inverse_signals"]
    lines.append(f"\nSignificant inverse pairs: {len(inverse)}")
    for sig in inverse[:10]:
        lines.append(
            f"- {sig['drug']} x {sig['event']}: ROR={sig['ror']:.4f}, "
            f"CI=[{sig['ci_lower']:.4f},{sig['ci_upper']:.4f}], n={sig['report_count']}"
        )

    insufficient = [x for x in result["by_pair"] if x.get("insufficient_data")]
    if insufficient:
        lines.append(f"\nInsufficient pairs: {len(insufficient)}")
        for sig in insufficient[:20]:
            lines.append(
                f"- {sig['drug']} x {sig['event']}: "
                f"a={sig['a']}, b={sig['b']}, c={sig['c']}, d={sig['d']}"
            )
    return "\n".join(lines)


async def async_main() -> int:
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    env_file_values = load_env_file()
    api_key = args.api_key or os.getenv("OPENFDA_API_KEY") or env_file_values.get(
        "OPENFDA_API_KEY"
    )

    agent = ClaudeFAERSAgent(
        api_key=api_key,
        timeout=args.timeout,
        max_concurrent=args.max_concurrent,
        delay_between_calls=args.delay,
    )

    suggested_terms: list[tuple[str, int]] = []
    drug_for_suggestions = args.suggest_events_for
    if args.use_suggested_events and not drug_for_suggestions and args.drugs:
        drug_for_suggestions = args.drugs[0]

    if drug_for_suggestions:
        suggested_terms = await agent.detector.client.top_event_terms(
            drug=drug_for_suggestions,
            limit=args.suggest_limit,
        )
        if not suggested_terms:
            print("No event terms returned from OpenFDA.")
            return 1
        print(f"Top MedDRA PT terms for {drug_for_suggestions}:")
        for term, count in suggested_terms:
            print(f"- {term}: {count}")

        # Suggest-only mode: print terms and exit.
        if not args.use_suggested_events and (not args.disease or not args.drugs):
            return 0

    if not args.disease or not args.drugs:
        raise SystemExit(
            "error: --disease and --drugs are required unless --suggest-events-for is used"
        )

    events = args.events
    if args.use_suggested_events:
        if not suggested_terms:
            if not drug_for_suggestions:
                raise SystemExit(
                    "error: --use-suggested-events requires --drugs or --suggest-events-for"
                )
            suggested_terms = await agent.detector.client.top_event_terms(
                drug=drug_for_suggestions,
                limit=args.suggest_limit,
            )
            if not suggested_terms:
                raise SystemExit("error: unable to fetch suggested events from OpenFDA")
        events = [term for term, _ in suggested_terms]
        print(
            f"\nUsing {len(events)} suggested events for scoring "
            f"(source drug: {drug_for_suggestions})."
        )

    payload = {
        "disease": args.disease,
        "candidate_drugs": args.drugs,
        "disease_events": events,
        "alpha": args.alpha,
        "correction": args.correction,
    }

    result = await agent.arun(payload)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(summarize(result, args.drugs))
    return 0


def main() -> int:
    return asyncio.run(async_main())


if __name__ == "__main__":
    raise SystemExit(main())
