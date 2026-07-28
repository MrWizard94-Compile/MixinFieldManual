# Chapter 11 — Probes and Measured Claims
### Diagnosing like an engineer, or: the beautiful hypothesis that measurement killed

This is the chapter I most wish someone had handed me earlier, and it contains almost
no mixin syntax. It's about the discipline that decides whether your next twenty hours
of compat work fix the actual bug or a plausible imaginary one. The case study is
real, the probes are real, and — this is the point — **the first hypothesis was
wrong**, in exactly the way your first hypothesis is usually wrong: it was the
explanation that required no further looking.

---

## 11.1 The bug and the beautiful hypothesis

**Symptom:** with Valkyrien Skies + Immersive Portals, a VS ship parked on the far
side of a portal does not render through the portal. Terrain shows fine; the ship is
simply absent.

**The obvious hypothesis** — the one that assembles itself in your head unbidden:
*it's a rendering bug.* Ships render through a special path (Embeddium render-section
lists, per-ship transforms — Chapter 5 territory); IP's nested passes are exotic;
surely the ship's render sections never get built in the nested pass. The fix would
be render-pipeline surgery: force-build ship sections during portal rendering.

Notice the hypothesis's seductive properties: it's consistent with the symptom, it
fits the prior ("render stuff breaks in nested passes — we've fixed three of those
already"), and it suggests an *actionable* fix. None of those properties make it true.

## 11.2 Probe one: interrogate, don't assume

Instead of building the fix, the project shipped itself a probe (Chapter 10 rules:
greppable tag, facts not vibes, strip after): an inject at the tail of Embeddium's
`createTerrainRenderList`, walking every loaded ship in both the main and nested
passes, logging dimension match and render-section state. Condensed findings, straight
from the project's issue log:

```
[VP-SHIP] pass=nested dimMatch=true  sectionsNonNull=120 built=120
[VP-SHIP] pass=nested dimMatch=false sections=0   (overworld ships, nether RSM)
[VP-SHIP] loadedShips = {128, 57, 125, 126, 127}  ← all overworld; nether ships absent
```

Two facts, one fatal to the hypothesis:

1. When the renderer's dimension matched the ship's, sections were present **and
   fully built — in the nested pass too** (`built=120`). The render pipeline was
   *fine*. Hypothesis falsified, in one probe, before any fix was built.
2. The remote dimension's ships weren't failing to render — they were **absent from
   the client's ship list entirely**. The nether ships sitting in plain view of the
   portal did not exist as far as the client knew.

The bug had just moved down a layer: from rendering to data. A ship that isn't on the
client can't render through any pipeline, however patched.

## 11.3 Probe two: pre-commit to a decision matrix

New question: *why* is the remote ship missing client-side? Two candidate branches
with very different fixes:

- **Branch A:** the client has the ship's metadata but never "loads" it → fix is a
  client-side shim (promote to loaded, pull the chunks). Cheap.
- **Branch B:** the server never sends remote-dimension ships at all → fix needs
  server cooperation. Expensive, architectural.

The second probe was designed *with the decision matrix written first*: log
`getAllShips()` vs `getLoadedShips()` bucketed by dimension; if remote ships appear
in `all` but not `loaded` → branch A; absent from `all` entirely → branch B. Result:

```
[VP-DATA] in OW:      overworld{all=5, loaded=5}   the_nether{all=0, loaded=0}
[VP-DATA] in Nether:  the_nether{all=2, loaded=2}  overworld{all=0, loaded=0}
```

Branch B, unambiguously. The client-side shim — the cheap fix, half-built in
imagination already — was **falsified before it was written.** The project's issue
log records both verdicts with the word "FALSIFIED" in caps, dated, with the probe
named, and the eventual fix (a server-side tracking change) cites them as its
justification.

## 11.4 The method, extracted

Six practices, each one visible in the story:

**1. Hypotheses are written down and falsifiable.** "The RSM never builds ship
sections in nested passes" is a claim a probe can kill. "Rendering is broken
somehow" is not. If you can't state what log line would *disprove* your theory, you
don't have a theory, you have a mood.

**2. Probes are designed to distinguish, not to confirm.** Probe two existed because
two branches *diverged*; its decision matrix was written before the data came back.
Pre-commitment is the vaccine against reading whatever you want in the logs.

**3. Findings get evidence classes.** The project's docs grade every claim:
**Measured/Established** (a probe said so, reproducibly) · **Supported** (measured
once) · **Working Hypothesis** (believed, untested) · **Falsified** (measured dead —
and *kept in the record*). The grade travels with the claim; six months later you
know which foundations are load-bearing measurement and which are old vibes.

**4. Falsified hypotheses are results, not embarrassments.** The dead render-pipeline
theory stays in the log with its probe data, because the *next* maintainer will have
the same beautiful idea — and now it costs them thirty seconds of reading instead of
a week of building.

**5. The fix cites its evidence.** The eventual server-side fix's documentation
references the probe findings by name. Code review question upgraded: not "does this
look right?" but "does the diagnosis this is built on still hold?"

**6. Measurement changes the budget, not just the direction.** Branch B meant the
real fix was expensive. That's exactly the information a time-boxed side-project
developer needs *before* spending the hours — the probes cost an evening; the wrong
fix would have cost weeks and then still not worked.

## 11.5 The lightweight version for your project

You don't need a research bureaucracy. The shipped project's overhead is one markdown
file (`KNOWN_ISSUES.md`) with a fixed shape per entry:

```
### N. <symptom, one line>
- Observed: <date, world/pack, exact conditions>
- Hypothesis: <falsifiable claim>          ← updated as probes rule things out
- Measured: <probe tag, findings, VERDICT — supported/FALSIFIED>
- Owner: <whose bug it really is — be honest>
- Status: <diagnosed / fix built pending verify / verified / deferred>
```

Two habits complete it: probes get greppable tags and get stripped (Chapter 10), and
every status that says "pending in-game verify" *means it* — a fix that compiles is a
hypothesis about a fix until the pack says otherwise (Chapter 9, §9.5).

That's the whole method. It fits in an evening, and it's the difference between compat
modding as guess-compile-pray and compat modding as engineering.

Next, the last chapter: shipping — version pinning policy, config hygiene, and the
release checklist that keeps all twelve chapters honest at once.
