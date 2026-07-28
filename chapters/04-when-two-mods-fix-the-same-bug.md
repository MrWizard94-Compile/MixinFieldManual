# Chapter 4 — When Two Mods Fix the Same Bug
### The resolution playbook: cancellers, config plugins, and choosing who yields

Chapter 1 used the Valkyrien Skies × Immersive Portals frustum collision to teach the
application model, and showed the shipped fix in miniature. This chapter is the
practitioner's version: the *complete* decision framework for redundant-patch
collisions, the two conditional-application tools and exactly when each applies, and
the parts of the shipped canceller that Chapter 1 glossed over.

The scenario, recapped in one line: two mods patch `Frustum.offsetToFullyIncludeCameraCube`
with functionally identical dead-loop fixes — IP via `@Overwrite`, VS via `@Inject
(require = 1)`, equal priority — and the mixin processor's conflict rules turn two
correct patches into a boot crash.

---

## 4.1 First, classify the collision

Not every collision is the same disease. Diagnose before prescribing:

**Type A — Redundant fixes** (this chapter): both patches exist to achieve the *same
outcome*. One of them can simply not-happen and nothing of value is lost. The
frustum case: both cap the same loop.

**Type B — Conflicting intentions**: both patches change the same code toward
*different* outcomes. Nobody can yield without losing their feature; you need
composition, not cancellation — that's Chapter 5's wrap hierarchy, or a genuine
either/or config choice for the user.

**Type C — Fragile adjacency**: the patches don't logically conflict, but one's
transformation breaks the other's assumptions (an overwrite that removes an inject's
anchor instruction, an inject whose cancel skips a peer's TAIL). Usually fixed by the
*victim* re-anchoring (Chapter 3's durable-anchor ranking) or wrapping instead.

Classifying honestly requires reading both patches (Chapter 3 tooling). Type A is the
happy case — and it's more common than you'd think, because popular vanilla bugs
attract independent fixes like streetlights attract moths.

## 4.2 The resolution ladder for Type A

In order of preference:

**Rung 1 — Upstream PR / issue.** The *systemically* correct fix: one mod detects the
other and stands down (`ModList`-gated config plugin, next section — trivial for an
author to add). File the issue with both class names, the exception, and the
subset/superset analysis; maintainers merge well-diagnosed compat patches far more
often than vague "ur mod crashes with X" reports. Do this *even when you also ship a
local fix* — your compat mod should aspire to obsolescence.

**Rung 2 — Cancel the redundant mixin locally.** When you can't wait for two release
cycles (your pack is dead *today*), MixinSquared's `MixinCanceller` removes the
chosen mixin before application, deterministically. This is the shipped fix from
Chapter 1, and §4.4 finishes its anatomy.

**Rung 3 — Priority/ordering games.** Not a rung. A trapdoor painted like a rung
(Chapter 1, §1.3).

## 4.3 The two conditional tools — and the ownership line between them

Both tools make a mixin *not apply*. The difference is whose mixin:

**`IMixinConfigPlugin.shouldApplyMixin` — for YOUR mixins.** Every mixin config can
name a plugin class; the processor asks it, per mixin, "apply this one?" This is how
you make your own patches conditional on environment — renderer choice, presence of
another mod, config flags. Valkyrien Skies itself does this (its
`ValkyrienCommonMixinConfigPlugin` gates Sodium-path vs vanilla-path render mixins on
which renderer is live). If IP or VS wanted to fix the frustum collision upstream,
this is the one-class change: detect the peer in `LoadingModList`, skip your own
dead-loop mixin. **You cannot use it on someone else's mixin** — plugins govern only
the config they're attached to.

**MixinSquared's `MixinCanceller` — for THEIR mixins.** A service-loaded hook,
registered via `META-INF/services/com.bawnorton.mixinsquared.api.MixinCanceller`,
consulted before mixins apply to a target class, able to cancel any mixin by class
name across all configs. It exists precisely because the ecosystem needed a
deterministic way for a *third party* to arbitrate between two mods that don't know
about each other. Load-order independent: cancellation happens during collection, not
during the application race.

The ownership line generates the rule of thumb: **shipping a compat mod? You'll use
MixinSquared. Maintaining one of the colliders? Add the config-plugin gate and free
the whole ecosystem from needing the compat mod at all.**

## 4.4 Anatomy of a shipped canceller — the parts that earn their keep

Chapter 1 printed `DeadLoopFrustumCanceller` in full. Four engineering details
deserve the slow-motion replay:

**The subset/superset audit is the actual work.** The code is twelve lines; the
*decision* — cancel VS's guard, keep IP's overwrite — took decompiling both patches
and confirming IP's replacement contains everything VS's guard provides (10-iteration
cap) *plus* behavior IP's own renderer requires (isometric early-return). Write this
audit down in the class javadoc. Six months later, when a VS update changes its fix,
the javadoc is what tells you whether your cancellation is still valid.

**Presence-gating keeps you from becoming the bug.** `shouldCancel` returns true only
when IP is actually installed. Without that check, your compat mod in an IP-less pack
would cancel VS's *only* dead-loop fix and reintroduce a vanilla freeze — you'd have
turned a compat patch into a sabotage patch. Every canceller needs an "is the
conflict actually present?" gate.

**Early-lifecycle rules are different rules.** Cancellers run before mixins apply —
before mod construction, before `ModList` exists. The shipped code queries
`LoadingModList` (populated at discovery time) and wraps even that in a try/catch,
because early-lifecycle APIs are the least stable surface in the loader. Know what
exists at your execution time; when in doubt, decompile the loader too.

**Failure direction is a design decision, not an accident.** The catch block assumes
"IP present." Wrong-but-present → double fix, harmless. Wrong-but-absent → boot crash
returns. When a guard can fail two ways, *choose* the way that degrades. (Chapter 7
builds a whole doctrine on this.)

And one detail that's easy to miss: the compat mod's main class **logs the
arbitration at boot** —

```java
LOGGER.info("[ValkyrienPortals] Active. MixinSquared detected; the Valkyrien Skies "
        + "frustum dead-loop mixin is cancelled in favour of Immersive Portals' overwrite.");
```

— and logs an ERROR with installation instructions when MixinSquared is missing.
Silent arbitration is undiagnosable arbitration. When a user's pack behaves oddly,
that log line is the difference between a five-minute answer and an afternoon.

## 4.5 What "resolved" means

A Type A collision is resolved when all of these hold:

- [ ] Both mods' *outcomes* survive (the bug stays fixed for everyone; nobody's
      feature regressed) — verified in-game, not by reading
- [ ] The resolution is deterministic across load orders and mixin versions
- [ ] It deactivates itself when the conflict is absent (presence gate)
- [ ] It announces itself in the log (and its absence-of-prerequisites louder)
- [ ] The arbitration reasoning is written where the next maintainer will look
- [ ] An upstream issue exists, so the fix can eventually retire

Six checkboxes for twelve lines of code — which is the honest ratio for compat work.
The code was never the hard part.

Next: Type B, where nobody can yield — and the wrap hierarchy that lets two mods
disagree about the same call and both be right on schedule.
