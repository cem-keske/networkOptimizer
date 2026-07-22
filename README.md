# FluxControl Solver

A little helper for the online game **[fluxcontrol.eu](https://fluxcontrol.eu)**.

In the game you are running a small electricity grid. Some power lines are
**overloaded** (carrying more than they can handle), and your job is to fix that
as **cheaply as possible** by turning each power station up or down, and by
connecting or disconnecting some power lines.

This tool does the hard maths for you and tells you the cheapest possible way to
remove the congestion. You copy a level out of the game, run one command, and it
tells you exactly how much to change each station, or which lines to connect or
disconnect.

![The solver on a 6-node level. Left: one line (red) is overloaded. Right: the cheapest fix, switching one line off and adjusting a couple of stations, clears the overload for 71.77 EUR.](docs/solver_screenshot.png)

---

## Requirements

1. **Python.** You can get it from [python.org](https://www.python.org/downloads/).
2. **Gurobi**, required to solve the optimization problem. Get the free licence at
   [gurobi.com](https://www.gurobi.com/) (it is free for students and academics).
3. **This tool.** Click the green **Code** button on the GitHub page, choose
   **Download ZIP**, and unzip it somewhere easy to find.

That is the setup. Now the fun part.

---

## How to use it

### Step 1: Add the "Export" button to your browser (one time)

Open a terminal, go into the tool's folder, and run:

```
python grid_solver.py --bookmarklet
```

It prints a long line starting with `javascript:...`. Copy the one under
**"DOWNLOAD bookmarklet"**.

Now add it as a bookmark in your browser:

- Right-click your bookmarks bar and choose **Add page** (or **New bookmark**).
- **Name:** anything, for example `Export FluxControl`.
- **URL / Address:** paste the `javascript:...` line you copied.
- Save.

You now have an **Export FluxControl** button in your browser.

### Step 2: Grab the level from the game

1. Open **fluxcontrol.eu** and start the level you want to solve.
2. Click your **Export FluxControl** bookmark.

Your browser downloads a small file called something like `levelX.json`. That
file is just the puzzle, saved.

### Step 3: Solve it

Back in the terminal, run this (adjust the file name and location to match what
got downloaded):

```
python grid_solver.py "C:\Users\YourName\Downloads\levelX.json"
```

You can add a few options here too:

- `--no-switching` solves using only station up and down changes, without
  connecting or disconnecting any lines. Use this if you want a solution that
  keeps the grid wiring exactly as it is.
- If you leave out the file name entirely, the tool reads the level straight from
  your clipboard instead. This works with the "COPY bookmarklet" (the other line
  printed in Step 1), which copies the level instead of downloading a file.

### Step 4: Read the answer

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

Here is how to read it:

- **Total cost** is the price of the fix. This is the number you are keeping low.
- **Node adjustments** are your to-do list:
  - **UP** means turn that station up by the shown amount.
  - **DN** means turn it down.
  - **no change** means leave it alone.
- **Line flows** are the result. Every line should say `[ok]` or `[near-limit]`,
  and none should say `[OVERLOADED]`.

A picture of the grid (before versus after) also pops up in a separate window,
with overloaded lines shown in red so you can see the problem and the fix.

### Step 5: Enter the numbers in the game

Go back to FluxControl and set each station to the adjustment from the list
(UP to increase, DN to decrease). The numbers always add up to zero, so the grid
stays balanced, and that is what unlocks the game's **Confirm** button.

Done. The overload is cleared at the lowest possible cost.

---

There is an example level, `level1.json`, already included, so you can try that
last command straight away before touching the game.

---

## For the curious

Under the hood this solves a **DC optimal power flow** problem with on/off
constraints: it finds the cheapest change to power injections that keeps every
line within its limit, using the standard linear ("DC") approximation of how
power flows through a grid. For background, see Zhu's
*Optimization of Power System Operation* [[ref]][opf-ref].

[opf-ref]: https://link.springer.com/content/pdf/bbm:978-3-642-17989-1/1.pdf
