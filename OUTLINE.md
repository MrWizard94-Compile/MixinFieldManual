# The Mixin Field Manual
### Cross-mod compatibility for Forge & NeoForge modders — from someone who ships it

**Product:** ~120-page technical manual (PDF + Markdown source bundle), $29 launch / $39 standard, Gumroad.
**Positioning:** Not a mixin tutorial — the internet has those. This is the book about what happens
when your mixin meets *other people's mixins* in a 300-mod pack, written from shipped compat mods
(Valkyrien Portals, OmniFix) with the real stack traces, the real fixes, and the discipline that
keeps them from crashing strangers' games.
**Buyer:** intermediate modders who can write an @Inject but lose days to conflicts, refmap mysteries,
and "works in dev, dies in prod."
**Format rule:** every Part II chapter is a war story — symptom → diagnosis → mechanism → fix → doctrine.
All code excerpts are from real shipped mods, verbatim.

**STATUS 2026-07-03: ALL 12 CHAPTERS + APPENDICES DRAFTED** (`chapters/`). Ch. 4 was re-scoped
during drafting: instead of repeating Ch. 1's frustum story it now delivers the full resolution
playbook (collision taxonomy A/B/C, the resolution ladder, IMixinConfigPlugin vs MixinSquared
ownership line, canceller anatomy). Remaining production work: author review pass, code-excerpt
verification pass, PDF layout, cover, presale page.

---

## Part I — Foundations (how mixins actually apply)

**1. The Collision: priorities, merges, and the load-order lie** ✅ DRAFTED
Two mods patch the same vanilla method; the game dies at boot with `InvalidInjectionException`.
How mixin application actually works (per-target merge, priority ordering, why equal priorities
are a coin you don't control), why "just change mod load order" is a lie, and the anatomy of the
real Valkyrien Skies × Immersive Portals frustum crash.

**2. The Injection Toolbox — and the blast radius of each tool**
@Inject / @Redirect / @Overwrite / MixinExtras (@WrapOperation, @WrapMethod,
@ModifyExpressionValue, @Local). Ranked not by power but by *how badly each one coexists*:
why @Redirect is a compat landmine, why @WrapOperation chains and @Redirect doesn't, when
@Overwrite is honest. Decision table included.

**3. Reading the Target: mappings, descriptors, and finding your injection point**
Official/Mojmap vs SRG vs runtime reality; what a refmap actually contains; using `javap -p -s`
to pin exact descriptors from the jar you'll run against (real example: pinning a
shadow-obfuscated vs-core method). The skill that turns "cannot find target" from a wall
into a five-minute task.

## Part II — War Stories (each one shipped)

**4. When Two Mods Fix the Same Bug: the frustum dead-loop collision**
VS and IP both patch `Frustum.offsetToFullyIncludeCameraCube` — functionally identical fixes
that crash each other. Why priority games and config renaming can't fix it, and the MixinSquared
`MixinCanceller` solution: cancelling the redundant mixin deterministically, load-order
independent, with a runtime presence check so the cancel only fires when both mods exist.
Source: Valkyrien Portals `DeadLoopFrustumCanceller`.

**5. Wrapping the Wrapper: composing over another mod's @WrapOperation**
VS wraps `prepareCullFrustum` to reposition the camera on ships; that wrap also fires inside
IP's nested portal render and blanks the pane. Fix: a priority-2000 wrap over the same call that
bypasses VS only mid-portal-render — plus the self-calibrating matrix trick (measure the ship
bank as B = MAIN·L⁻¹ each frame instead of assuming it). MixinExtras chaining semantics
explained properly. Source: `MixinGameRendererPortalCamera`.

**6. Targeting the Untargetable: synthetic lambdas and obfuscated internals**
Two escalations: (a) wrapping a Kotlin synthetic (`init$lambda$17`) to fix a ClassCastException
VS throws on every dimension change under IP; (b) mixing into a shadow-obfuscated vs-core class
(`CY`) with a javap-pinned descriptor and @Local capture. When this is justified, how to pin it
to one upstream version, and how to make it fail soft everywhere else.
Sources: `MixinValkyrienSkiesModShipUnloadGuard`, `MixinVsCoreChunkTrackerPortalDims`.

**7. The require=0 Doctrine: compat mods that never crash a stranger's pack**
Graceful degradation as a design system, not a flag: what require=0 actually trades away, boot-time
presence logging so silent no-ops are diagnosable, LoadingModList checks before mixins apply, and
the "recoverable log noise beats a hard crash" decision rule — when it's right and when it's cowardice.

**8. Ducks, Accessors, Invokers: talking to classes you don't own**
Duck interfaces done properly (and the trap: a duck cast that explodes when *another* mod swaps
the object out from under you — the `ImmPtlClientChunkMap` vs `ClientChunkCacheDuck` CCE, diagnosed
and guarded). Accessor/Invoker mixins for private vanilla internals. Source: VP unload guard +
`LevelRendererPrepareCullFrustumInvoker`.

## Part III — Production Discipline

**9. Dev Lies and Prod Truth: the build pipeline**
Why your mixin works in runClient and dies in the pack (or vice versa): refmap generation, the
MixinExtras annotation processor you forgot, reobfJar, remap=false selectors that must name SRG,
compiling against production jars. The exact gradle wiring from a shipped compat mod.

**10. Debugging Applied Mixins**
`-Dmixin.debug.export`, audit mode, reading transformed bytecode, bisecting a 300-mod pack in
O(log n) launches, and instrumentation mixins you strip before release.

**11. Probes and Measured Claims: diagnosing like an engineer**
The VP methodology: write a probe mixin, log the actual state (dimensions, section counts,
watch lists), classify findings (Established / Supported / Falsified), and let measurements kill
your favorite hypothesis early. Includes the real case where the "render pipeline is broken"
theory died to a probe and saved weeks.

**12. Shipping It: versioning against upstream, mixins.json hygiene, release checklist**
Pinning vs loosening, defaultRequire policy, what belongs in `client` vs `mixins`, changelog
discipline for compat mods, and the pre-release checklist (boot with target absent, target
present, both + Embeddium/Sodium, dedicated server).

## Appendices
A. Selector & @At cheat sheet · B. MixinExtras quick reference · C. The Compat Checklist
(printable) · D. Tooling: javap/CFR recipes for decompiling your dependencies legally and fast.

---

## Production notes
- Chapters 4–6, 8, 11 lift code verbatim from Valkyrien Portals (author-owned). OmniFix modules
  feed chapters 7 and 12. Nothing needs upstream permission — all excerpts are the author's own code.
- Draft order: 1 ✅ → 2 → 9 (the three most-searched pains) → war stories 4–6 → rest.
- Companion repo (Pro tier upsell, later): runnable example pack of each pattern.
- Cross-sell: RepoForge Pro gets one line in the appendix; this manual gets one line in RepoForge's README.
