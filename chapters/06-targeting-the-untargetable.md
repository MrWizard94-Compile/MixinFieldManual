# Chapter 6 — Targeting the Untargetable
### Synthetic lambdas, obfuscated internals, and the etiquette of version-pinning

Sometimes the code you must patch has no stable name. The compiler invented the
method (`init$lambda$17`), or the author's build pipeline deliberately scrambled it
(`org.valkyrienskies.core.impl.shadow.CY`, methods `a` through `a`, eleven of them).
Every tutorial tells you not to touch these. This chapter is about what to do when
"don't" isn't an option — because in compat work, the bug doesn't care whether its
home address is polite.

Two escalations, both shipped. Then the etiquette that makes them defensible.

---

## 6.1 Escalation one: the synthetic lambda

**Symptom:** with IP installed, VS throws a `ClassCastException` on *every* dimension
transit. Not a crash — worse, a per-transit error that also silently aborts cleanup
code downstream of the throw.

**Diagnosis** (decompiled from the production jar — Chapter 3 tooling): VS's client
ship-unload handler is a Kotlin lambda registered at init. In source, roughly:

```kotlin
val level = Minecraft.getInstance().level
if (level != null) {
    (level.chunkSource as ClientChunkCacheDuck).`vs$removeShip`(event.ship)  // ← CCE
}
val player = Minecraft.getInstance().player
if (player is PlayerKnownShipsDuck) player.vs_removeKnownShip(event.ship.id) // never runs
```

The cast assumes the chunk source is vanilla's `ClientChunkCache` (which carries VS's
duck mixin — Chapter 8). IP replaces the chunk source with its own
`ImmPtlClientChunkMap`, which doesn't. The cast throws at the first line, which also
kills the *unrelated* player-side cleanup below it.

Kotlin compiles that lambda to a **synthetic method** on the enclosing class:
`init$lambda$17(Lorg/valkyrienskies/core/api/events/ShipUnloadEventClient;)Lkotlin/Unit;`.
Synthetic, private, static, numbered by the compiler — and still just a method,
which means still a mixin target:

```java
@Mixin(value = ValkyrienSkiesMod.class, remap = false)
public abstract class MixinValkyrienSkiesModShipUnloadGuard {

    @WrapMethod(
        method = "init$lambda$17(Lorg/valkyrienskies/core/api/events/ShipUnloadEventClient;)Lkotlin/Unit;",
        require = 0)
    private static Unit vp$tolerateImmersivePortalsChunkSource(ShipUnloadEventClient event,
                                                               Operation<Unit> original) {
        ClientLevel level = Minecraft.getInstance().level;
        if (level == null || level.getChunkSource() instanceof ClientChunkCacheDuck) {
            return original.call(event);          // VS's assumption holds — run it untouched
        }
        // IP owns the chunk source: nothing for VS to clean there (correct, not a
        // band-aid). But preserve the player-side removal the CCE was aborting:
        LocalPlayer player = Minecraft.getInstance().player;
        if (player instanceof PlayerKnownShipsDuck knownShips) {
            knownShips.vs_removeKnownShip(event.getShip().getId());
        }
        return Unit.INSTANCE;
    }
}
```

Study the *shape* of the guard, because it's the template for every "their assumption
breaks under this other mod" fix:

- **Happy path untouched.** When the cast would succeed, `original.call` — VS's exact
  code runs. You haven't forked their behavior; you've fenced their assumption.
- **The skip is justified, not convenient.** The javadoc (and now this book) argues
  *why* skipping the chunk-source branch is correct: IP's chunk map holds no VS ship
  tracking, so there is genuinely nothing to remove. "It stopped throwing" is not a
  diagnosis; know what the skipped code was *for*.
- **Collateral damage restored.** The CCE was also aborting the known-ships removal.
  The wrap replicates it. Fixing the throw without restoring what the throw was
  blocking just trades a loud bug for a quiet leak.
- **`require = 0` with intent** (§6.3): on any VS build where the compiler numbered
  the lambda differently, the wrap silently doesn't apply — the CCE returns as
  recoverable log noise, instead of a hard mixin failure taking down the boot.

## 6.2 Escalation two: the shadow-obfuscated internal

**Problem** (from this mod's remote-ship-visibility feature): the fix requires
relaxing one dimension check inside vs-core's chunk tracker — a class shipped as
`org.valkyrienskies.core.impl.shadow.CY`, name-mangled, all methods `a`. No API, no
mappings, no source.

Process, exactly as shipped:

1. **Decompile the production jar** (CFR). Identify the class by its *behavior* —
   here, a `toString` helpfully self-identifying as `ChunkTrackingInfo`, and a
   per-chunk loop comparing `ship.getChunkClaimDimension()` against
   `player.getDimension()`.
2. **Pin the descriptor with `javap -p -s`** against the same jar (Chapter 3). Eleven
   methods named `a`; exactly one takes `(AABBd, AABBic, LevelYRange, ShipTransform,
   CY, ServerShipInternal, Set, Vector3d, DD, TreeSet, TreeSet, II)`. Copy it
   verbatim — it cannot be wrong, it came from the class file.
3. **Target the *interface call*, not the mangled structure.** Inside that method the
   one stable landmark is an invocation of `VsiPlayer.getDimension()` — an
   *unobfuscated internal interface*. Wrapping that call needs no knowledge of CY's
   locals or control flow:

```java
@Mixin(value = CY.class, remap = false)
public abstract class MixinVsCoreChunkTrackerPortalDims {

    @WrapOperation(
        method = "a(Lorg/joml/primitives/AABBd;Lorg/joml/primitives/AABBic;"
            + "Lorg/valkyrienskies/core/api/world/LevelYRange;"        // javap-pinned,
            + /* ...descriptor continues, copied verbatim... */ "II)V", // 2.4.11 bytecode
        at = @At(value = "INVOKE",
            target = "Lorg/valkyrienskies/core/internal/world/VsiPlayer;getDimension()Ljava/lang/String;"),
        require = 0)
    private static String vp$portalVisibleDimension(VsiPlayer player, Operation<String> original,
                                                    @Local(argsOnly = true) ServerShipInternal ship) {
        String actual = original.call(player);
        if (PortalShipVisibility.seesShip(player.getUuid(), ship.getId())) {
            return ship.getChunkClaimDimension();   // gate passes for portal-visible pairs
        }
        return actual;
    }
}
```

The `@Local(argsOnly = true)` capture pulls the `ServerShipInternal` parameter by
type — unique among the arguments, so no ordinal gambling (Chapter 2, §2.6). And note
what the wrapper *does*: it answers a question differently under a narrow predicate.
It doesn't reorganize obfuscated control flow it can't see. The less you assume about
the mangled parts, the longer the pin survives.

One build-side consequence: the annotation processor will warn `Cannot find target
method` for this selector — it can't statically model shadow classes. That's a
warning you **sign for** (Chapter 9, §9.6): a javadoc paragraph stating the descriptor
is bytecode-verified against 2.4.11 and the runtime match is what counts.

## 6.3 The etiquette of the pin

Both escalations bind to compiler accidents of one specific upstream build. That's
not a flaw to hide — it's a contract to write down. The four clauses:

**Pin publicly.** The mixin javadoc names the exact artifact (`decompiled from
valkyrienskies-120-2.4.11.jar`) and how the target was verified. Future-you, bumping
the dependency, reruns the same `javap` command and diffs.

**Fail soft, by chosen direction.** `require = 0` on every pinned target: on a build
where the lambda index shifted or the descriptor changed, the mixin *silently doesn't
apply* and the pack survives. Then — critically — decide what the world looks like
when it doesn't apply. Guard one: the CCE returns as log noise (recoverable — chosen
over a boot crash). Guard two: remote ships stay invisible (the pre-fix status quo).
Both degradations were *selected*, not discovered. If the no-apply world is
unacceptable, `require = 0` is wrong and you need a version check that refuses to
load instead.

**Make silence diagnosable.** A `require = 0` mixin that didn't apply announces
nothing by default. Pair pins with boot-time logging of the environment (mod versions
detected, features armed/disarmed) so "it silently does nothing" is answerable from a
log file. Chapter 7 systematizes this.

**Re-verify on every upstream bump — mechanically.** The pin's maintenance cost is
one `javap` + one diff per dependency update. Put it in the update checklist
(Chapter 12). A pin you don't re-verify is a `require = 0` feature quietly rotting.

## 6.4 When *not* to do any of this

The escalation ladder exists; climb it only after the lower rungs genuinely fail:
a real API or event → a duck/accessor on a *stable* class (Chapter 8) → a mixin on a
named, mapped method → an upstream PR asking for the hook you need (file it anyway,
even while shipping the pin) → and only then, the lambda or the shadow class. Pins
are debt with a documented interest rate. The etiquette above is what keeps the rate
fixed instead of compounding.

Next: the `require = 0` doctrine in full — graceful degradation as a design system
for compat mods that never, ever crash a stranger's pack.
