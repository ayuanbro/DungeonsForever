"""Measure the native route facade or compatibility IdleJobs callback offline.

This measures a bounded sample, not a hard scheduling guarantee or in-game UI
acceptance. The publication hooks are no-ops. All run limits and the report
destination are explicit CLI inputs so other machines can reproduce a scenario.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "validation"))
from test_prof_native_data import native_runtime
from benchmark_delivery import full_native_vm


def measure(slug, learned, *, target, cpu_limit_ms, max_callbacks, timeout,
            profile_nonyield=False, runner_mode='facade'):
    # Normal TOC loading places ProfRoutePlans after ProfSolverRun, replacing its
    # Start/State API with the RA.Get/Recalculate lifecycle and its own schedule.
    # Keep compat explicit so earlier reduced-fixture reports remain reproducible.
    lua = full_native_vm() if runner_mode == 'facade' else native_runtime()
    lua.execute("ns.IsForever=true")
    data = ROOT / "Core/Data/Data_ProfLearningSources.lua"
    runner = ROOT / "Core/ProfSolverRun.lua"
    if runner_mode == 'compat':
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)", data.read_text(encoding="utf-8"))
    lua.globals().probeClock = lambda: time.perf_counter() * 1000
    lua.globals().probeSlug = slug
    lua.globals().probeKnown = learned
    lua.globals().probeTarget = target
    lua.globals().probeCpuLimitMs = cpu_limit_ms
    lua.globals().probeThreadClock = lambda: time.thread_time() * 1000
    lua.execute("""
      selected=probeSlug
      IsPlayerSpell=function()return probeKnown end
      debugprofilestop=probeClock
      ns.IdleJobs={Add=function(fn)probeCallback=fn end}
      ns.ProfRouteAuto.AHPriceOf=function()return 1 end
      ns.ProfModule.ProfLearned=function()return {[selected]={cur=1,max=75}}end
    """)
    if runner_mode == 'compat':
        lua.execute("assert(loadstring(...))('DungeonsForever',ns)", runner.read_text(encoding="utf-8"))
    if profile_nonyield:
        lua.execute("""
          local function packed(...)return {n=select('#',...),...}end
          local function wrap(parent,key,label,copyOnly)
            if not(parent and type(parent[key])=='function')then return end
            local original=parent[key]
            parent[key]=function(...)
              if copyOnly and select(2,...)~=nil then return original(...)end
              local start=probeClock()
              local values=packed(original(...))
              local span=probeClock()-start
              probeSpans[#probeSpans+1]={name=label,wallMs=span}
              return unpack(values,1,values.n)
            end
          end
          probeSpans={}
          local E=ns.ProfEconomy
          wrap(E,'Copy','E.Copy(no tick)',true)
          wrap(E,'Normalize','E.Normalize')
          wrap(E,'ResolveRecipe','E.ResolveRecipe')
          wrap(E,'SelectLearningRoute','E.SelectLearningRoute')
          wrap(E,'FormulaFor','E.FormulaFor')
          wrap(ns.ProfLearningSources,'Get','LearningSources.Get')
          wrap(ns.VendorPriceDB,'GetOffers','VendorPriceDB.GetOffers')
          wrap(ns.VendorPriceDB,'GetFormulaOffers','VendorPriceDB.GetFormulaOffers')
          wrap(ns.ProfRouteSolver,'RefreshStatus','Solver.RefreshStatus')
        """)
    lua.execute("""
      probeHandle=ns.ProfSolverRun.Start(probeSlug,{start=1,target=probeTarget,
        autoCraftTools=false,recoveryEnabled=false,cpuLimitMs=probeCpuLimitMs},
        {onProgress=function()end,onDone=function()end})
    """)
    callback = lua.globals().probeCallback
    durations = []
    records = []
    done = False
    started = time.perf_counter()
    while not done and len(durations) < max_callbacks and time.perf_counter() - started < timeout:
        phase_before = lua.globals().ns.ProfSolverRun.State(lua.globals().probeHandle.job)["phase"]
        memory_before = lua.eval("collectgarbage('count')")
        if profile_nonyield:
            lua.execute("probeSpans={}")
        process_before = time.process_time()
        thread_before = time.thread_time()
        before = time.perf_counter()
        done = bool(callback())
        elapsed = (time.perf_counter() - before) * 1000
        thread_elapsed = (time.thread_time() - thread_before) * 1000
        process_elapsed = (time.process_time() - process_before) * 1000
        durations.append(elapsed)
        record = {"callback": len(durations), "phaseBefore": phase_before,
                  "phaseAfter": lua.globals().ns.ProfSolverRun.State(lua.globals().probeHandle.job)["phase"],
                  "wallMs": elapsed, "threadCpuMs": thread_elapsed,
                  "processCpuMs": process_elapsed,
                  "nonCpuWallMs": max(0, elapsed - thread_elapsed) if sys.platform != "win32" else None,
                  "memoryBeforeKiB": memory_before,
                  "memoryAfterKiB": lua.eval("collectgarbage('count')")}
        if profile_nonyield:
            spans = [{"name": row["name"], "wallMs": row["wallMs"]}
                     for row in lua.globals().probeSpans.values()]
            record["largestNonYieldSpans"] = sorted(spans, key=lambda row: row["wallMs"], reverse=True)[:5]
        records.append(record)
    ordered = sorted(durations)
    if not ordered:
        raise RuntimeError("runner did not execute an IdleJobs callback")
    return {
        "profession": slug,
        "runner": runner_mode,
        "learned": learned,
        "target": target,
        "cpuLimitMs": cpu_limit_ms,
        "callbacks": len(ordered),
        "done": done,
        "status": lua.globals().probeHandle.job.status,
        "p95Ms": ordered[max(0, int(len(ordered) * .95) - 1)],
        "maxMs": max(ordered),
        "over2ms": sum(value > 2 for value in ordered),
        "totalMs": sum(ordered),
        "allMeasuredCallbacksWithin2ms": all(value <= 2 for value in ordered),
        "maxThreadCpuMs": max(row["threadCpuMs"] for row in records),
        "cpuOver2ms": sum(row["threadCpuMs"] > 2 for row in records) if sys.platform != "win32" else None,
        "cpuUsableForSliceAttribution": sys.platform != "win32",
        "phaseSummary": {phase: {
            "callbacks": sum(row["phaseBefore"] == phase for row in records),
            "maxWallMs": max(row["wallMs"] for row in records if row["phaseBefore"] == phase),
            "maxThreadCpuMs": max(row["threadCpuMs"] for row in records if row["phaseBefore"] == phase),
        } for phase in sorted({row["phaseBefore"] for row in records})},
        "slowestCallbacks": sorted(records, key=lambda row: row["wallMs"], reverse=True)[:10],
        "profileNonYield": profile_nonyield,
        "hooks": ("No-op caller progress/done hooks; actual ProfRoutePlans schedule/pump publication, "
                  "saving and execution refresh; UI initialization listeners not dispatched"
                  if runner_mode == 'facade' else
                  "No-op progress/done hooks; reduced-domain ProfSolverRun compatibility callback"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", action="append", required=True, metavar="PROFESSION:learned|unlearned")
    parser.add_argument("--target", type=int, required=True)
    parser.add_argument("--cpu-limit-ms", type=float, required=True)
    parser.add_argument("--max-callbacks", type=int, required=True)
    parser.add_argument("--timeout", type=float, required=True, help="Wall-clock safety limit per job in seconds")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runner", choices=('facade', 'compat'), default='facade',
                        help='facade follows the full TOC and ProfRoutePlans replacement API (default)')
    parser.add_argument("--profile-nonyield", action="store_true",
                        help="Diagnostic wrappers add CPU/allocations; use to locate functions, not judge the release budget")
    args = parser.parse_args()
    if args.target <= 1 or args.cpu_limit_ms <= 0 or args.max_callbacks <= 0 or args.timeout <= 0:
        parser.error("target must exceed 1 and all limits must be positive")
    observations = []
    for value in args.case:
        slug, separator, mode = value.partition(":")
        if not separator or mode not in ("learned", "unlearned"):
            parser.error("each case must be PROFESSION:learned or PROFESSION:unlearned")
        result = measure(slug, mode == "learned", target=args.target,
                         cpu_limit_ms=args.cpu_limit_ms, max_callbacks=args.max_callbacks,
                         timeout=args.timeout, profile_nonyield=args.profile_nonyield, runner_mode=args.runner)
        observations.append(result)
        print(json.dumps({key: value for key, value in result.items() if key != "slowestCallbacks"}), flush=True)
    report = {
        "environment": "Offline Lua5.1/mock client; Python perf_counter monotonic clock",
        "runner": args.runner,
        "entryPoint": ("TOC-overridden ProfSolverRun.Start -> RA.Recalculate/Get -> ProfRoutePlans.schedule/pump"
                       if args.runner == 'facade' else "ProfSolverRun.Start compatibility runner without ProfRoutePlans"),
        "scope": "Actual callback durations for explicitly bounded sample jobs; not real game acceptance",
        "runnerSHA256": hashlib.sha256((ROOT / "Core/ProfSolverRun.lua").read_bytes()).hexdigest(),
        "facadeSHA256": hashlib.sha256((ROOT / "Core/ProfRoutePlans.lua").read_bytes()).hexdigest(),
        "dataSHA256": hashlib.sha256((ROOT / "Core/Data/Data_ProfLearningSources.lua").read_bytes()).hexdigest(),
        "limits": {"maxCallbacks": args.max_callbacks, "timeoutSeconds": args.timeout},
        "cpuTimerCaution": ("Windows thread/process clocks were observed stepping in 15.625ms ticks; "
                            "raw CPU columns cannot attribute a 2ms wall-clock outlier."
                            if sys.platform == "win32" else None),
        "observations": observations,
        "limitations": [
            "Lupa/Python timing overhead is included; caller progress/done hooks are no-ops.",
            "Facade loads the complete profession TOC, but queued Init and real UI widget/listener work are excluded.",
            "OS scheduling, GC and nonyielding APIs can exceed cooperative slice budgets.",
            "One resume and a smaller slice reduce headroom pressure but do not prove a hard bound.",
            "Real-client UI, long-search and GC-stress profiling remain required.",
            "Optional nonyield function spans are inclusive wall times with extra instrumentation overhead.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if all(row["done"] for row in observations) else 1


if __name__ == "__main__":
    raise SystemExit(main())
