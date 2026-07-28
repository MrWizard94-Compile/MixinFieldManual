# Chapter 8 — Ducks, Accessors, Invokers
### Talking to classes you don't own — and the cast that exploded

Injection changes what code *does*. Just as often, compat work only needs to change
what code *can be asked*: read a private field, call a private method, attach one new
capability to a vanilla object. Mixin's answer is three related tools — accessors,
invokers, and duck interfaces — and they're blessedly boring right up until the
ecosystem's favorite failure mode: **the duck that isn't there.**

---

## 8.1 Accessors and invokers: private API, minus the reflection tax

An accessor mixin is an interface whose methods mixin binds directly to a target's
private members:

```java
// From Valkyrien Skies — reaching ChunkMap's private updateChunkTracking:
@Mixin(ChunkMap.class)
public interface ChunkMapAccessor {
    @Invoker("updateChunkTracking")
    void callUpdateChunkTracking(ServerPlayer player, ChunkPos pos,
                                 MutableObject<ClientboundLevelChunkWithLightPacket> cache,
                                 boolean wasLoaded, boolean load);
}
// usage: ((ChunkMapAccessor) level.getChunkSource().chunkMap).callUpdateChunkTracking(...)
```

`@Accessor` generates a getter/setter for a field; `@Invoker` a bridge to a method.
No reflection, no `setAccessible`, no per-call overhead — the mixin processor wires
it at class-load. When to reach for one instead of an injection: **you need to *use*
existing behavior from a new call site**, not modify it where it lives.

The shipped example of that distinction, from Chapter 5: the portal-camera wrap
bypasses VS's camera logic but still must run vanilla's private
`prepareCullFrustum`. Wrong tool: a second injection replicating vanilla's body
(now you maintain a fork of it). Right tool:

```java
@Mixin(LevelRenderer.class)
public interface LevelRendererPrepareCullFrustumInvoker {
    @Invoker("prepareCullFrustum")
    void vp$invokePrepareCullFrustum(PoseStack poseStack, Vec3 cameraPos, Matrix4f projection);
}
```

Two hygiene rules: **prefix your accessor methods** (`vp$...`) — the interface is
glued onto a shared class, and two mods both adding `callTick()` is a name collision
you cause; and remember accessors follow the same mapping rules as selectors — the
string `"prepareCullFrustum"` is refmapped (Chapter 9), so official names in source,
SRG at runtime, automatically — *unless* you're `remap = false`, in which case write
the runtime name.

## 8.2 Duck interfaces: attaching capability to someone else's object

A duck goes one step further: the mixin *implements a new interface* on the target
and carries new state or behavior with it. VS's client chunk cache duck, from the
decompiled production jar:

```java
@Mixin(ClientChunkCache.class)
public abstract class MixinClientChunkCache implements ClientChunkCacheDuck {
    @Unique
    private final LongObjectMap<LevelChunk> vs$shipChunks = new LongObjectHashMap<>();

    @Override
    public LongObjectMap<LevelChunk> vs$getShipChunks() { return this.vs$shipChunks; }

    @Override
    public void vs$removeShip(ClientShip ship) { /* drop the ship's chunks */ }
}
```

Now any code holding a `ClientChunkCache` can do
`((ClientChunkCacheDuck) chunkSource).vs$getShipChunks()` — vanilla's object,
carrying VS's ship-chunk storage. Ducks are how mods bolt whole subsystems onto
vanilla without wrappers or global maps keyed by identity. Design rules that age
well:

- **Prefix everything** — interface methods *and* `@Unique` fields (`vs$shipChunks`).
  The target class is a shared apartment; label your boxes.
- **Keep ducks dumb**: storage and narrow operations. Logic that *uses* the duck
  belongs in your own classes, where it's testable and mappable.
- **The duck is a contract with a hidden clause** — which brings us to the explosion.

## 8.3 The cast that exploded

The `instanceof`-free duck cast is idiomatic all over the ecosystem:

```kotlin
(level.chunkSource as ClientChunkCacheDuck).`vs$removeShip`(event.ship)
```

The hidden clause: this assumes **the object in that slot is the class your mixin
patched.** Your mixin made `ClientChunkCache` a `ClientChunkCacheDuck` — it did not
make *every possible chunk source* one. Enter Immersive Portals, which replaces
`ClientLevel.getChunkSource()`'s object with its own `ImmPtlClientChunkMap` — a
separate class, not a subclass carrying the mixin. The cast throws
`ClassCastException` on every dimension transit, and (Chapter 6's war story) the
throw also aborts unrelated cleanup below it.

Nobody erred, exactly. VS duck-typed a vanilla slot; IP substituted the slot's
occupant; both are standard practice. The lesson is for *your* code on both sides of
the contract:

**When you consume a duck, `instanceof` is not optional politeness:**

```java
if (level.getChunkSource() instanceof ClientChunkCacheDuck duck) {
    duck.vs$removeShip(ship);
}
// else: this slot's occupant isn't ours — decide the else-branch consciously (Ch. 7)
```

That pattern-match cast costs nothing and converts "another mod swapped the object"
from a crash into a chosen degradation. The shipped guard in Chapter 6 is exactly
this check retrofitted around VS's unguarded cast — with the else-branch doing the
work the exception used to abort.

**When you provide a swappable object** (fewer of you, but it happens): you've broken
every duck that was riding the original. Either extend the vanilla class so mixins
and ducks come along, or document loudly that your substitute is duck-free.

**When you diagnose a mystery CCE naming a class you've never heard of:** it's this.
Some mod's duck cast met some other mod's substitute object. `javap` the named class
for its interfaces, find whose duck is missing, and you know both parties in under
ten minutes.

## 8.4 Choosing between the three (and a fourth option)

| Need | Tool |
|------|------|
| Read/write a private field of a class you don't own | `@Accessor` |
| Call a private method from your own code | `@Invoker` |
| Attach new state/capability that travels with the object | Duck (`implements` + `@Unique`) |
| Attach state to objects you *can't* mixin (final, dynamic, other-mod-swapped) | Your own `WeakHashMap`/capability keyed by the object |

That fourth row is the honest fallback the CCE story motivates: when the slot's
occupant isn't guaranteed to be any particular class, stop attaching state to the
class and key it externally. VS's own Embeddium compat does exactly this where it
must (a `WeakHashMap<ClientShip, SortedRenderLists>` inside its render mixin) — weak
keys, so the map never outlives the objects.

## 8.5 Doctrine

1. **Accessors/invokers over reflection, always** — free at runtime, mapping-aware,
   and they fail at *apply time* (visible) rather than call time (3 a.m.).
2. **Reuse beats replication:** if bypassing someone's wrapper leaves you needing
   vanilla behavior, invoke vanilla — don't fork its body into your mod.
3. **Prefix every name you glue onto a shared class.** Fields and methods both.
4. **A duck cast without `instanceof` is a bet that no other mod exists.** You know
   better by now — and the else-branch is a Chapter 7 decision, not an afterthought.
5. **When the slot itself is contested, attach nothing** — external weak-keyed state
   is humbler and survives everyone's substitutions.

Part III next — the chapters that assume your mixin is *written* and ask whether it
actually works: the build pipeline (Chapter 9, if you haven't read it yet — many will
have jumped there first, and that's fine), debugging applied mixins, and the probe
methodology.
