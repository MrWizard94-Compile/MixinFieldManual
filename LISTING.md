# The Mixin Field Manual — Gumroad Listing Kit (Presale)

## Product name
**The Mixin Field Manual — Cross-Mod Compatibility for Forge & NeoForge Modders**

## Structure on Gumroad (two products)
1. **Free:** "Mixin Field Manual — Sample Chapter" → `build/MixinFieldManual-Sample.html`
   exported to PDF. Price $0+, email collection ON. This is the funnel.
2. **Paid presale:** full manual. **$29 presale** ("early-bird — ships as PDF on
   [DATE, ~2 weeks out]; you'll get it automatically") → **$39** after delivery.
   Buyers get first-edition updates free.

## Cover
Commission/generate in the RepoForge visual family (anvil/forge theme — "field manual"
military-handbook styling works well: stencil title, worn texture). 1280×720 for
Gumroad, same art on the PDF title page later.

## Description (paste into Gumroad)

---

**Your mixin works. Then someone installs it next to 300 other mods.**

Every mixin tutorial teaches you to patch Minecraft. None of them teach you the actual
hard part: your patch landing on code that five other mods have already transformed —
where a correct `@Inject` and a correct `@Overwrite` can crash a pack *because both
authors were right*.

The Mixin Field Manual is about that part. It's written from shipped compatibility
mods — the kind that make Valkyrien Skies coexist with Immersive Portals — and every
chapter is built on real code, real stack traces, and real measured diagnoses. Nothing
in it is theoretical.

**Part I — Foundations.** How mixins *actually* apply (priorities, merges, and why
load order is a lie) · every injector ranked by how well it coexists with strangers ·
reading any target — mapped, synthetic, or obfuscated — with javap and CFR.

**Part II — War Stories.** Five shipped fixes, each one symptom → diagnosis →
mechanism → fix → doctrine: resolving redundant patches with cancellers · composing
your wrap over another mod's wrap (including measuring their transform instead of
guessing it) · targeting synthetic Kotlin lambdas and shadow-obfuscated internals
without your mod rotting · the require=0 doctrine · the duck cast that exploded.

**Part III — Production Discipline.** Why mixins work in dev and die in production
(refmaps, annotation processors, SRG) · debugging applied mixins and bisecting giant
packs honestly · the probe methodology that killed a beautiful, wrong hypothesis
before it cost weeks · shipping: version policy and the release checklist.

**Plus four appendices:** @At/descriptor cheat sheets, MixinExtras quick reference,
the printable Compat Checklist, and javap/CFR recipes.

12 chapters · 4 appendices · every code excerpt from working, shipped mods.

**Who it's for:** you can write an @Inject, and you've lost at least one evening to a
mixin conflict, a refmap mystery, or "works in dev." This book is those evenings,
refunded.

**Who it's not for:** complete beginners (learn basic mixins first — free tutorials
cover that), and Fabric-only devs (concepts transfer; the build-pipeline chapter and
examples are Forge/NeoForge).

*Read Chapter 1 free (link) — if the collision chapter doesn't teach you something,
don't buy the book.*

---

## Tags
minecraft, modding, forge, neoforge, mixin, java, minecraft mods, game development, programming ebook

## FAQ block
- **Format?** PDF (print-ready), plus the Markdown source of every chapter.
- **When?** Presale buyers receive the PDF on [DATE] via Gumroad — nothing to do.
- **Updates?** First-edition revisions free, delivered through Gumroad.
- **Refunds?** 14 days, no questions.
- **Fabric?** ~70% transfers (application model, MixinExtras, probes); build chapter is Forge-specific. If that ratio bugs you, don't buy.

## Presale launch checklist
1. Export sample HTML → PDF (Ctrl+P), upload as the free product; enable email collection.
2. Create presale product at $29 with the ship date **in the first line** of the description.
3. Author review pass on all 12 chapters (voice + facts) before [DATE].
4. Verify pass: Ch.1's injection-refusal mechanic vs Mixin source; Ch.5/6/11 excerpts vs the VP repo.
5. Announce: r/feedthebeast dev thread + NeoForge/Forge Discords (ask mods first;
   value-first: lead with the free chapter) + a "what I learned shipping VS×IP compat"
   post that *is* Chapter 1's story, linking the free sample.
6. Email RepoForge buyers + Lite list: one message, free chapter attached, presale mentioned once.
