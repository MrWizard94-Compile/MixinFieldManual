# Chapter 3 — Reading the Target
### Mappings, descriptors, and finding your injection point

Chapters 1 and 2 assumed you already knew *where* to inject. This chapter is about
earning that knowledge, because the difference between a modder who fears
`Cannot find target method` and one who fixes it in five minutes is not talent — it's
a small toolkit and the habit of reading bytecode-adjacent output without flinching.

The skill matters double in compat work: you're not just reading Minecraft (mapped,
documented, discussed on every Discord), you're reading *other mods* — sometimes
Kotlin-compiled, sometimes jar-in-jar'd, occasionally deliberately obfuscated. The
same three tools handle all of it.

---

## 3.1 Descriptors: the five-minute literacy course

Every method in the JVM is identified by name + **descriptor** — the parenthesized
parameter list and return type in JVM notation. You've been writing them in `@At`
targets all along:

```
Lnet/minecraft/server/level/ServerPlayer;m_9088_(Lnet/minecraft/world/level/ChunkPos;)V
└──────────── owner class ──────────────┘└name┘└───────── descriptor ──────────────┘
```

The grammar fits on an index card:

| Code | Type | | Code | Type |
|------|------|-|------|------|
| `V` | void | | `J` | long |
| `Z` | boolean | | `F` | float |
| `B` | byte | | `D` | double |
| `I` | int | | `Lpkg/Name;` | object type |
| `S` | short | | `[X` | array of X |
| `C` | char | | | |

So `(Lorg/joml/Vector3d;DD)Z` reads: takes a `Vector3d` and two doubles, returns
boolean. That's the entire language. Everything else in this chapter is about finding
the *correct* string to write — because a descriptor that's plausible-but-wrong
produces the same "cannot find target" as one that's nonsense, and guessing costs a
full launch cycle per guess.

## 3.2 Tool one: `javap` — ground truth from the jar you'll run against

`javap` ships with every JDK and disassembles class files *from the exact jar your
pack loads*. When a target is obfuscated, synthetic, or just suspicious, this is the
authority — not the wiki, not the mappings site, not your memory:

```
javap -p -s -classpath valkyrienskies-120-2.4.11.jar org.valkyrienskies.core.impl.shadow.CY
```

`-p` shows private members, `-s` prints signatures (descriptors). Real output, from
pinning a shadow-obfuscated tracker method for a shipped mixin:

```
private static final void a(org.joml.primitives.AABBd, org.joml.primitives.AABBic,
    org.valkyrienskies.core.api.world.LevelYRange, ...);
  descriptor: (Lorg/joml/primitives/AABBd;Lorg/joml/primitives/AABBic;Lorg/valkyrienskies/
               core/api/world/LevelYRange;...DDLjava/util/TreeSet;Ljava/util/TreeSet;II)V
```

Copy the descriptor verbatim into your `method = "a(...)"` selector. It cannot be
wrong; it came from the class file. When a class has eleven methods named `a` (welcome
to obfuscation), the descriptor is the *only* disambiguator — and `javap` hands you
all eleven so you can match parameter shapes against the decompiled logic.

## 3.3 Tool two: CFR — decompilation as standard practice

You cannot arbitrate between two mods' patches (Chapter 1), pick an injection point,
or verify a fix without reading the code you're patching. For mods without published
sources — or where you must verify the *shipped* bytecode rather than trust a repo —
decompile:

```
java -jar cfr.jar --outputdir decomp/ immersive-portals-3.0.8-all.jar
```

CFR handles Kotlin-compiled classes better than most (you'll get readable, if
verbose, Java from Kotlin bytecode — synthetic lambdas included, which Chapter 6
needs). Practical habits from shipped work:

- **Keep a `references/` directory in the compat project** with the decompiled trees
  of every mod you patch, pinned to the exact versions in your pack. Your injection
  points, your arbitration decisions, and your bug diagnoses all cite line numbers in
  these trees; when you bump a dependency, re-decompile and diff.
- **Decompile the production jar, not the dev artifact.** The production jar is what
  your selectors run against — SRG names and all (Chapter 9). CFR output of a shipped
  Forge mod shows `m_9088_`-style calls; that's not noise, that's *the answer key* for
  your `remap = false` selectors.
- **Legality, plainly:** decompiling for interoperability is the community norm and
  most mod licenses (and the loaders themselves) operate on that assumption. You're
  reading to coexist, not to copy. Don't paste decompiled code into your mod; write
  your own.

## 3.4 Choosing the injection point

You've found the method. Where in it do you land? Ranked by durability across upstream
updates:

1. **`HEAD` / `RETURN` / `TAIL`** — survive almost any refactor of the body. If your
   logic works as "before anything" or "after everything," take the durable option.
2. **`INVOKE` on a stable call** — `@At(value = "INVOKE", target = ...)` pointing at a
   call the method *must* make to do its job (the `prepareCullFrustum` call inside
   `renderLevel`, say). Refactors move these less often than you'd fear; pick calls
   that are semantically load-bearing, not incidental.
3. **`INVOKE` with `ordinal`** — the *n*-th occurrence of a call. Now you're coupled
   to how many times upstream calls something. Every upstream release is a dice roll.
4. **`FIELD`, `CONSTANT`, offset-y `slice` gymnastics** — sometimes necessary, always
   a version-pin (Chapter 6's etiquette applies: pin, `require = 0`, document).

Cross-check your chosen point three ways before writing the mixin: the decompiled
source (does the logic surround it the way you think?), `javap -c` if you need
instruction-level certainty, and — after writing it — the applied-class export
(Chapter 10) to see what actually happened.

## 3.5 Mappings archaeology, quickly

For Minecraft's own classes you'll mostly live in official names and let the refmap
translate (Chapter 9). The two lookups you still do by hand:

- **Official → SRG** (for `remap = false` selectors): your own build prints the
  mapping file location (`build/createMcpToSrg/output.tsrg` — grep it), or read the
  SRG name straight out of a decompiled production mod that calls the method. The
  second is my habit: it verifies the mapping *and* the call site in one look.
- **"What is this `f_1234_` field?"** (reading decompiled production code): reverse
  the same tsrg file, or load the decompiled tree next to a mapped dev workspace and
  match shapes. Tedious the first week; automatic by the third.

## 3.6 Doctrine

1. **The jar is the truth.** Wikis, repos, and memory describe what someone intended
   to ship; `javap` and CFR show what your players actually run.
2. **Descriptors are copied, never composed by hand.** Every hand-typed descriptor is
   a launch-cycle-long bug waiting to be found.
3. **Keep the `references/` decomp tree, pinned and diffable.** Compat work is a
   citation-based discipline; cite line numbers, re-verify on every dependency bump.
4. **Prefer durable anchors** (HEAD/TAIL, load-bearing INVOKEs) **and treat fragile
   ones as version-pins** with the full pin etiquette.
5. **Read before you arbitrate.** Chapter 1 said it and it bears repeating: deciding
   which of two colliding patches yields, without reading both, is guessing with
   extra steps.

Part II starts next: five shipped war stories, beginning with the full resolution
playbook for the collision Chapter 1 diagnosed.
