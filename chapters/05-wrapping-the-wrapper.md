# Chapter 5 — Wrapping the Wrapper
### Composing over another mod's @WrapOperation, and measuring what you can't assume

This is a Type B collision (Chapter 4's taxonomy): two mods transforming the same call
toward *different* goals, where neither can simply yield. It's also the chapter where
compat work stops being about mixin mechanics and starts being about **the domain** —
because the mixin part of this fix is four lines, and the correctness part is a small
theorem about camera matrices.

**Symptom:** with Valkyrien Skies and Immersive Portals installed, portals render fine
— until the player rides a VS ship. Then every portal pane goes blank, showing nothing
instead of the other side.

---

## 5.1 Diagnosis: a wrap that fires in a context its author never imagined

VS wraps the `LevelRenderer.prepareCullFrustum(...)` call inside
`GameRenderer.renderLevel` with a `@WrapOperation` (priority 1000, the default). Its
job: when the player is mounted on a ship, replace the render camera with a
ship-relative one — repositioned to the ship's world-space eye, pose banked with the
ship's roll. Perfectly correct for the main render pass.

But Immersive Portals renders the view *through* a portal by issuing **nested
`renderLevel` passes** with its own carefully-placed remote camera. And VS's wrap
fires on *every* `renderLevel` — including the nested ones. Mid-portal-pass, IP
positions the camera at the far side of the portal; VS's wrap immediately clobbers it
back to the ship position. The portal pane draws a view from the wrong place: blank.

Note the shape of this bug, because you will meet it wearing other costumes: **a
correct patch, keyed on global state ("is the player on a ship?"), firing inside a
nested context its author didn't know existed.** IP's nested passes, dimension-preview
mods, shadow-map passes, entity-in-GUI renders — renderers are full of nested contexts,
and mixins keyed on "the" camera or "the" pass silently assume there's only one.

## 5.2 The composition: priority 2000, and the right to decide

Both mods are right: VS *must* reposition the main camera; IP *must* own the nested
camera. Nobody yields — so somebody has to *sequence*. The shipped fix wraps the same
call at priority 2000, which in MixinExtras' chaining model makes it the **outer**
wrapper: it runs first, and VS's wrap only runs if the outer wrap calls `original`:

```java
@Mixin(value = GameRenderer.class, priority = 2000)
public abstract class MixinGameRendererPortalCamera {

    @WrapOperation(method = "renderLevel", at = @At(value = "INVOKE",
        target = "Lnet/minecraft/client/renderer/LevelRenderer;prepareCullFrustum("
            + "Lcom/mojang/blaze3d/vertex/PoseStack;Lnet/minecraft/world/phys/Vec3;"
            + "Lorg/joml/Matrix4f;)V"))
    private void vp$bypassShipCameraInPortalPass(LevelRenderer levelRenderer,
            PoseStack poseStack, Vec3 cameraPos, Matrix4f projection,
            Operation<Void> original) {
        if (PortalRendering.isRendering()) {
            // Nested pass: IP's camera stands; skip VS entirely, call vanilla direct.
            ((LevelRendererPrepareCullFrustumInvoker) levelRenderer)
                .vp$invokePrepareCullFrustum(poseStack, cameraPos, projection);
        } else {
            original.call(levelRenderer, poseStack, cameraPos, projection); // VS runs
        }
    }
}
```

Three deliberate choices:

**The discriminator is IP's own API** — `PortalRendering.isRendering()` — not a
re-derivation ("is this camera far from the player?" heuristics age like milk). The
mod that creates the context is the authority on whether you're in it.

**Skipping VS means calling vanilla explicitly.** You can't just *not* call
`original` — the frustum still needs preparing. But `prepareCullFrustum` is private
vanilla API, so the mod ships an `@Invoker` (Chapter 8) to reach it:
`LevelRendererPrepareCullFrustumInvoker.vp$invokePrepareCullFrustum(...)`. Outer wraps
that bypass inner wraps must be able to reproduce the *un-wrapped* behavior; budget
for the accessor.

**Priority 2000 is a claim of jurisdiction, stated in the javadoc.** "We decide
whether VS's camera logic applies, per pass." If some third mod someday needs to
decide about *our* decision, they go to 3000, and the chain keeps composing. That's
the entire virtue of wraps over redirects (Chapter 2): disagreement becomes nesting.

## 5.3 The part you can't guess: the ship-bank matrix

Shipping the bypass alone produced a subtler bug: on a *tilted* ship, the portal pane
was no longer blank — but the view through it was rolled relative to the portal frame.
Reason: VS banks the **main** view with the ship's roll, and the portal *frame* is
drawn in that banked main pass. The nested *content* pass (bypassed past VS) has a
fresh, unbanked camera. Frame and content disagree by exactly the ship's bank.

The tempting fix is to recompute the ship's roll from VS's transform data and apply
it. The shipped fix is better, and it's the methodological heart of this chapter:
**measure the bank instead of re-deriving it.** VS's bank, whatever it is, acts as a
screen-space operator `B` on the pose: `MAIN = B · L`, where `L` is the look-only pose
that exists *before* VS's wrap runs. Both `MAIN` and `L` pass through our wrapper
every frame — so `B` is observable:

```java
// Main pass: capture the pre-VS look pose, let VS bank it, derive B = MAIN · L⁻¹.
Matrix4f lookPose = new Matrix4f(poseStack.last().pose());
original.call(levelRenderer, poseStack, cameraPos, projection);
vp$shipBank.set(poseStack.last().pose()).mul(lookPose.invert());
```

```java
// Nested pass: left-multiply IP's camera by the measured bank, then vanilla frustum prep.
pose.pose().mulLocal(vp$shipBank);
pose.normal().mulLocal(vp$shipBankNormal);
```

Properties that make this *exact* rather than approximate: it's measured fresh every
frame from whatever VS actually did (no assumptions about VS's math, no version
coupling to VS's internals); it collapses to the identity matrix whenever VS doesn't
bank — so unmounted players, level ships, and vanilla riders pay nothing; and the
main pass always precedes the nested passes within a frame, so `B` is always current
when consumed.

**Self-calibration beats re-derivation** whenever another mod's transformation passes
through your hands: capture input, capture output, apply the measured difference where
you need it. You inherit their correctness for free, including future versions of it.

## 5.4 The supporting cast

Real fixes are ensembles. The blank-pane fix exposed two more nested-context bugs,
each dispatched with Chapter 2's smallest-tool rule:

- **Fog occlusion:** Embeddium computes its fog-culling distance from the *host*
  pass's shader fog, truncating through-portal terrain. One `@ModifyExpressionValue`
  on `getShaderFogEnd()` returning `Float.MAX_VALUE` when `PortalRendering.isRendering()`
  (full code in Chapter 2). Note it's the same discriminator again — one authority,
  used everywhere.
- **Frustum prep access:** the `@Invoker` above — infrastructure, not logic.

One condition, three surgical patches, no overwrites, everything chainable. That's
what Type B resolution looks like when it goes well.

## 5.5 Doctrine

1. **Nested contexts are where correct mixins go feral.** Any patch keyed on global
   state must ask: what happens when my target runs *inside* someone else's pass?
2. **Sequence with wrap priority; state the jurisdiction in prose.** Outer decides
   about inner. Write the sentence in the javadoc next to the number.
3. **Use the context-owner's own API as the discriminator.** Heuristic re-detection
   of someone else's state is a slow-motion version break.
4. **Bypassing an inner wrap means reproducing unwrapped behavior** — ship the
   invoker/accessor to reach the vanilla path explicitly.
5. **Measure other mods' transformations instead of re-deriving them.** B = MAIN·L⁻¹
   cost two matrix ops per frame and zero coupling to VS's math. The re-derivation
   would have cost correctness on the next VS update.

Next: what to do when the thing you must patch has no name — synthetic lambdas and
deliberately obfuscated internals.
