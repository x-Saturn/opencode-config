#!/usr/bin/env python3
"""Derivation verification helper for the `derivation` skill.

Modes
-----
numeric   Compare lhs and rhs at sample points (standard library only).
          Add --symbolic to also try a symbolic difference when sympy is installed.
solve     Substitute proposed roots back into an expression and report residuals.

Examples
--------
python verify.py numeric --check "2|sin(x)**2+cos(x)**2|1" --at "x=0.37,1.91,-1.23"
python verify.py numeric --symbolic --check "3|(1-x**2)/(1+x**2)**2|((1+x**2)-2*x**2)/(1+x**2)**2"
python verify.py numeric --check "4|exp(a+b)|exp(a)*exp(b)" --at "a=0.4,1.1;b=0.7,2.3"
python verify.py solve --step 5 --expr "x**2-4" --roots "2,-2"

Exit codes: 0 all checks passed, 1 at least one failed, 2 usage or parse error.

Output is ASCII so it survives any Windows console code page.
"""

from __future__ import annotations

import argparse
import math
import re
import sys

MATH_NAMES = {name: getattr(math, name) for name in dir(math) if not name.startswith("_")}
MATH_NAMES.update({"abs": abs, "min": min, "max": max, "pow": pow})

DEFAULT_SAMPLES = [0.37, 1.91, -1.23, 2.57, -0.68, 3.11, -2.41, 0.83]


def parse_at(text: str) -> dict[str, list[float]]:
    """Parse 'x=0.3,1.7;y=2.0' into {'x': [0.3, 1.7], 'y': [2.0]}."""
    out: dict[str, list[float]] = {}
    if not text:
        return out
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        name, sep, values = part.partition("=")
        name = name.strip()
        if not sep or not name or not values.strip():
            raise ValueError(f"bad --at segment {part!r}; expected x=0.3,1.7")
        out[name] = [float(v) for v in values.split(",") if v.strip()]
    return out


def variables(expr: str) -> list[str]:
    names = set(re.findall(r"\b[A-Za-z_]\w*\b", expr))
    return sorted(n for n in names if n not in MATH_NAMES)


def evaluate(expr: str, env: dict[str, float]):
    return eval(expr, {"__builtins__": {}}, {**MATH_NAMES, **env})  # noqa: S307


def format_env(env: dict[str, float]) -> str:
    return ", ".join(f"{k}={v:g}" for k, v in env.items()) or "no variables"


def compare(lhs: str, rhs: str, env: dict[str, float], tol: float) -> tuple[bool, float]:
    a = evaluate(lhs, env)
    b = evaluate(rhs, env)
    if a is None or b is None:
        raise ValueError("expression evaluated to None")
    if isinstance(a, complex) or isinstance(b, complex):
        ca, cb = complex(a), complex(b)
        diff, scale = abs(ca - cb), max(1.0, abs(ca), abs(cb))
    else:
        fa, fb = float(a), float(b)
        if math.isnan(fa) or math.isnan(fb):
            raise ValueError("expression evaluated to NaN")
        diff, scale = abs(fa - fb), max(1.0, abs(fa), abs(fb))
    rel = diff / scale
    return rel <= tol, rel


def run_numeric(check: dict, at: dict[str, list[float]], tol: float, max_points: int) -> dict:
    lhs, rhs = check["lhs"], check["rhs"]
    names = variables(lhs)
    names += [n for n in variables(rhs) if n not in names]
    count = max([len(at.get(n, [])) for n in names] + [0]) or max_points

    passed, failed, skipped = 0, [], 0
    max_rel = 0.0
    for index in range(count):
        env = {}
        for name in names:
            pool = at.get(name) or DEFAULT_SAMPLES
            env[name] = pool[index % len(pool)]
        try:
            ok, rel = compare(lhs, rhs, env, tol)
        except Exception:  # domain error, division by zero, unknown name, ...
            skipped += 1
            continue
        max_rel = max(max_rel, rel)
        if ok:
            passed += 1
        else:
            failed.append((env, rel))

    total = passed + len(failed)
    if total < 2:
        return {
            "level": "T0",
            "step": check["step"],
            "status": "skip",
            "message": f"not enough usable points ({total}, skipped {skipped})",
        }
    if failed:
        env, rel = failed[0]
        return {
            "level": "T0",
            "step": check["step"],
            "status": "fail",
            "message": f"{passed}/{total} points passed; {format_env(env)} rel={rel:.2e}",
        }
    return {
        "level": "T0",
        "step": check["step"],
        "status": "pass",
        "message": f"{total}/{total} points passed; max rel {max_rel:.1e}",
    }


def run_symbolic(check: dict) -> dict:
    try:
        import sympy  # type: ignore
    except ImportError:
        return {
            "level": "T1",
            "step": check["step"],
            "status": "skip",
            "message": "sympy not installed, symbolic check skipped",
        }

    step = check["step"]
    try:
        diff = sympy.sympify(check["lhs"]) - sympy.sympify(check["rhs"])
    except Exception as exc:
        return {"level": "T1", "step": step, "status": "skip", "message": f"parse error: {exc}"}

    value = diff
    for name, func in (
        ("simplify", sympy.simplify),
        ("trigsimp", sympy.trigsimp),
        ("cancel", sympy.cancel),
        ("expand", sympy.expand),
    ):
        try:
            value = func(diff)
        except Exception:
            continue
        if value == 0:
            return {"level": "T1", "step": step, "status": "pass", "message": f"difference is 0 ({name})"}
    return {"level": "T1", "step": step, "status": "fail", "message": f"difference = {str(value)[:140]}"}


def run_solve(step: str, expr: str, roots: list[float], symbol: str | None, tol: float) -> list[dict]:
    names = variables(expr)
    sym = symbol or (names[0] if names else "x")
    results = []
    for root in roots:
        try:
            residual = float(evaluate(expr, {sym: root}))
        except Exception as exc:
            results.append(
                {"level": "SOLVE", "step": step, "status": "skip", "message": f"{sym}={root:g} eval failed: {exc}"}
            )
            continue
        ok = abs(residual) <= tol
        results.append(
            {
                "level": "SOLVE",
                "step": step,
                "status": "pass" if ok else "fail",
                "message": f"{sym}={root:g} residual {residual:.2e}",
            }
        )
    return results


def parse_check(text: str) -> dict:
    parts = text.split("|")
    if len(parts) == 2:
        step, lhs, rhs = "?", parts[0], parts[1]
    elif len(parts) == 3:
        step, lhs, rhs = parts
    else:
        raise ValueError(f'bad --check {text!r}; expected "step|lhs|rhs"')
    if not lhs.strip() or not rhs.strip():
        raise ValueError(f"empty expression in --check {text!r}")
    return {"step": step.strip(), "lhs": lhs.strip(), "rhs": rhs.strip()}


def emit(result: dict) -> None:
    mark = {"pass": "[OK]", "fail": "[FAIL]", "skip": "[SKIP]"}[result["status"]]
    print(f'{mark} {result["level"]} ({result["step"]}) {result["message"]}')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Derivation checks: numeric sampling, symbolic difference, root residual")
    sub = parser.add_subparsers(dest="mode", required=True)

    p_num = sub.add_parser("numeric", help="sample lhs and rhs at several points")
    p_num.add_argument("--check", action="append", required=True, help='step|lhs|rhs (repeatable)')
    p_num.add_argument("--at", default="", help='sample values, e.g. "x=0.3,1.7;y=2.0"')
    p_num.add_argument("--tol", type=float, default=1e-9, help="relative tolerance, default 1e-9")
    p_num.add_argument("--symbolic", action="store_true", help="also compare symbolically (needs sympy)")
    p_num.add_argument("--max-points", type=int, default=3, help="samples when --at is omitted, default 3")

    p_solve = sub.add_parser("solve", help="substitute proposed roots and report residuals")
    p_solve.add_argument("--step", default="?")
    p_solve.add_argument("--expr", required=True, help="expression that should equal 0")
    p_solve.add_argument("--roots", required=True, help="comma separated roots, e.g. 2,-2")
    p_solve.add_argument("--symbol", default=None, help="variable name, defaults to the first one found")
    p_solve.add_argument("--tol", type=float, default=1e-9, help="absolute residual tolerance, default 1e-9")

    args = parser.parse_args(argv)
    results: list[dict] = []

    try:
        if args.mode == "numeric":
            checks = [parse_check(text) for text in args.check]
            at = parse_at(args.at)
            for check in checks:
                results.append(run_numeric(check, at, args.tol, args.max_points))
                if args.symbolic:
                    results.append(run_symbolic(check))
        else:
            roots = [float(v) for v in args.roots.replace(" ", "").split(",") if v]
            results = run_solve(args.step, args.expr, roots, args.symbol, args.tol)
    except ValueError as exc:
        print(f"[FAIL] bad argument: {exc}")
        return 2

    for result in results:
        emit(result)

    failed = sum(1 for r in results if r["status"] == "fail")
    passed = sum(1 for r in results if r["status"] == "pass")
    skipped = sum(1 for r in results if r["status"] == "skip")
    print(f"summary: {passed} passed / {failed} failed / {skipped} skipped")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
