# Appendices

## Appendix A — Selector & @At cheat sheet

**Method selector forms** (in `method = "..."`):
```
tick                                          bare name (unique methods only)
tick()V                                       name + descriptor (always prefer)
init$lambda$17(L.../EventClass;)Lkotlin/Unit; synthetic — pin the full descriptor
```

**Descriptor grammar:** `V` void · `Z` bool · `B` byte · `S` short · `C` char ·
`I` int · `J` long · `F` float · `D` double · `Lpkg/Class;` object · `[X` array.
`(Lnet/minecraft/world/level/ChunkPos;)V` = "takes ChunkPos, returns void."

**@At values, by durability (most → least):**

| Value | Anchors at | Notes |
|-------|-----------|-------|
| `HEAD` | first instruction | survives any body refactor |
| `RETURN` | every return | with `ordinal` for a specific one |
| `TAIL` | final return | |
| `INVOKE` | a method call | `target=` full owner+name+descriptor; the compat workhorse |
| `INVOKE_ASSIGN` | after call's result stored | |
| `FIELD` | field get/put | `opcode=` GETFIELD/PUTFIELD/GETSTATIC/PUTSTATIC |
| `NEW` | constructor call | |
| `CONSTANT` | LDC of a constant | fragile; constants get inlined/folded |
| `INVOKE` + `ordinal` | n-th matching call | version-pin etiquette applies (Ch. 6) |

**Injector quick-pick (Ch. 2):** value change → `@ModifyExpressionValue` /
`@ModifyReturnValue` / `@ModifyArg` · add behavior/guard → `@Inject` (cancel on
narrow predicates only) · conditional bypass/composition → `@WrapOperation` /
`@WrapMethod` · call replacement → still `@WrapOperation` · whole method → 
`@Overwrite` + ownership (Ch. 2 §2.5). `@Redirect`: legacy only.

---

## Appendix B — MixinExtras quick reference

| Annotation | Signature shape | Chains with strangers? |
|------------|-----------------|------------------------|
| `@WrapOperation` | `(args of call, Operation<Ret>, [@Local...])` — call `original.call(...)` or don't | Yes — nests by priority, higher = outer; wraps other mods' `@Redirect`s as the original |
| `@WrapMethod` | `(method args, Operation<Ret>)` — whole-method wrap | Yes |
| `@ModifyExpressionValue` | `(Ret value) -> Ret` at the producing instruction | Yes — output feeds next mod's input |
| `@ModifyReturnValue` | `(Ret value) -> Ret` at RETURN | Yes |
| `@Local` | extra handler param; capture by type; `argsOnly = true` for parameters | n/a — prefer unique types over ordinals |

Build requirement (Ch. 9): MixinExtras' own **annotation processor** must be on
`annotationProcessor` alongside Sponge's, or its selectors miss the refmap — works
in dev, silently dead in production.

Priority mnemonic: **"outranks = wraps around."** Priority 2000 wraps around 1000;
its `original.call` *is* the 1000 wrap. Say the jurisdiction as a sentence in the
javadoc (Ch. 5).

---

## Appendix C — The Compat Checklist (print me)

**Before writing:**
- [ ] Both sides decompiled into `references/`, pinned to pack versions (Ch. 3)
- [ ] Collision classified: redundant / conflicting / fragile-adjacent (Ch. 4)
- [ ] Smallest tool chosen; any `@Redirect` has a written justification (Ch. 2)
- [ ] Upstream issue filed, even if also fixing locally (Ch. 4)

**While writing:**
- [ ] Discriminators use the context-owner's API, not heuristics (Ch. 5)
- [ ] Duck casts guarded by `instanceof`, else-branch chosen consciously (Ch. 8)
- [ ] Pins: descriptor from `javap`, `require = 0`, no-apply world identified,
      javadoc contract written (Ch. 6)
- [ ] Every guard's failure direction priced and documented (Ch. 7)
- [ ] Names prefixed (`yourmod$...`) on everything glued to shared classes (Ch. 8)

**Before shipping** — the full release checklist is Chapter 12 §12.4; short form:
- [ ] Warnings fixed or signed · refmap in jar · SRG selectors re-verified
- [ ] javap diffs re-run for all pins · boot matrix (present/absent/server/renderer)
- [ ] One in-game exercise per feature · probes stripped
- [ ] mixins.json client/common audit · changelog states verified versions
- [ ] Boot posture logs: every conditional feature announces armed/disarmed/why

---

## Appendix D — Tooling recipes (javap & CFR)

**Pin a descriptor from the exact jar your pack runs:**
```
javap -p -s -classpath <mod.jar> full.class.Name
```
`-p` private members, `-s` descriptors. Copy descriptors verbatim — never compose
by hand. Eleven methods named `a`? Match parameter shapes against the decompile.

**Instruction-level view (checking an @At anchor):**
```
javap -p -c -classpath <mod.jar> full.class.Name > Name.bytecode.txt
```

**Decompile a whole mod:**
```
java -jar cfr.jar --outputdir references/<modname>_decomp/ <mod.jar>
```
CFR handles Kotlin-compiled bytecode acceptably (synthetic lambdas visible by name —
exactly what Ch. 6 targets). Keep decomp trees in `references/`, refresh + diff on
every dependency bump.

**Find who owns a mystery class in a pack:**
```
for %j in (mods\*.jar) do @jar -tf "%j" | findstr /i "TheClass" >nul && echo %j
```
(POSIX: `for j in mods/*.jar; do unzip -l "$j" | grep -qi TheClass && echo "$j"; done`)

**Official ↔ SRG lookup without leaving your build:** your compile prints the tsrg
location (`build/createMcpToSrg/output.tsrg`) — grep it in either direction. Or read
the SRG name straight from the decompiled *production* jar of any mod calling the
method: that verifies mapping and call site in one look (Ch. 3).

**Extract a jar-in-jar for the compile classpath (Ch. 9):**
```
jar -xf <outer-mod.jar> META-INF/jarjar/
```
then reference the inner jar via `compileOnly files(...)`.

---

*End of the Mixin Field Manual. Every code excerpt in this book is from shipped,
working mods; every war story cost a real evening. May your packs boot clean.*
