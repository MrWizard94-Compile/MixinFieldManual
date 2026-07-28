# Chapter 1 — The Collision
### Priorities, merges, and the load-order lie

You will meet this crash. Maybe you already have.

Two well-written mods, both popular, both fine on their own. Put them in the same pack
and the game dies during boot with this (the message format is verbatim from Mixin
0.8.5's `Injector` — you'll see why every clause matters by the end of the chapter):

```
org.spongepowered.asm.mixin.injection.throwables.InvalidInjectionException:
  @At("INVOKE") on ...fix_frustum_dead_loop.MixinFrustum with priority 1000
  cannot inject into net/minecraft/client/renderer/culling/Frustum::
  offsetToFullyIncludeCameraCube(I)V merged by ...MixinFrustum_FixDeadLoop
  with priority 1000
```

And then — this is the cruel part — a *cascade* of unrelated errors, because the mixin
lifecycle aborted and took every other patch to that class down with it. The bug report
you receive will blame whichever mod's name appears last in the log. The actual cause is
neither mod being wrong. It's both mods being *right in the same place*.

This chapter is about why that happens, mechanically — because every fix in this manual
rests on understanding the application model, and because the two "obvious" fixes
(change the load order, bump your priority) fail for reasons that are invisible until
you know how mixins actually land on a class.

The running example is real: **Valkyrien Skies 2 × Immersive Portals on Forge 1.20.1**,
a boot crash I diagnosed and shipped a fix for in a compat mod called Valkyrien Portals.
We'll use the genuine classes, the genuine stack trace logic, and at the end you'll see
the genuine fix — which is neither of the obvious ones.

---

## 1.1 What actually happens when a mixin "applies"

Forget mods for a second. From the mixin processor's point of view, there are no mods —
there are **target classes** and there are **mixins registered against them**, gathered
from every `*.mixins.json` in the JVM, regardless of which jar contributed them.

When a target class is first loaded, the processor:

1. **Collects** every mixin (from every mod) that targets it.
2. **Sorts** them — by `priority`, then by tiebreakers you do not meaningfully control.
3. **Applies them in order**, one at a time, each transforming the *result* of the
   previous application. Overwrites replace method bodies. Injects add callbacks into
   whatever body exists *at that moment*. Shadows bind. Interfaces attach.
4. **Validates** as it goes — and if a mixin declares requirements that can't be met
   (that's `require`), the processor doesn't shrug. It throws, and the class's entire
   mixin construction aborts.

Three consequences fall out of this model, and each one kills a popular myth:

**Myth 1: "Mods patch the game."** No — mixins patch *the class as transformed so far*.
Your `@Inject` at `HEAD` of `tick()` doesn't inject into vanilla `tick()`; it injects
into `tick()` *after* every lower-priority mixin already had its way with it. Most days
this distinction is invisible. On collision day it's everything.

**Myth 2: "Load order decides who wins."** Mod loading order affects almost nothing
here. Sorting is by **priority** (default `1000`, set via `@Mixin(priority = ...)`), and
for *equal* priorities the tiebreak comes down to mixin-config registration ordering —
effectively alphabetical/discovery accidents you shouldn't build on and your users can't
reproduce. If your compat strategy depends on your config being named `aa_mymod.mixins.json`,
you don't have a strategy, you have a horoscope.

**Myth 3: "If both patches apply, both patches work."** Application order changes
*semantics*. An inject that lands before an overwrite is erased by it. An inject that
lands after an overwrite injects into the *overwritten* body — which may no longer
contain the instruction your `@At` was pointing at.

That third myth is where our crash lives.

## 1.2 The case: two mods fix the same vanilla bug

Minecraft's `Frustum.offsetToFullyIncludeCameraCube(int)` has a mild vanilla defect:
when the camera sits very far from the origin (say, on a Valkyrien Skies ship in the
shipyard region at coordinates in the millions — or in Immersive Portals' distant
dimension rendering), floating-point behavior can turn its adjustment loop into a
**dead loop**. The game doesn't crash; it just stops, forever, inside frustum math.

Both mods hit this in the wild. Both fixed it. Both fixes are correct:

- **Immersive Portals** ships `MixinFrustum_FixDeadLoop`, an `@Overwrite` of the whole
  method: a 10-iteration cap on the loop, an isometric-view early return its own
  renderer needs, and a rate-limited warning. Priority: default, `1000`.
- **Valkyrien Skies** ships `feature.fix_frustum_dead_loop.MixinFrustum`, an `@Inject`
  that plants a loop-counter guard at the `FrustumIntersection.intersectAab` call
  inside that same method. Priority: default, `1000`. And — load-bearing detail —
  `require = 1`: "if this injection can't apply, that is a critical failure."

Now walk the application model with both installed. The processor collects both mixins
against `Frustum`. Equal priority, so the ordering is a tiebreak accident. IP's
overwrite merges — the method body is now IP's replacement, and the processor records
that this method was **merged by a mixin at priority 1000**. Then VS's inject arrives,
also at 1000, targeting an instruction inside a method that a peer-priority mixin now
owns.

The processor refuses. Injecting into a method merged by a mixin of **equal or higher
priority** is treated as a conflict, not a merge. This isn't folklore — the check is
three lines in Mixin 0.8.5's `Injector`: a merged target from another mixin is
injectable only when `mergedPriority < injectorPriority`, strictly. Equal priority —
`1000 < 1000` — is false, so the injection fails, `require = 1` turns that failure
critical, `InvalidInjectionException` flies (the exact message that opened this
chapter, both priorities named), and the mixin construction for `Frustum` aborts. Every mod that touches `Frustum` — including
innocent bystanders — now fails on this class. Boot dies. The log blames whoever
touched it last.

Read that again and notice what it means: **this crash has no guilty party.** IP's
overwrite is the superset fix and its renderer genuinely needs the isometric branch.
VS's guard is defensively written — `require = 1` is *good practice* for a fix your mod
depends on. Two correct engineering decisions, one dead game.

## 1.3 Why the obvious fixes don't work

**"Bump the priority."** Suppose you maintain VS and set your inject's mixin to
priority 1001. Now it applies after IP's overwrite and — because it now *outranks* the
merger — the processor permits the injection... into IP's replacement body. You are now
injecting a loop guard into a method that already has a loop guard, at an injection
point (`intersectAab` call) that happens to still exist. It boots. It even works. Until
IP refactors its overwrite and your `@At` target vanishes, and the crash returns —
except now it only reproduces with a specific IP build, in other people's packs, and
every hour of debugging happens in your issue tracker. Priority games don't resolve
semantic collisions; they defer them to a worse day.

And if you *don't* maintain either mod — if you're the pack developer or the compat
modder — you can't change their priorities at all. Priority is baked into jars you
don't control.

**"Rename your config so it sorts first."** Same coin, other face. Equal-priority
ordering by config-name accident is not a contract; it's not even stable across mixin
versions. You cannot deterministically slot a third mixin *between* two equal-priority
mixins from other jars. There is no gap to slot into.

**"Ask one of them to remove their fix."** Genuinely the right *idea* — the fixes are
functionally redundant, one should yield. But you're now scheduling your pack's boot
around two upstream release cycles and a diplomatic negotiation. Meanwhile your game
doesn't start. What you want is the same *outcome* — one of the two mixins stands down —
achieved *locally, deterministically, and reversibly*.

## 1.4 The actual fix: cancel the redundant mixin

That tool exists: **MixinSquared** provides a `MixinCanceller` service — a hook that
runs *before mixins apply to a target class* and can remove a specific mixin from the
set, by name, regardless of which jar it came from and regardless of ordering.

Here is the shipped fix from Valkyrien Portals, verbatim minus its (extensive) javadoc:

```java
public final class DeadLoopFrustumCanceller implements MixinCanceller {

    private static final String VS_FRUSTUM_DEADLOOP_MIXIN =
            "org.valkyrienskies.mod.mixin.feature.fix_frustum_dead_loop.MixinFrustum";

    /** Resolved once: Immersive Portals supplies the surviving frustum overwrite. */
    private static final boolean IMMERSIVE_PORTALS_PRESENT = detectImmersivePortals();

    @Override
    public boolean shouldCancel(List<String> targetClassNames, String mixinClassName) {
        // Only intervene when IP is actually present, so VS keeps its own dead-loop
        // fix in packs that do not run Immersive Portals.
        return IMMERSIVE_PORTALS_PRESENT && VS_FRUSTUM_DEADLOOP_MIXIN.equals(mixinClassName);
    }

    private static boolean detectImmersivePortals() {
        try {
            // LoadingModList is populated at mod-discovery time, well before mixins
            // apply, so it is safe to query from this early-instantiated service.
            return net.minecraftforge.fml.loading.LoadingModList.get()
                    .getModFileById("immersive_portals") != null;
        } catch (Throwable t) {
            // If the FML lookup shape ever changes, assume present rather than let
            // the unhandled frustum collision crash the game.
            return true;
        }
    }
}
```

Registered via `META-INF/services/com.bawnorton.mixinsquared.api.MixinCanceller`, one
line: the class name. That's the entire mod surface for this fix — no mixin of its own.

Walk through why each decision is the way it is, because this small class is the
chapter's doctrine in miniature:

**Which mixin dies?** VS's — not because VS is wrong, but because IP's overwrite is
the **superset**: it contains the same 10-iteration cap *plus* isometric handling that
IP's own rendering requires. Cancel IP's instead and you fix the boot but break IP's
renderer. When two fixes are redundant, cancel the subset. Deciding that required
actually decompiling and reading both — Chapter 3 shows the tooling; there is no
shortcut around reading the code you're arbitrating between.

**Why is this deterministic when priorities weren't?** The canceller removes VS's
mixin from the target class's set *before application begins*, so VS's `require = 1`
check never runs — there's no failed injection to be critical about. No ordering, no
tiebreaks, no race. It behaves identically whether your jar loads first or last.

**Why the presence check?** Because in a pack *without* IP, VS's dead-loop fix is the
only one — cancelling it there would reintroduce a vanilla freeze. A compat mod's
patches must be conditional on the conflict actually existing. Note *where* the check
reads from: `LoadingModList`, which is populated at mod discovery, long before any
target class loads. The usual `ModList.get()` isn't built yet at canceller time —
early-lifecycle code has its own rules about what exists.

**Why does the catch block assume `true`?** Deliberate failure-direction choice. This
compat mod declares IP as a hard dependency, so "IP present" is the overwhelmingly
likely truth; if FML's internal API shifts under us, guessing "present" risks
double-fixed frustum behavior (harmless), while guessing "absent" risks the original
boot crash (fatal). When a guard can fail in two directions, pick the direction that
degrades instead of detonates. This principle gets a full chapter (7) because it is,
honestly, most of what separates compat mods people trust from compat mods people
uninstall.

## 1.5 The doctrine

Everything else in this manual builds on the model from this chapter, so here it is,
compressed:

1. **Mixins apply per target class, in priority order, each seeing the previous
   result.** Your patch lands on *their* output, or theirs on yours. Know which.
2. **Equal priorities are a coin flip you don't own.** Never ship behavior that
   depends on winning the tiebreak.
3. **Priority changes defer collisions; they don't resolve them.** Outranking an
   overwrite means injecting into code that can silently change shape under you.
4. **Collisions between correct mods are normal**, and they are *your* problem
   precisely when you're the one shipping the pack or the compat layer.
5. **The deterministic tools operate before application** — cancellers (this chapter),
   wrappers that compose instead of colliding (Chapter 5), and guards that fail soft
   (Chapter 7). Everything that operates *during* the ordering lottery is a horoscope.
6. **Cancel the subset, keep the superset — and prove it by reading both.** Arbitration
   without decompilation is guessing with extra steps.

Next chapter: the injection toolbox itself — six ways to touch a method, ranked by how
badly each coexists with strangers. Spoiler: the most popular one (`@Redirect`) is the
worst neighbor on the list, and the reason follows directly from the application model
you just learned.
