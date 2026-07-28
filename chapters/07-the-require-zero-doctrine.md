# Chapter 7 — The require=0 Doctrine
### Compat mods that never crash a stranger's pack

A compat mod occupies the most exposed position in the ecosystem: it patches the seams
*between* mods, it ships to packs you'll never see, and it binds to upstream builds you
don't control. When it fails — and across enough version combinations, it will — the
only question that matters is **how**. This chapter is the design system for making
every failure a degradation instead of a detonation.

The headline tool is `require = 0`, but the doctrine is bigger than a flag. It's four
practices that only work together.

---

## 7.1 What `require` actually promises

Every injector carries a `require` count: how many injections must succeed or the
mixin application is a *critical failure* — the exception from Chapter 1, the aborted
class, the dead boot.

- **`require = 1` (or the config default)** says: *this game must not run without my
  patch.* That's the right claim for a mod's own core fixes — Valkyrien Skies marking
  its dead-loop guard `require = 1` was correct in isolation; a VS world without that
  guard can freeze.
- **`require = 0`** says: *if my patch can't land, the game goes on without it.* The
  right claim for compat patches, because the alternative math is brutal: your compat
  mod targeting upstream build X, in a pack that updated to build Y, with `require = 1`,
  is a mod that **crashes the pack for everyone as punishment for a version bump you
  didn't approve.** The bug you were fixing returns either way; `require` only decides
  whether it returns alone or brings a boot loop with it.

The decision rule, compressed: **`require` encodes whose failure it is.** Your own
mod's invariant → fail loud, `require = 1`. A patch over *someone else's* code shape →
fail soft, `require = 0`, because the shape was never yours to guarantee.

## 7.2 Choose every failure's direction

`require = 0` handles "the mixin didn't apply." Real compat code has a dozen more
failure points — presence checks, early-lifecycle API calls, casts, reflection — and
each one fails in *some* direction whether you choose it or not. Choose it.

The worked example from the shipped canceller (Chapter 4): a try/catch around a
`LoadingModList` query returns `true` ("assume IP present") on any throw, because the
two wrong outcomes aren't symmetric — wrongly-present means a harmless double-fix,
wrongly-absent means the boot crash returns. The general procedure:

1. Enumerate the guard's two wrong answers.
2. Price each one (crash? corruption? cosmetic noise? missing feature?).
3. Hard-code the failure toward the cheaper wrong answer.
4. Write the price analysis in a comment, because the next reader will "fix" an
   undocumented asymmetry back into a coin flip.

And its sibling from Chapter 6: when a pinned mixin doesn't apply, *what world does
the user get?* The unload-guard's answer — the old ClassCastException as recoverable
log spam — was **selected** over a hard failure, with the selection written into the
javadoc. If the no-apply world were unacceptable (data corruption, say), the honest
tool isn't `require = 0`, it's refusing to load with a clear version-mismatch message.
Graceful degradation is only graceful if you've looked at where it lands.

## 7.3 Silence must be diagnosable

Here's the cost of all this softness: a compat mod built on `require = 0` and
defensive gates can end up *silently doing nothing* — wrong upstream version, missing
prerequisite, cancelled feature — while the user experiences "I installed the fix and
nothing changed." If diagnosing that takes a debugger, you've shipped a support
burden, not a mod.

The countermeasure is boot-time posture logging. The shipped mod's entire main class
is this:

```java
public ValkyrienPortals() {
    if (classPresent("com.bawnorton.mixinsquared.api.MixinCanceller")) {
        LOGGER.info("[ValkyrienPortals] Active. MixinSquared detected; the Valkyrien "
                + "Skies frustum dead-loop mixin is cancelled in favour of Immersive "
                + "Portals' overwrite.");
    } else {
        LOGGER.error("[ValkyrienPortals] MixinSquared is NOT on the classpath. The "
                + "frustum-conflict canceller cannot run, so the Valkyrien Skies / "
                + "Immersive Portals boot crash will occur. Install MixinSquared "
                + "(bundled with Supplementaries) alongside this mod.");
    }
}
```

Anatomy of a good posture log: **states what will happen** (not just what was
detected), **names the consequence of the missing prerequisite** ("the boot crash
will occur"), and **tells the user the fix** ("install MixinSquared, bundled with
Supplementaries"). One log line converts a mystery bug report into a self-service fix.

Scale the pattern with the mod: one INFO line per feature at boot — *armed* or
*disarmed and why* — plus sparse runtime heartbeats for tick-driven features (the
ship-transit handler logs `[VP-TRANSIT] alive: loadedShips=N` every five seconds at
debug level; when a user says "ships won't teleport," the first question — *is the
handler even running?* — is answered by grep).

## 7.4 Gate on presence, at the right lifecycle moment

Every conditional patch needs an "is the conflict/partner actually here?" gate, and
*where you ask* matters as much as asking:

- **Before mixins apply** (cancellers, config plugins): `ModList` doesn't exist yet.
  Query `LoadingModList` — populated at discovery — and treat even that as unstable
  API (try/catch, chosen failure direction).
- **At mod construction**: classpath probes (`Class.forName(name, false, loader)`)
  for library presence, as above. The `false` matters — probe without initializing.
- **At runtime**: the context-owner's own API (`PortalRendering.isRendering()`,
  Chapter 5) rather than re-derived heuristics.

Wrong-lifecycle presence checks are a classic silent-failure source: code that asks
`ModList` during mixin plugin evaluation gets an absent answer and disarms a feature
that should be armed — and without §7.3's logging, nobody ever learns why.

## 7.5 When the doctrine is cowardice

Graceful degradation has a failure mode of its own: using `require = 0` as a way to
avoid *finding out* whether your mixin applies. Symptoms: no posture logging, no
version pin documentation, no answer to "what happens when it doesn't apply," a
changelog that never mentions verified-against versions. That's not resilience;
that's shipping "maybe" with extra steps.

The doctrine is legitimate only as a *package*:

- [ ] `require = 0` on patches over code shapes you don't own — and `require = 1`
      kept for invariants that are genuinely yours
- [ ] Every guard's failure direction chosen by priced comparison, documented inline
- [ ] The no-apply world identified and accepted in writing (or the mixin upgraded to
      a hard version check instead)
- [ ] Boot posture logging: every feature announces armed/disarmed-with-reason
- [ ] Presence gates at the correct lifecycle stage, themselves failure-directed
- [ ] Pins re-verified on every upstream bump (Chapter 6's etiquette, Chapter 12's
      checklist)

Six checkboxes again. The flag is one keystroke; the doctrine is why users trust the
mod that carries it.

Next: ducks, accessors, and invokers — the machinery for talking to classes you don't
own, and the shipped story of a duck cast that exploded when a third mod swapped the
object underneath it.
