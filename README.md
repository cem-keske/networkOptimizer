# FluxControl Solver

A little helper for the online game **[fluxcontrol.eu](https://fluxcontrol.eu)**.

In the game you're running a small electricity grid. Some power lines are
**overloaded** (carrying more than they can handle), and your job is to fix that
as **cheaply as possible** by turning each power station up or down, and connecting or disconnecting some power lines.

This tool does the hard maths for you, and tells you the cheapest possible way to remove the congestion.
You copy a level out of the game, run one command, and it tells you exactly how much to change each station, or which lines
to connect or disconnect.

---

## Requirements

1. **Python** — you can get it from [python.org](https://www.python.org/downloads/)
   
2. **Gurobi** — required to solve the optimization problem. Get the free licence at
   [gurobi.com](https://www.gurobi.com/) (it's free for students and academics),
   
3. **Download this tool** — click the green **Code** button on the GitHub page →

That's the setup. Now the fun part.

---

## How to use it 

### Step 1 — Add the "Export" button to your browser (one time)

Open a terminal, go into the tool's folder, and run:

```
python solve_level.py --bookmarklet
```

It prints a long line starting with `javascript:...`. Copy the one under
**"DOWNLOAD bookmarklet"**.

Now add it as a bookmark in your browser:

- Right-click your bookmarks bar → **Add page** (or **New bookmark**).
- **Name:** anything, e.g. `Export FluxControl`.
- **URL / Address:** paste the `javascript:...` line you copied.
- Save.

You now have an **Export FluxControl** button in your browser. 

### Step 2 — Grab the level from the game

1. Open **fluxcontrol.eu** and start the level you want to solve.
2. Click your **Export FluxControl** bookmark.

Your browser downloads a small file called something like `levelX.json`. That file is just the puzzle, saved.

### Step 3 — Solve it

Back in the terminal, run this (adjust the file name/location to match what got
downloaded):

```
python solve_level.py "C:\Users\YourName\Downloads\levelX.json"
```
*You can add a few options here too:

### Step 4 — Read the answer

The tool prints something like this:

```
======================================================
  Optimal redispatch   (total cost = 137.25 EUR)
======================================================

Node adjustments:
  N0  -- no change   (+31.0 MW)
  N1  DN  -4.75 MW   +49.0 -> +44.2 MW
  N2  UP  +4.75 MW   -90.0 -> -85.2 MW
  N3  -- no change   (+10.0 MW)

Line flows after redispatch:
  L0-1     +1.00 MW  (  2.0% of 50 MW)  [ok]
  L1-2    +50.00 MW  (100.0% of 50 MW)  [near-limit]
  L2-3    -40.00 MW  ( 80.0% of 50 MW)  [ok]
```

Here's how to read it:

- **Total cost** — the price of the fix. This is the number you're keeping low.
- **Node adjustments** — your to-do list:
  - **UP** = turn that station **up** by the shown amount.
  - **DN** = turn it **down**.
  - **no change** = leave it alone.
- **Line flows** — the result. Every line should say `[ok]` or `[near-limit]`.
  None should say `[OVERLOADED]`.

A picture of the grid (before vs. after) also pops up in a separate window, with
overloaded lines shown in red so you can see the problem and the fix.

### Step 5 — Enter the numbers in the game

Go back to FluxControl and set each station to the adjustment from the list
(UP = increase, DN = decrease). The numbers always add up to zero, so the grid
stays balanced — that's what unlocks the game's **Confirm** button.

Done! The overload is cleared at the lowest possible cost.

---

There's an example level, `level1.json`, already included — so you can try that
last command straight away, before touching the game.

---

## For the curious

Under the hood this solves a **DC optimal power flow** problem with on/off constraints: it finds the
cheapest change to power injections that keeps every line within its limit, using
the standard linear ("DC") approximation of how power flows through a grid. https://link.springer.com/content/pdf/bbm:978-3-642-17989-1/1.pdf
