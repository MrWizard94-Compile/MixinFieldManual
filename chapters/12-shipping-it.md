# Chapter 12 — Shipping It
### Config hygiene, version policy, and the checklist that keeps the other eleven chapters honest

Everything before this chapter happens on your machine. This chapter is about the
moment it stops being yours: the config file the mixin processor reads in strangers'
packs, the version claims your metadata makes, the documentation that answers issues
while you sleep, and the release ritual that catches the mistakes each chapter warned
about — one last time, cheaply.

---

## 12.1 mixins.json hygiene

The config is small; every field is load-bearing. The shipped one, annotated:

```json
{
    "required": true,
    "minVersion": "0.8",
    "package": "com.valkyrienportals.mixin",
    "compatibilityLevel": "JAVA_17",
    "refmap": "valkyrienportals.refmap.json",
    "mixins": [
        "common.MixinEntityDragger",
        "common.MixinVsCoreChunkTrackerPortalDims",
        "common.MixinChunkMapCrossDimGuard",
        "common.MixinChunkManagementUntrackGuard"
    ],
    "client": [
        "client.MixinGameRendererPortalCamera",
        "client.LevelRendererPrepareCullFrustumInvoker",
        "client.MixinRenderSectionManagerPortalFog",
        "client.MixinValkyrienSkiesModShipUnloadGuard"
    ],
    "injectors": { "defaultRequire": 1 }
}
```

- **`mixins` vs `client` vs `server` is a correctness boundary, not organization.**
  A client-class mixin listed in the common array crashes dedicated servers — the
  class it targets doesn't exist there. Sort by *where the target class exists*,
  audit on every addition. (Renderer mixins, GUI, camera → `client`. Tick handlers,
  chunk tracking → `mixins`.)
- **`defaultRequire: 1` with per-mixin `require = 0` opt-outs** — this is the
  Chapter 7 doctrine encoded: loud by default, soft where you've *signed* for
  softness. The lazy inverse (`defaultRequire: 0` everywhere) turns every future
  typo'd selector into a silent no-op. Make silence a per-case decision.
- **`refmap` must match the build config** (Chapter 9) — a renamed refmap that no
  longer matches the gradle `mixin { add ... }` line ships a jar whose selectors
  can't translate. It fails only in production, naturally.
- **One config per concern.** If you grow a second family of patches (say, optional
  Create compat), a second `.mixins.json` gated by its own config plugin keeps
  presence-conditional mixins out of packs that don't need them.

## 12.2 Version policy: what you pin, what you tolerate, what you refuse

A compat mod makes compatibility *claims* in three places; keep them consistent:

**`mods.toml` dependency ranges** — the loader-enforced outer wall. Declare hard
dependencies on both sides of the seam you patch (this mod requires *both* VS and
IP), with ranges as wide as you've *actually verified* — no wider. A range you
haven't booted is a promise you haven't kept.

**Bytecode pins** (Chapter 6) — the javap-verified synthetic/obfuscated targets,
pinned to exact upstream builds, failing soft elsewhere. These are *narrower* than
your mods.toml range on purpose: the mod runs across the range; the pinned features
arm only where verified. The delta between the two ranges must appear in your
documentation ("on VS builds other than 2.4.11, feature X disarms — see boot log").

**The verified matrix in your changelog** — every release names the exact upstream
versions it was built and tested against:

```
1.1.0 — verified against: valkyrienskies-120-2.4.11, immersive-portals-3.0.8,
        embeddium-0.3.31, Forge 47.4.20 (MC 1.20.1)
```

That one line converts "does it work with X?" issues into self-service answers, and
turns every upstream update into a defined task: re-verify the matrix (re-run the
javap diffs from the Chapter 6 etiquette), not "hope."

**When to update the pins:** on a schedule you choose, not upstream's. `require = 0`
means their release day doesn't become your emergency. Batch pin-refreshes with your
own releases; the boot posture log (Chapter 7) tells affected users the truth in the
meantime.

## 12.3 Documentation that answers issues while you sleep

Three files, all of which you've now seen working in this book:

- **`KNOWN_ISSUES.md`** (Chapter 11's shape): symptom, hypothesis, measured verdicts,
  honest ownership, status. This is where "is this bug known?" gets answered without
  you, and where falsified diagnoses stay dead instead of resurrecting in every new
  issue thread.
- **Mixin javadocs as arbitration records.** Every non-trivial mixin in the shipped
  mod carries: the symptom it fixes, the measured root cause, why *this* mechanism,
  what it was pinned against, and the chosen failure direction. Expensive to write
  once; it's also your Chapter 4 audit trail, your Chapter 6 pin contract, and your
  Chapter 9 warning signature — the same paragraphs do all three jobs.
- **The boot posture log** (Chapter 7) — documentation that ships *inside* the
  runtime, which is the only place most users ever look.

## 12.4 The release checklist

Compressed from all twelve chapters — the point of the book on one page. Print
Appendix C; this is the annotated version.

**Build truth (Ch. 9):**
- [ ] Clean build; every warning fixed or signed with a javadoc paragraph
- [ ] Selector-bearing libraries' annotation processors registered; refmap present
      in the built jar and spot-checked
- [ ] All `remap = false` MC-name selectors verified against decompiled production
      bytecode this release, not last release

**Pin integrity (Ch. 3, 6):**
- [ ] `javap` re-run and diffed for every pinned descriptor against the *current*
      pack's jars
- [ ] `references/` decomp trees refreshed to match; arbitration javadocs still true

**Behavior (Ch. 5, 10, 11):**
- [ ] Boot matrix: pack with all targets present · each target absent · dedicated
      server · renderer variant (Sodium/Embeddium) if you touch rendering
- [ ] One in-game exercise per feature — "applies" is not "works"
- [ ] Every KNOWN_ISSUES entry marked "pending verify" actually verified or kept
      pending *in writing*
- [ ] All probe mixins stripped from the config and the jar

**Config & metadata (this chapter):**
- [ ] mixins.json arrays audited client/common; `require` posture per-mixin correct
- [ ] mods.toml ranges == what you actually booted; changelog states the verified
      matrix
- [ ] Boot posture logs present for every conditional feature (armed/disarmed/why)

**The last one:**
- [ ] Read your own log output from the final test boot, start to finish, once.
      You'll catch something. You always catch something.

## 12.5 Doctrine — and the end of the book

1. **The config file is doctrine encoded** — environment boundaries, require
   posture, refmap wiring. Audit it like code, because it is.
2. **Make only compatibility claims you've booted.** Ranges, pins, and changelog
   matrix must agree with each other and with reality.
3. **Upstream's release day is not your emergency** — that's what fail-soft pins and
   posture logs bought you. Spend the calm they purchased.
4. **Documentation is load-bearing**: the issue file, the arbitration javadocs, the
   boot log. Each one answers a class of question forever.
5. **The checklist is cheap and the alternative isn't.** Twenty minutes per release
   versus a weekend per incident. You did the engineering; let the ritual protect it.

Compat modding is unglamorous power: nobody screenshots the crash that didn't
happen. But every pack that boots clean with your seam-patches in it is a small
piece of infrastructure you built between strangers' code — deterministic where the
ecosystem was racy, measured where it was superstitious, soft-failing where it was
brittle. That's the craft. Ship it.
