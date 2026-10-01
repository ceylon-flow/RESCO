import subprocess
import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

WORKSPACE = "/home/nithira/ceylon_flow/RESCO"
BENCHMARK_DIR = os.path.join(WORKSPACE, "resco_benchmark")
RESULTS_DIR = os.path.join(WORKSPACE, "results")

# 1. Define Benchmark Matrix
experiments = [
    # Static Baselines (10 episodes each)
    ("cologne3", "FIXED", 10),
    ("cologne3", "MAXPRESSURE", 10),
    # Deep RL Models (100 episodes each)
    ("cologne3", "IDQN", 100),
    ("cologne3", "MPLight", 100),
    ("cologne3", "IPPO", 100),
]

# 2. Run All Experiments Headless (High Speed)
for map_name, alg, eps in experiments:
    print(f"\n==========================================")
    print(f" Running {alg} on {map_name} for {eps} episodes...")
    print(f"==========================================")
    cmd = [
        "python", "main.py",
        f"@{map_name}", f"@{alg}",
        f"episodes:{eps}",
        "gui:False", "libsumo:True"
    ]
    subprocess.run(cmd, cwd=BENCHMARK_DIR, check=True)

# 3. Generate Comparative Plot
print("\nGenerating final comparative plot...")
plt.figure(figsize=(12, 7))

for f in sorted(os.listdir(RESULTS_DIR)):
    if 'cologne3' in f and f.endswith('.json'):
        with open(os.path.join(RESULTS_DIR, f)) as fp:
            d = json.load(fp)
            model_name = f.split('+')[1].split('_')[0].upper()
            delays = list(d['timeLoss'].values())[0]
            
            if len(delays) >= 50:
                # Plot raw and smoothed curves
                window = 5
                smoothed = np.convolve(delays, np.ones(window)/window, mode='valid')
                plt.plot(range(window-1, len(delays)), smoothed, label=f"{model_name} (smoothed)", linewidth=2.5)
            elif len(delays) > 0:
                # For static baselines, plot the average horizontal baseline
                avg = np.mean(delays)
                plt.axhline(y=avg, linestyle='--', label=f"{model_name} (avg: {avg:.1f}s)", linewidth=2)

plt.xlabel('Episode', fontsize=12)
plt.ylabel('Average Delay / timeLoss (s)', fontsize=12)
plt.title('Cologne Corridor (cologne3) - 100 Episode Benchmark', fontsize=14)
plt.legend(fontsize=11)
plt.grid(True, alpha=0.3)

out_file = os.path.join(RESULTS_DIR, "cologne3_100episodes_benchmark.png")
plt.savefig(out_file, dpi=300, bbox_inches='tight')
print(f"Benchmark plot successfully saved to: {out_file}")
