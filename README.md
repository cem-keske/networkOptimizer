# FluxControl Solver

A little helper for the online game **[fluxcontrol.eu](https://fluxcontrol.eu)**.

In the game you're running a small electricity grid. Some power lines are
**overloaded** (carrying more than they can handle), and your job is to fix that
as **cheaply as possible** by turning each power station up or down.

This tool does the hard maths for you. You copy a level out of the game, run one
command, and it tells you exactly how much to change each station — the cheapest
possible answer. You then type those numbers back into the game.

You do **not** need to be a programmer to use it. Just follow the steps below.

---

## What you need first (one-time setup)

You only ever do this once.

1. **Install Python** — download it from [python.org](https://www.python.org/downloads/)
   and run the installer. On Windows, tick **"Add Python to PATH"** during install.
2. **Install Gurobi** — the maths engine this tool uses. Get the free licence at
   [gurobi.com](https://www.gurobi.com/) (it's free for students and academics),
   then install it.
3. **Download this tool** — click the green **Code** button on the GitHub page →
   **Download ZIP** → unzip it somewhere easy to find, like your Desktop.

That's the setup. Now the fun part.

---

## How to use it (every time you play)

The whole thing is 5 short steps.

### Step 1 — Add the "Export" button to your browser (one time)

Open a terminal (on Windows: search for **PowerShell**), go into the tool's
folder, and run:

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

You now have an **Export FluxControl** button in your browser. This is a
one-time thing — it stays there forever.

### Step 2 — Grab the level from the game

1. Open **fluxcontrol.eu** and start the level you want to solve.
2. Click your **Export FluxControl** bookmark.

Your browser downloads a small file called something like `level1.json` into
your **Downloads** folder. That file is just the puzzle, saved.

### Step 3 — Solve it

Back in the terminal, run this (adjust the file name/location to match what got
downloaded):

```
python solve_level.py "C:\Users\YourName\Downloads\level1.json" --no-switching
```

> **Tip:** The `--no-switching` part matters. It tells the tool to only turn
> power stations up and down — the exact kind of change the game lets you make.
> Leave it off and the tool may suggest disconnecting a line, which the game
> won't accept.

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

## Quick reference

| I want to...                                | Type this                                             |
| ------------------------------------------- | ----------------------------------------------------- |
| Set up the Export button (one time)         | `python solve_level.py --bookmarklet`                 |
| Solve a downloaded level (game-friendly)    | `python solve_level.py level1.json --no-switching`    |
| Try it right away with the included example | `python solve_level.py level1.json --no-switching`    |

There's an example level, `level1.json`, already included — so you can try that
last command straight away, before touching the game.

---

## Common hiccups

- **"python is not recognised"** — Python isn't installed, or "Add to PATH"
  wasn't ticked. Reinstall Python and tick that box.
- **The Export bookmark does nothing** — make sure a level is actually loaded and
  visible in the game before you click it.
- **Something about a Gurobi licence** — Gurobi isn't installed or activated. See
  the free-licence link in the setup section above.
- **The numbers won't "Confirm" in the game** — double-check you entered every UP
  and DN exactly; the game only accepts the solution when everything balances.

---

## For the curious (optional)

Under the hood this solves a **DC optimal power flow** problem: it finds the
cheapest change to power injections that keeps every line within its limit, using
the standard linear ("DC") approximation of how power flows through a grid. The
optimisation is handled by Gurobi. You don't need to know any of that to use it.
