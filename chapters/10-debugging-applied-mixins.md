# Chapter 10 — Debugging Applied Mixins
### Seeing what actually landed, and bisecting a 300-mod pack without losing a weekend

Your mixin compiles. The pack boots. The feature doesn't work — or worse, something
*else* doesn't work, and a user with 287 mods says your name in a bug report. This
chapter is the observation toolkit: how to see the class as transformed, how to read
what the mixin processor is trying to tell you, and how to isolate a culprit in
logarithmic time instead of linear despair.

---

## 10.1 The flags: making the invisible visible

Three JVM flags (add to the pack/instance JVM arguments) cover most sessions:

**`-Dmixin.debug.export=true`** — the important one. Every transformed class is
written to `.mixin.out/` in the run directory as a `.class` file. Decompile it (CFR,
drag into your IDE) and you are looking at **the truth**: vanilla + every mod's
mixins, merged, in application order. Questions this settles in one look:

- Did my inject land, and *where* exactly? (Your handler method will be right there,
  named, with the callback wired in.)
- What did the other mod's overwrite leave of the method I targeted?
- Whose redirect owns that call now?
- Why does the applied control flow not match my mental model?

Habit from shipped work: when a mixin "applies but doesn't work," read the exported
class *before* adding a single log line. Half the time the bug is visible — your
injection landed after an early return, inside the wrong overload, behind another
mod's cancel.

**`-Dmixin.debug.verbose=true`** — promotes the processor's application chatter to
the log: each mixin as it applies, priorities, and — gold for Chapter 1-style
collisions — the *order* everything landed on a contested class.

**`-Dmixin.dumpTargetOnFailure=true`** — on an `InvalidInjectionException`, dumps the
target class as the processor saw it at failure time, so you can see exactly why your
selector missed (the instruction wasn't there / was already replaced).

## 10.2 Reading the failure signatures

The common exceptions, translated from processor-ese:

| Log says | It means | First move |
|----------|----------|------------|
| `InvalidInjectionException ... requires 1 injection(s) but 0 succeeded` | Selector matched nothing — wrong name/descriptor, wrong world (Ch. 9), or another mod removed the instruction | `dumpTargetOnFailure` + check the refmap inside your jar |
| `Cannot merge` / conflict on a `@Redirect` or `@Overwrite` | Two mods claimed the same instruction/method (Ch. 1, 2) | Verbose log for the other claimant; classify per Ch. 4 |
| `NoSuchMethodError` at *runtime*, not apply time | Your handler *body* calls something that doesn't exist in this environment — usually official-vs-SRG (Ch. 9) or a missing compile-only dep | Check which name-world the failing call belongs to |
| Mixin listed in verbose log but feature inert | Applied but never fires: wrong overload, guarded branch, or your `require = 0` pin didn't match on this build (Ch. 6, 7) | Export and read; check boot posture logs |
| CCE naming a class you've never heard of | Duck cast met a substituted object (Ch. 8) | `javap` the named class's interfaces |

## 10.3 Bisection: O(log n) launches, done honestly

When the report is "your mod breaks with [pack]," and the pack has 300 mods:

1. **Reproduce first.** Get the pack (or its mod list + configs). No repro, no bisect
   — "cannot reproduce, need logs/pack export" is a legitimate and *kind* reply.
2. **Halve the suspects, keep the skeleton.** Your mod + its hard dependencies +
   half the rest. Crash persists → culprit in the kept half; gone → other half.
   Loader/library mods travel together (removing a lib removes its dependents —
   move them as a block, or the bisect lies to you).
3. **Expect interaction pairs.** Compat bugs are often *triples*: you + A is fine,
   you + B is fine, you + A + B breaks (Chapter 5's nested-context bug was exactly
   this shape). When a lone suspect doesn't fall out, bisect for the *second* member
   with the first held fixed.
4. **Six to nine launches** covers 300 mods for a single culprit. Budget it, do it
   mechanically, resist the urge to reason your way out mid-bisect — hypotheses are
   for Chapter 11; bisection works *because* it doesn't need them.

Instance managers make this cheap: duplicate the instance once, disable in bulk.
Never bisect a user's only copy of their world. Copy first — and test on a copy of
their *save* too, since some interactions only fire with specific in-world state
(a ship parked at a portal, say).

## 10.4 Instrumentation mixins: probes you ship to yourself

Sometimes reading the applied class isn't enough — you need to know what the code
*sees at runtime*: which pass is executing, what's in the collection, which dimension
this object claims. The tool is a deliberately temporary **probe mixin**: an inject
whose only job is to log structured facts from inside someone else's code path.

Ground rules that made probes effective in the shipped project (Chapter 11 tells the
full story of what they discovered):

- **Tag every line** with a greppable marker (`[VP-SHIP]`, `[VP-DATA]`) — analysis
  happens in a log file at 2 a.m.; make it `grep`-shaped.
- **Log facts, not vibes**: counts, dimension ids, booleans, positions. The probe's
  output should be *evidence* usable in a falsification argument, not "got here!".
- **Rate-limit anything per-tick or per-frame** (heartbeat counters, log-every-N) or
  the probe changes the timing of the thing it observes and drowns the log.
- **Probes are scaffolding: strip them before release.** They live in their own mixin
  entries so removal is one line in the config plus one deleted file. A probe left in
  a shipped jar is a performance bug with your name on it. The shipped project's
  KNOWN_ISSUES file marks probes "(since stripped)" — the *findings* are recorded in
  documentation; the instrument is gone.

## 10.5 Doctrine

1. **Export beats speculation.** The transformed class is a fact you can read;
   read it before instrumenting, instrument before theorizing.
2. **Learn the five failure signatures** — nearly every mixin bug announces its
   category in the first log line, if you know the dialect.
3. **Bisect mechanically, in halves, on copies.** Reasoning during bisection is how
   a 9-launch job becomes a weekend.
4. **Probes log greppable facts, rate-limited, and never ship.** Findings go in the
   docs; instruments go in the bin.

Which raises the real question — what do you *do* with the facts a probe produces?
Next chapter: the measurement methodology that killed a beautiful, wrong hypothesis
and saved weeks of building the wrong fix.
