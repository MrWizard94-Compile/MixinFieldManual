# Chapter 9 — Dev Lies and Prod Truth
### The build pipeline, or: where mixins that work on your machine go to die

There is a special despair reserved for the mixin that works perfectly in `runClient`
and silently does nothing in the shipped pack. Or its mirror twin: dead in dev,
flawless in production. Neither is a mystery once you accept an uncomfortable fact:

**Your development environment and your players' game are running two different
programs with two different sets of names.**

This chapter maps the name-worlds, shows exactly where each translation happens in the
build, and walks the three real failure modes — each one taken from a shipped Forge
1.20.1 compat mod's build files, not from theory.

---

## 9.1 The three name-worlds

For Forge 1.20.1 (NeoForge's early versions inherit the same architecture; modern
NeoForge simplifies it — see the note in 9.6):

| World | `ServerPlayer.untrackChunk` is called... | Who lives here |
|-------|------------------------------------------|----------------|
| **Official (Mojmap)** | `untrackChunk` | Your dev source code, your IDE, `runClient` |
| **SRG** | `m_9088_` | **Production**: every player's runtime, every shipped mod jar |
| **Notch (obfuscated)** | one letter | Nobody you deal with; historical |

Your `gradle.properties` says which world your *source* lives in:

```properties
mapping_channel=official
mapping_version=1.20.1
```

You write `player.untrackChunk(pos)` and it compiles against a Minecraft artifact with
those friendly names. But the jar your players run calls `m_9088_`, because ForgeGradle's
`reobfJar` task remaps your compiled bytecode from official to SRG on the way out:

```groovy
tasks.named('jar', Jar).configure {
    // ...
    finalizedBy 'reobfJar'   // the moment your code changes languages
}
```

So far, so automatic — **for code**. Method bodies get remapped mechanically and you
never think about it. The pain lives entirely in the place `reobfJar` can't reach:
**strings inside your mixin annotations.**

## 9.2 The refmap: how your selectors survive translation

`@Inject(method = "updateChunkTracking", at = @At(target =
"Lnet/minecraft/server/level/ChunkMap;..."))` — those are *strings*. A bytecode
remapper doesn't rewrite string constants (imagine the carnage if it did). Instead, the
**mixin annotation processor** runs at compile time, resolves every selector you wrote
against the mappings, and writes the translations into a **refmap** — a JSON sidecar
shipped inside your jar:

```groovy
mixin {
    add sourceSets.main, "valkyrienportals.refmap.json"
    config "valkyrienportals.mixins.json"
}
```

At runtime, the mixin processor reads your selector, consults the refmap, and applies
the SRG name in production (or passes the official name through in dev). You can watch
this machinery in your build log if you know what the lines mean:

```
Note: ObfuscationServiceMCP supports [notch] ObfuscationServiceFG3 supports [searge]
Note: Loading searge mappings from ...\build\createMcpToSrg\output.tsrg
Note: Writing refmap to ...\build\tmp\compileJava\compileJava-refmap.json
```

**Failure mode #1 — the missing refmap entry.** If a selector never makes it into the
refmap, dev works (dev names need no translation) and production silently misses.
The classic cause in modern mixins is the next section, and it has bitten nearly
everyone shipping MixinExtras.

## 9.3 The annotation processor you forgot

The Sponge mixin AP knows how to refmap *Sponge's* annotations. It does **not** know
that MixinExtras' `@WrapOperation` carries its own `method` and `target` selectors —
unless MixinExtras' own annotation processor is also on the compile path. From a
shipped `build.gradle`, comment preserved because it was earned:

```groovy
annotationProcessor 'org.spongepowered:mixin:0.8.5:processor'
// MixinExtras' annotation processor — without it the Sponge mixin AP leaves
// @WrapOperation's own method/target selectors out of the refmap, so they would
// not resolve against SRG at runtime. This emits those SRG mappings.
annotationProcessor files("libs/mixinextras-0.4.1.jar")
```

Without that second line: every `@Inject` in the mod translates fine, every
`@WrapOperation` quietly fails to apply in production, and — if you followed the
`require = 0` doctrine from Chapter 7 — nothing even crashes to tell you. Your compat
feature is just... absent, in other people's packs, invisibly. This is the single most
cost-effective line in the whole build file.

**The rule:** every mixin *library* that adds annotations with selectors needs its AP
registered alongside Sponge's. Check this first when a wrap works in dev and vanishes
in prod.

## 9.4 `remap = false`: when you leave the translation system on purpose

Refmaps translate selectors that target *Minecraft* classes. When your mixin targets
**another mod's class** — VS's `ChunkManagement`, IP's `NewChunkTrackingGraph` — those
names are identical in dev and prod, so you declare `@Mixin(value = ..., remap = false)`
and the processor stops trying to translate.

Now the subtle trap. Inside a `remap = false` mixin, suppose your `@At` targets a call
*to a Minecraft method* — the other mod's bytecode calling `ServerPlayer.untrackChunk`.
No refmap entry will be generated for your selector. So the string you write must be
the name that exists **in the bytecode you'll actually run against** — and shipped mod
jars speak SRG:

```java
@Mixin(value = ChunkManagement.class, remap = false)
public abstract class MixinChunkManagementUntrackGuard {

    @WrapOperation(
        method = "tickChunkLoading",
        at = @At(value = "INVOKE",
            // SRG, on purpose: this selector is never refmapped, and the production
            // bytecode of the target mod calls m_9088_, not untrackChunk.
            target = "Lnet/minecraft/server/level/ServerPlayer;m_9088_(Lnet/minecraft/world/level/ChunkPos;)V"
        ),
        require = 0)
```

How do you *find* `m_9088_`? You don't guess and you don't trust wiki tables: you
decompile the actual jar from the actual pack (CFR one-liner in Appendix D) and read
what the call site says. The decompiled output of a production mod jar is SRG
ground truth by definition.

Note the corollary: this selector is *wrong* in a fully-deobfuscated dev runtime,
where the method is named `untrackChunk`. Which brings us to the honest part.

## 9.5 The dev runtime is partly a lie — decide where truth lives

Here's a `dependencies` block pattern from the same shipped mod:

```groovy
// Compile-only against the in-pack jars: nothing here is bundled into our output.
compileOnly files(".../mods/valkyrienskies-120-2.4.11.jar")
compileOnly files(".../mods/immersive-portals-3.0.8-all.jar")
compileOnly files(".../mods/embeddium-0.3.31+mc1.20.1.jar")
// VS's core API ships as a jar-in-jar, invisible to the outer jar's compile
// classpath — vendor it explicitly so those types resolve.
compileOnly files("libs/vs-api-1.1.0.jar")
// VS's client API returns Kotlin collections; resolving their supertypes needs the
// Kotlin stdlib. Kotlin-for-Forge supplies it at runtime, so this stays compile-only.
compileOnly files(".../mods/kotlinforforge-4.12.0-all.jar")

// Dev-only: production jars for runClient testing (no deobf — mixin phase only).
runtimeOnly files(".../mods/valkyrienskies-120-2.4.11.jar")
```

Three lessons compressed in there:

1. **Compile against the exact jars your pack runs.** Not Maven's idea of VS — the
   file in the instance's `mods/` folder. Compat code is version-married; make the
   compiler enforce the marriage.
2. **Jar-in-jar contents are invisible to your compile classpath.** VS embeds its core
   API inside its jar; your compiler can't see through that. Extract or vendor the
   inner jar (`vs-api-1.1.0.jar` here) as `compileOnly`. Same for language stdlibs
   that a language-loader mod (Kotlin-for-Forge) provides at runtime.
3. **Loading production (SRG) mod jars into an official-names dev runtime only half
   works** — the comment says it out loud: *mixin phase only*. Classes load, mixins
   apply or refuse, boot succeeds or crashes — that much is testable in dev. Actual
   cross-mod behavior calls SRG names your dev Minecraft doesn't have. The shipped
   mod's answer, and this manual's: **dev verifies compilation and mixin application;
   the real pack verifies behavior.** Budget for a pack-launch test cycle; it is not
   optional and pretending otherwise is how "works in dev" ends up in your changelog.

## 9.6 Warnings you fix, warnings you sign for

Zero-warning builds are the right default. But obfuscated-target work produces exactly
one warning class you cannot engineer away:

```
warning: Cannot find target method "a(Lorg/joml/primitives/AABBd;...)V"
         for @WrapOperation ... in org.valkyrienskies.core.impl.shadow.CY
```

The AP is validating your selector against a *shadow-obfuscated* class it can't
statically model. The method exists — you pinned its descriptor with `javap` against
the production jar (Chapter 6) — and runtime application succeeds. The discipline is
not "suppress warnings" and not "tolerate warnings": it's **sign for them
individually**. Each accepted warning gets a javadoc paragraph on the mixin stating
why it fires, why it's unavoidable, and what evidence backs the selector. An accepted
warning without a signature is just a warning you got used to.

*(NeoForge note: shortly after splitting from Forge in the 1.20.x line, NeoForge
dropped SRG as the runtime intermediary — development and production both use Mojang's
official mappings, so the refmap dance and the `remap = false` selector traps largely
disappear there. The jar-in-jar, exact-version, and dev-vs-pack-truth lessons survive
intact. If you target both loaders, this chapter is your Forge appendix and your
NeoForge history lesson.)*

## 9.7 The pre-ship checklist

Before any compat release leaves your machine:

- [ ] `build` clean; every warning either fixed or **signed** (9.6)
- [ ] MixinExtras (and any other selector-bearing library) AP registered (9.3)
- [ ] Refmap present *inside the built jar*; spot-check one translated selector
- [ ] All `remap = false` selectors that touch MC names verified against decompiled
      production bytecode, not memory (9.4)
- [ ] Compiled against the pack's exact dependency jars; versions recorded in the
      changelog (9.5)
- [ ] Boot test **in the real pack**: target mods present, absent, and the
      renderer-swap case (Sodium/Embeddium) if you touch rendering
- [ ] One in-game behavior check per feature — dev proved it *applies*; only the pack
      proves it *works*

Chapter 10 picks up from the last checkbox: what to do when the pack says no —
`mixin.debug.export`, audit mode, and bisecting a 300-mod pack in O(log n) launches.
