# How to train on a new map

Follow these steps to run RESCO on a SUMO map you made. Replace `<map>` with your map's folder name
(for example `katubedda`). A filled-in example is at the bottom.

Always use the `resco` conda env:

```bash
conda activate resco
cd /home/nithira/ceylon_flow/RESCO
which python        # must end in .../envs/resco/bin/python
```

---

## Step 1: Add your map files

Put the net file and the route file in `resco_benchmark/environments/<map>/`.
The folder name is the map name you will type in every command.

## Step 2: Register the map

Open `resco_benchmark/config/config.yaml`. Paste this at the **end** of the file, keeping the 8 spaces of indentation:

```yaml
        <map>:
            network: <your net file>.net.xml
            route: <your route file>.rou.xml
            flow: 0
            start_time: 0
            end_time: 3600
```

- `end_time` is how many seconds your route file simulates (3600 = 1 hour).
- Keep `flow: 0`. Without it the run crashes looking for a file called `<map>.flo.xml`.

## Step 3: Describe the traffic lights

RESCO needs to know which lanes belong to each traffic light. Do this in `resco_benchmark/config/signal.yaml`.

**3a. Print the facts about your net** (change the file name at the end of the first line):

```bash
python - resco_benchmark/environments/<map>/<your net file>.net.xml <<'EOF'
import sys, sumolib
net = sumolib.net.readNet(sys.argv[1], withPrograms=True)
for tls in net.getTrafficLights():
    print("\n== TLS:", tls.getID())
    for fr, to, idx in sorted(tls.getConnections(), key=lambda c: c[2]):
        print(f"  link {idx:2d}: {fr.getID():8s} -> {to.getID():8s} ({fr.getEdge().getID()} -> {to.getEdge().getID()})")
    prog = list(tls.getPrograms().values())[0]
    greens = [p.state for p in prog.getPhases() if "y" not in p.state and set(p.state) - {"r", "s"}]
    for i, s in enumerate(greens):
        print(f"  green phase (action) {i}: {s}   open links: {[k for k, c in enumerate(s) if c in 'Gg']}")
EOF
```

It prints, for every traffic light: its id, which lane leads to which lane, and each green phase with the links it opens.

**3b. Add an entry** at the **end** of `signal.yaml`, **on a new line** (the file has no final newline, so
if you append directly it breaks the previous entry):

```yaml
'<map>': {
  'phase_pairs': [ ['S-S', 'N-N'], ['S-E', 'N-W'], ['W-W', 'E-E'], ['W-S', 'E-N'] ],
  'pair_to_act_map': {
    '<traffic light id 1>': { 0: 0, 1: 1, 2: 2, 3: 3 },
    '<traffic light id 2>': { 0: 0, 1: 1, 2: 2 },
  },
  '<traffic light id 1>': {
    'lane_sets': {
      'S-W': [ ], 'S-S': [ ], 'S-E': [ ],
      'W-N': [ ], 'W-W': [ ], 'W-S': [ ],
      'N-E': [ ], 'N-N': [ ], 'N-W': [ ],
      'E-S': [ ], 'E-E': [ ], 'E-N': [ ]
    },
    'downstream': { 'N': null, 'E': null, 'S': null, 'W': null },
    fixed_timings: [ 7, 1, 7, 1 ],
    fixed_phase_order_idx: 0
  },
  '<traffic light id 2>': {
    ... same layout as above ...
  },
  'management': { 'top_mgr': [ '<traffic light id 1>', '<traffic light id 2>' ] },
  'management_neighbors': { 'top_mgr': [ ] }
}
```

Fill in the blanks using the output from 3a:

| What | How to fill it in |
|---|---|
| `<traffic light id>` | Copy the `== TLS:` names exactly. Add one block per traffic light. |
| `lane_sets` | Give each road coming into the junction a compass letter (N, E, S or W) = the direction its cars are travelling. Use a different letter for each road. Then list its lanes (`<edge>_<lane number>`) by what they do: `S-W` = right turn, `S-S` = straight, `S-E` = left turn (for a road labelled S). The other letters work the same way: `W-N` right, `W-W` straight, `W-S` left; `N-E`, `N-N`, `N-W`; `E-S`, `E-E`, `E-N`. Use `[ ]` when a movement doesn't exist. A lane that does two things goes in both lists. Keep all 12 lines, in this order. |
| `downstream` | If this junction's exit road leads straight into another traffic light, write that light's id next to the direction cars leave in. Otherwise `null`. |
| `phase_pairs` | A list of movement pairs that a green phase serves, e.g. `['S-S', 'N-N']` = north-south straight. Add one pair for each different green phase you saw in 3a. |
| `pair_to_act_map` | For each traffic light: `{ pair number : green phase number }`. The pair number is the position in `phase_pairs` (the first is 0). The green phase number is the `green phase (action)` number printed in 3a. |
| `fixed_timings` | One number per green phase: how long it stays green, in 5-second steps (33 s green → 7). |
| `management` | List every traffic light id once. |

Check: for each light, `pair_to_act_map` needs one entry per green phase from 3a, and `fixed_timings` needs one
number per green phase.

## Step 4: Quick test (about 1 minute)

```bash
cd resco_benchmark
python main.py @<map> @FIXED episodes:2 gui:False libsumo:True
cd ..
```

The terminal stays almost silent. That is normal. Check it worked:

```bash
grep "lights\|Episode:" results/<map>+fixed*/git_FINAL/*/console.log
```

You should see a `lights N (...)` line with your traffic light ids, then two `Episode:` lines. If not, open that
`console.log` and read the last lines (see "If something goes wrong").

Then delete the test results so they don't appear in your real plot:

```bash
rm -rf results/<map>*
```

## Step 5: Start training in the background

```bash
nohup python run_full_benchmark.py --map <map> IDQN:100 > results/<map>_run.log 2>&1 &
```

- `IDQN:100` means algorithm `IDQN`, 100 episodes. You can list several, they run one after another:
  `FIXED:10 MAXPRESSURE:10 IDQN:100 MPLight:100 IPPO:100`.
- Algorithms: `FIXED`, `MAXPRESSURE`, `MAXWAVE` (no learning, use about 10 episodes) and `IDQN`, `MPLight`, `IPPO`
  (learning, use about 100 episodes).
- It keeps running if you close the terminal. Each episode takes roughly 15–40 seconds.
- The learning algorithms use the GPU automatically. The three no-learning ones don't.

Watch it:

```bash
tail -f results/<map>_run.log                       # shows which algorithm is running (Ctrl+C leaves it running)
nvtop                                                # GPU usage (press q to quit)
grep "Episode:" results/<map>+*/git_FINAL/*/console.log | tail -n 3     # latest episode numbers
```

Is it still running?

```bash
pgrep -af run_full_benchmark
```

Stop it:

```bash
pkill -f run_full_benchmark.py
pkill -f "main.py @<map>"
```

### Results

When it finishes the last lines of `results/<map>_run.log` say `Benchmark plot successfully saved`. Everything is in `results/`:

| File | What it is |
|---|---|
| `results/<map>_benchmark.png` | The comparison plot (average delay per episode, lower is better) |
| `results/<map>+<algorithm>_....json` | The numbers for each run |
| `results/<map>_run.log` | The log of the run |

Re-draw the plot from existing results without running anything:

```bash
python run_full_benchmark.py --map <map> --plot-only
```

---

## Changed the map and want to run again?

1. Changed the net (roads, lanes or signals): run step 3a again and update the entry in `signal.yaml`.
2. Changed how long the route file runs: update `end_time` in `config.yaml`.
3. Move the old results away so they don't show up in the new plot:
   ```bash
   mkdir -p ~/resco_old_results && mv results/<map>* ~/resco_old_results/
   ```
4. Repeat steps 4 and 5.

## If something goes wrong

Runs write their errors to a file, not to the terminal. Open the newest
`results/<map>+<algorithm>*/git_FINAL/*/console.log` and read the last lines. (Lines about `Gym has been unmaintained` are harmless.)

| What you see | What to do |
|---|---|
| `FileNotFoundError ... .flo.xml` | Add `flow: 0` to your map in `config.yaml` (step 2). |
| `Route file not found` / `Net file not found` | The file names in `config.yaml` don't match the files in your map folder. |
| `ModuleNotFoundError` (libsumo, pfrl, ...) | Wrong conda env. Run `conda activate resco` and check `which python`. |
| Error when reading `signal.yaml` | The new entry was added on the same line as the previous one. Put it on its own line. |
| Error about an unknown lane | A lane name in `lane_sets` isn't in the net. Compare with the output of step 3a. |
| Error naming a traffic light id | The id in `signal.yaml` isn't exactly the one printed in step 3a. |
| Plot has old or duplicate lines | Old results are still in `results/`. Move them away (see above). |

---

## Example: Katubedda

Folder `resco_benchmark/environments/katubedda/`, files `Simulation.net.xml` and `Simulation.rou.xml`.
Already added to the repo, shown here as a finished example of steps 2 and 3.

`config.yaml`:

```yaml
        katubedda:
            network: Simulation.net.xml
            route: Simulation.rou.xml
            flow: 0
            start_time: 0
            end_time: 3600
```

`signal.yaml`:

```yaml
'katubedda': {
  'phase_pairs': [ ['S-S', 'N-N'], ['S-E', 'N-W'], ['W-W', 'E-E'], ['W-S', 'E-N'], ['N-N', 'N-E'], ['W-N', 'W-S'] ],
  'pair_to_act_map': {
    'clusterJ0_J1_J10_J11_#4more': { 0: 0, 1: 1, 2: 2, 3: 3 },
    'clusterJ10_J11_J12_J13_#2more': { 0: 0, 4: 1, 5: 2 },
  },
  'clusterJ0_J1_J10_J11_#4more': {
    'lane_sets': {
      'S-W': [ 'E8_0' ],
      'S-S': [ 'E8_0', 'E8_1', 'E8_2' ],
      'S-E': [ 'E8_3' ],
      'W-N': [ 'E13_0' ],
      'W-W': [ 'E13_0' ],
      'W-S': [ 'E13_0' ],
      'N-E': [ 'E9_0' ],
      'N-N': [ 'E9_0', 'E9_1', 'E9_2' ],
      'N-W': [ 'E9_3' ],
      'E-S': [ 'E10_0' ],
      'E-E': [ 'E10_0' ],
      'E-N': [ 'E10_1' ]
    },
    'downstream': { 'N': null, 'E': null, 'S': 'clusterJ10_J11_J12_J13_#2more', 'W': null },
    fixed_timings: [ 7, 1, 7, 1 ],
    fixed_phase_order_idx: 0
  },
  'clusterJ10_J11_J12_J13_#2more': {
    'lane_sets': {
      'S-W': [ ],
      'S-S': [ 'E14_0', 'E14_1', 'E14_2' ],
      'S-E': [ 'E14_2' ],
      'W-N': [ 'E4_0' ],
      'W-W': [ ],
      'W-S': [ 'E4_1' ],
      'N-E': [ 'E1_0' ],
      'N-N': [ 'E1_0', 'E1_1', 'E1_2', 'E1_3' ],
      'N-W': [ ],
      'E-S': [ ],
      'E-E': [ ],
      'E-N': [ ]
    },
    'downstream': { 'N': null, 'E': null, 'S': null, 'W': null },
    fixed_timings: [ 7, 1, 7 ],
    fixed_phase_order_idx: 0
  },
  'management': {
    'top_mgr': [ 'clusterJ0_J1_J10_J11_#4more', 'clusterJ10_J11_J12_J13_#2more' ]
  },
  'management_neighbors': {
    'top_mgr': [ ]
  }
}
```

The compass letters are only labels, because the Katubedda net is rotated. Here the road `E14` between the two
lights is labelled `S` at both ends, which is why the first light has `'S': 'clusterJ10_J11_J12_J13_#2more'` under
`downstream`.

Tip: in short tests every algorithm got about the same delay (~1,500 s). The route file sends 5000 cars/hour on
each of its two flows, which is more than the roads can take. Lower `vehsPerHour` in `Simulation.rou.xml`
(for example to 1000–1500) if you want the comparison to mean something.
