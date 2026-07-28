# Chapter 2 — The Injection Toolbox
### Six ways to touch a method, ranked by blast radius

Every mixin tutorial ranks the injectors by *power*: what each one lets you change.
This chapter ranks them by the only metric that matters once your mod leaves your dev
environment: **how well each tool coexists with strangers.** Because after Chapter 1
you know the truth — your mixin never patches vanilla. It patches vanilla *as already
transformed by every other mod in the pack*, and other mods' mixins land on yours.

The ranking, best neighbor to worst:

| Tool | What it does | Coexistence | Use when |
|------|--------------|-------------|----------|
| `@Inject` | Adds a callback at a point | Excellent (additive) — until you `cancel` | Observing, adding behavior, early-exit guards |
| `@ModifyExpressionValue` / `@ModifyReturnValue` / `@ModifyArg` | Edits one value in flight | Excellent (chainable) | Changing a single value, keeping all logic |
| `@WrapOperation` / `@WrapMethod` | Wraps a call/method, may skip it | Very good (chains by priority) | Conditional bypass, composing over other mods |
| `@Redirect` | Replaces one call instruction | **Poor — exclusive claim** | Legacy code; almost never in new compat work |
| `@Overwrite` | Replaces the whole method | **Total — last mixin standing** | Method is unsalvageable; you accept ownership |

The rest of the chapter is each row with real shipped code, its failure mode with
strangers, and the judgment call.

---

## 2.1 `@Inject` — the good neighbor with one bad habit

An inject adds a callback; it removes nothing. Two mods injecting at `HEAD` of the same
method both run. Ten mods, all ten run. This is why `@Inject` should be your default:
it's the only injector that's additive *by construction*.

Real example, from Valkyrien Portals — VS's entity-dragging system was dragging
Immersive Portals' portal *entities* along with ships, ripping portals off their frames:

```java
@Mixin(value = EntityDragger.class, remap = false)
public abstract class MixinEntityDragger {

    @Inject(method = "isDraggable", at = @At("HEAD"), cancellable = true, require = 0)
    private static void vp$immersivePortalsAreNotShipDraggable(Entity entity,
                                                              CallbackInfoReturnable<Boolean> cir) {
        if (entity instanceof Portal) {
            cir.setReturnValue(false);
        }
    }
}
```

Note what made this the *right* tool: VS deliberately exposes `isDraggable` as an
extension point ("ships and entities marked non-draggable return false"). We're
answering a question the API asked. Root cause, not band-aid.

**The bad habit: `cancellable = true`.** The moment your HEAD inject calls
`cir.setReturnValue(...)` or `ci.cancel()`, you've skipped the *entire remaining
method body* — including every other mod's `TAIL` injections into it and vanilla logic
they assumed would run. A cancellable HEAD inject that fires often is an `@Overwrite`
wearing a friendly costume. Rules of thumb:

- Cancel on a **narrow predicate** (as above: only for `Portal` entities), never
  unconditionally.
- Prefer cancelling methods that return a *decision* (booleans, nullables) over
  methods that perform *work* — skipping a decision is composable; skipping work
  breaks whoever queued behind it.

## 2.2 The value modifiers — surgical, chainable, underused

MixinExtras' `@ModifyExpressionValue` edits exactly one value where it's produced,
leaving every instruction in place. Multiple mods modifying the same expression
*chain* — each receives the previous mod's output. It is nearly impossible to conflict
with.

Real example — Embeddium collapses its fog-occlusion distance from the host pass's fog
during Immersive Portals' nested renders, truncating the through-portal view:

```java
@ModifyExpressionValue(
    method = "getEffectiveRenderDistance",
    at = @At(value = "INVOKE",
             target = "Lcom/mojang/blaze3d/systems/RenderSystem;getShaderFogEnd()F")
)
private float vp$ignoreFogOcclusionInPortalPass(float fogEnd) {
    return PortalRendering.isRendering() ? Float.MAX_VALUE : fogEnd;
}
```

One float, conditionally replaced. Nothing else about the method changes; another
mod's patch to the same method never notices we exist. When your change is "this one
value should be different under this one condition," this family is *always* the
answer — reach for it before you reach for anything heavier.

## 2.3 `@WrapOperation` / `@WrapMethod` — composition as a first-class citizen

A wrap intercepts a call (or a whole method) and receives an `original` handle. You
can call it, skip it, or transform around it. The compat magic is in the chaining:
**when several mixins wrap the same target, they nest** — the higher-priority mixin's
wrap is outermost, and its `original.call(...)` descends into the next wrap down,
bottoming out at the real code.

That nesting is not a footnote; it's a *strategy*. Valkyrien Skies wraps
`prepareCullFrustum` to swap in a ship-relative camera. That wrap also fires during
IP's nested portal passes and blanks the portal pane. The shipped fix wraps *the same
call* at priority 2000 — outside VS's 1000 — and simply declines to invoke VS's wrap
mid-portal-render:

```java
@Mixin(value = GameRenderer.class, priority = 2000)
public abstract class MixinGameRendererPortalCamera {

    @WrapOperation(method = "renderLevel", at = @At(value = "INVOKE",
        target = "Lnet/minecraft/client/renderer/LevelRenderer;prepareCullFrustum(...)V"))
    private void vp$bypassShipCameraInPortalPass(LevelRenderer levelRenderer, ...,
                                                 Operation<Void> original) {
        if (PortalRendering.isRendering()) {
            // invoke vanilla directly — VS's wrap (our 'original') is skipped
            ((LevelRendererPrepareCullFrustumInvoker) levelRenderer)
                .vp$invokePrepareCullFrustum(poseStack, cameraPos, projection);
        } else {
            original.call(levelRenderer, poseStack, cameraPos, projection);  // VS runs
        }
    }
}
```

Read the priority as a sentence: *"I want to make decisions about VS's decision."*
Outer wraps decide whether inner wraps happen. If you instead need your logic to run
closest to the metal — inside everyone else's interception — you want *lower* priority.
Chapter 5 dissects this example in full (including the self-calibrating matrix trick
that makes the bypass exact); here the point is the shape: **wraps turn "we both patch
X" from a collision into a hierarchy.**

`@WrapMethod` is the same idea at whole-method granularity — Chapter 6 uses it to
guard a Kotlin synthetic lambda. And one more MixinExtras kindness: a `@WrapOperation`
can wrap a call that *another* mod has `@Redirect`ed — the redirect is treated as the
original. Your wrap survives their legacy code.

## 2.4 `@Redirect` — the exclusive claim

A redirect *replaces* a call instruction. Not "adds a hook" — replaces. And a replaced
instruction can only be replaced once: the second mod's redirect on the same target is
a merge conflict, which in `require = 1` hands becomes a boot crash, and in `require = 0`
hands becomes a silently missing feature. Either way, exactly one mod wins and neither
agreed to the duel.

Redirects are all over important mods for one reason: they predate MixinExtras. Here's
one in the wild — Valkyrien Skies redirecting `PoseStack.translate` inside Embeddium's
block-entity renderer, to re-position ship block entities from shipyard coordinates to
world space:

```java
@Redirect(method = "renderBlockEntity",
    at = @At(value = "INVOKE", target = "Lcom/mojang/blaze3d/vertex/PoseStack;translate(DDD)V"))
private static void renderShipBlockEntityInShipyard(PoseStack instance, double x, ...) {
    ClientShip ship = VSGameUtilsKt.getLoadedShipManagingPos(level, pos);
    if (ship == null) {
        instance.translate(x, y, z);            // faithful original
    } else {
        VSClientGameUtils.transformRenderWithShip(...);  // ship-space transform
    }
}
```

It works. It also means *no other mod can redirect that translate call, ever*, in any
pack containing VS. When you find yourself writing `@Redirect` in new code, stop and
check: `@WrapOperation` can do everything a redirect can (call-site replacement with
access to args and receiver) *while remaining chainable*. In new compat work the
honest uses of `@Redirect` round to zero. Write wraps; leave redirects to history.

## 2.5 `@Overwrite` — honest totality

An overwrite replaces the entire method and makes you its owner. Every other mixin
that targeted the old body now targets yours — or fails against it (Chapter 1 was
exactly this: IP's overwrite versus VS's inject).

It is not always wrong. IP's frustum overwrite was *correct*: the vanilla method was
unsalvageable for its use case, the replacement needed isometric branches no injection
point could express, and IP accepted ownership — including the obligation to keep the
method semantically compatible for everyone downstream. That's the deal you sign:

- Document it (`@author` and `@reason` aren't decoration — strict mixin checks can
  demand them, and future archaeologists definitely will).
- Keep every observable behavior of the original unless breaking it is the point.
- Accept that you are now load-bearing infrastructure for mods you've never heard of.

If that paragraph made you tired, good — the tiredness is the design signal. Almost
everything you'd overwrite for can be expressed as a wrap plus value modifiers.

## 2.6 `@Local` — capturing context without capturing liability

MixinExtras' `@Local` grabs a local variable or argument from the target method by
type, sparing you the brittle `LocalCapture` ordinal dance. It's how the shipped
vs-core tracker mixin gets the ship being processed inside an obfuscated method:

```java
private static String vp$portalVisibleDimension(VsiPlayer player, Operation<String> original,
                                                @Local(argsOnly = true) ServerShipInternal ship) {
```

One discipline note: capture by unique type (`argsOnly = true` narrows to parameters).
The moment you need ordinals to disambiguate two locals of the same type, you've bound
yourself to the compiler's whims — pin the target version and test that assumption
(Chapter 6 covers version-pinning etiquette).

## 2.7 Doctrine

1. **Reach for the smallest tool that expresses the change**: value modifier → inject
   → wrap → (never) redirect → (rarely, with ownership) overwrite.
2. **Additive beats exclusive.** Injects and modifiers stack with strangers by
   construction; redirects and overwrites make you the only tenant.
3. **A cancellable HEAD inject is an overwrite with better manners** — cancel on
   narrow predicates, prefer cancelling decisions over work.
4. **Wraps convert collisions into hierarchies.** Priority states *whose judgment
   nests outside whose* — say it as a sentence before you pick the number.
5. **New `@Redirect`s need a written justification** for why a wrap can't do it.
   You will almost never finish that sentence.

Next: none of this matters if your selectors don't survive the trip from your dev
environment to a real pack. Chapter 9 is about the build pipeline — where mixins that
work on your machine go to die.
