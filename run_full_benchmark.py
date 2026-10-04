"""Run RESCO benchmark experiments on any registered map and plot the comparison.

Examples (run from the repo root, inside the conda env you want to use):

    python run_full_benchmark.py --map katubedda FMA2C:100
    python run_full_benchmark.py --map katubedda FIXED:10 MAXPRESSURE:10 IDQN:100
    python run_full_benchmark.py --map katubedda            # default matrix below
    python run_full_benchmark.py --map katubedda --plot-only

Each positional argument is ALGORITHM:EPISODES. The map must exist in
resco_benchmark/config/config.yaml and signal.yaml (see docs/env_pipeline_guide.md).
"""
import argparse
import json
import os
import subprocess
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

WORKSPACE = os.path.dirname(os.path.abspath(__file__))
BENCHMARK_DIR = os.path.join(WORKSPACE, "resco_benchmark")
RESULTS_DIR = os.path.join(WORKSPACE, "results")

DEFAULT_EXPERIMENTS = [
    # Static baselines
    "FIXED:10",
    "MAXPRESSURE:10",
    # Deep RL models
    "IDQN:100",
    "MPLight:100",
    "IPPO:100",
]


def run_experiments(map_name, experiments):
    # Always import resco_benchmark from this checkout, even if the conda env's
    # editable install points at another clone.
    env = dict(os.environ)
    env["PYTHONPATH"] = WORKSPACE + os.pathsep + env.get("PYTHONPATH", "")

    for exp in experiments:
        alg, eps = exp.split(":")
        print("\n==========================================")
        print(f" Running {alg} on {map_name} for {eps} episodes...")
        print("==========================================", flush=True)
        cmd = [
            sys.executable, "main.py",
            f"@{map_name}", f"@{alg}",
            f"episodes:{eps}",
            "gui:False", "libsumo:True",
        ]
        subprocess.run(cmd, cwd=BENCHMARK_DIR, env=env, check=True)


def plot_results(map_name):
    print("\nGenerating final comparative plot...")
    plt.figure(figsize=(12, 7))

    plotted = 0
    for f in sorted(os.listdir(RESULTS_DIR)):
        if not (f.startswith(map_name + "+") and f.endswith(".json")):
            continue
        with open(os.path.join(RESULTS_DIR, f)) as fp:
            d = json.load(fp)
        model_name = f.split("+")[1].split("_")[0].upper()
        delays = list(d["timeLoss"].values())[0]

        if len(delays) >= 50:
            # Smoothed learning curve
            window = 5
            smoothed = np.convolve(delays, np.ones(window) / window, mode="valid")
            plt.plot(range(window - 1, len(delays)), smoothed,
                     label=f"{model_name} (smoothed)", linewidth=2.5)
            plotted += 1
        elif len(delays) > 0:
            # Short runs (static baselines): horizontal average line
            avg = np.mean(delays)
            plt.axhline(y=avg, linestyle="--",
                        label=f"{model_name} (avg: {avg:.1f}s)", linewidth=2)
            plotted += 1

    if plotted == 0:
        print(f"No result JSONs found for map '{map_name}' in {RESULTS_DIR}")
        return

    plt.xlabel("Episode", fontsize=12)
    plt.ylabel("Average Delay / timeLoss (s)", fontsize=12)
    plt.title(f"{map_name} - Benchmark", fontsize=14)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)

    out_file = os.path.join(RESULTS_DIR, f"{map_name}_benchmark.png")
    plt.savefig(out_file, dpi=300, bbox_inches="tight")
    print(f"Benchmark plot successfully saved to: {out_file}")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--map", required=True, help="map name (folder under resco_benchmark/environments)")
    parser.add_argument("--plot-only", action="store_true", help="skip the runs, just plot existing results")
    parser.add_argument("experiments", nargs="*", metavar="ALG:EPISODES",
                        help="default: " + " ".join(DEFAULT_EXPERIMENTS))
    args = parser.parse_args()

    experiments = args.experiments or DEFAULT_EXPERIMENTS
    for exp in experiments:
        if exp.count(":") != 1 or not exp.split(":")[1].isdigit():
            parser.error(f"bad experiment '{exp}', expected ALGORITHM:EPISODES")

    if not args.plot_only:
        run_experiments(args.map, experiments)
    plot_results(args.map)


if __name__ == "__main__":
    main()
