using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// Element skill: cast → charge in the palm → flight (or instant link) → impact → linger. All parameters come from ElementProfile.
    /// · Each Play() is an independent shot: rapid casts don't interrupt the previous shot, which still lands.
    /// · The landing point follows a moving target; if the target disappears mid-flight, the shot flies to its last known position.
    /// · Trails are emitted by distance travelled, so density is frame-rate independent.
    /// · Hits are reported to the target through IElementHitReceiver (with element info, for elemental reactions).
    /// · When the component is disabled / destroyed (caster dies): all in-flight orbs and shells are reclaimed immediately, IsPlaying drops to zero and Finished fires.
    /// Element differences follow effekseer-vfx craft §3/§4: at least three of shape, motion, rhythm, material and secondary motion differ.
    /// The motion of each style (Trail / Impact / Linger) lives here; a new element only needs a new ElementProfile that picks styles.
    /// </summary>
    public class ElementSkill : SkillBase
    {
        public ElementProfile profile;
        public CastDriver caster;
        [Tooltip("Target radius: the hit point is on the target surface facing the caster")] public float targetRadius = 0.45f;

        int active;
        readonly List<ShellPiece> held = new List<ShellPiece>();   // pooled shells borrowed by this component (all returned on disable)
        /// <summary>Fires when any element skill hits (review tools use it to log hit frames).</summary>
        public static event System.Action<ElementSkill> AnyHit;
        ElementProfile P => profile;

        public override void Play()
        {
            if (!profile) { Debug.LogError($"[ElementSkill] {name}: no ElementProfile assigned", this); return; }
            string missing = profile.Validate();
            if (missing.Length > 0) Debug.LogError($"[ElementSkill] {profile.name}: missing {missing}", this);
            StartCoroutine(Cast(target));
        }

        protected override IEnumerator Run() { yield break; }   // the base class's single-shot flow is not used

        protected override void OnDisable()
        {
            base.OnDisable();
            StopAllCoroutines();                                   // Unity doesn't stop coroutines on enabled=false: otherwise flight / crown coroutines would keep modifying shells already returned (and possibly borrowed by someone else)
            foreach (var s in held) if (s) s.Release();
            held.Clear();
            if (active > 0) { active = 0; RaiseFinished(); }
        }

        ShellPiece Take(Material m) { var s = ElementFX.Shell(m); held.Add(s); return s; }
        void Give(ShellPiece s) { if (!s) return; s.Release(); held.Remove(s); }

        Vector3 Hand => caster ? caster.HandPosition : HandPos;

        /// <summary>Hit point on the target: the surface facing the caster (the top when fromAbove), with per-element height from aimHeight.</summary>
        Vector3 Surface(Transform tgt, Vector3 lastKnown, Vector3 from)
        {
            Vector3 c = (tgt ? tgt.position + targetOffset : lastKnown) + Vector3.up * P.aimHeight;
            if (P.fromAbove) return c + Vector3.up * targetRadius * 0.9f + Vector3.ProjectOnPlane(from - c, Vector3.up).normalized * targetRadius * 0.4f;
            Vector3 toFrom = Vector3.ProjectOnPlane(from - c, Vector3.up);
            return c + (toFrom.sqrMagnitude > 1e-4f ? toFrom.normalized * targetRadius : Vector3.zero);
        }

        Vector3 Center(Transform tgt, Vector3 lastKnown) => tgt ? tgt.position + targetOffset : lastKnown;

        IEnumerator Cast(Transform tgt)
        {
            active++; IsPlaying = true;
            Vector3 lastKnown = tgt ? tgt.position + targetOffset : transform.TransformPoint(fallbackTarget);
            int stamp = caster ? caster.ReleaseStamp : 0;
            float charge = caster ? caster.Cast(P.castSpeed) : 0.4f;
            var pieces = new List<Object>();

            IEnumerator body = P.delivery == DeliveryType.Instant ? Lightning(tgt, lastKnown, charge, stamp, pieces)
                             : P.delivery == DeliveryType.Eruption ? Eruption(tgt, lastKnown, charge, stamp, pieces)
                             : Projectile(tgt, lastKnown, charge, stamp, pieces);
            yield return body;

            foreach (var o in pieces) if (o) { spawned.Remove(o); Destroy(o); }
            if (active > 0 && --active == 0) { IsPlaying = false; RaiseFinished(); }
        }

        /// <summary>Whether charging is done: Animator waits for the Release animation event (with a timeout fallback), Legacy goes by time.</summary>
        bool ChargeDone(float t, float charge, int stamp)
        {
            if (caster && caster.UsesReleaseEvent)
            {
                if (caster.ReleasedSince(stamp)) return true;
                if (t > charge + 1f) { Debug.LogWarning($"[ElementSkill] {caster.name}: Animator cast has no \"Release\" animation event — released by timeout (1 s late). Add the event to the cast clip.", caster); return true; }
                return false;
            }
            return t >= charge;
        }

        // ───────────────────────── Charge ─────────────────────────
        /// <summary>A small orb grows in the palm while secondary matter converges on the hand, until the cast animation releases.</summary>
        IEnumerator Charge(Transform orb, float charge, int stamp)
        {
            float t = 0;
            while (!ChargeDone(t, charge, stamp))
            {
                float k = Mathf.Clamp01(t / charge);
                orb.position = Hand;
                orb.localScale = Vector3.one * P.chargeSize * EaseOutBack(Mathf.Clamp01(k * 1.3f), 2.2f);
                ElementFX.Face(orb, P.spinDegPerSec * 0.5f * t);
                for (int i = ElementFX.Rate(28 * (1 - k * 0.6f), Time.deltaTime); i > 0; i--)
                {
                    Vector3 p = Hand + Random.onUnitSphere * Random.Range(0.3f, 0.5f);
                    ElementFX.Spark(p, (Hand - p) / 0.18f, Random.Range(0.04f, 0.07f), 0.18f, P.theme);
                }
                t += Time.deltaTime; yield return null;
            }
        }

        // ───────────────────────── Projectile ─────────────────────────
        IEnumerator Projectile(Transform tgt, Vector3 lastKnown, float charge, int stamp, List<Object> pieces)
        {
            var orb = ElementFX.Quad("Orb_" + P.displayName, P.orb, null);   // world space: a scaled caster rig must not scale the orb
            pieces.Add(orb.gameObject); spawned.Add(orb.gameObject);
            orb.localScale = Vector3.zero;

            // 1) Charge
            yield return Charge(orb, charge, stamp);

            // 2) Flight: analytic trajectory + tracking target movement
            Vector3 hand = Hand;
            Vector3 aim0 = Surface(tgt, lastKnown, hand);
            float dist = Vector3.Distance(hand, aim0);
            float T = Mathf.Max(0.08f, dist / Mathf.Max(0.5f, P.speed));      // runtime clamp: even speed = 0 can't fly forever
            Vector3 g = Physics.gravity * P.gravityScale + Vector3.down * (P.lift > 0 ? 8f * P.lift / (T * T) : 0f);
            Vector3 v0 = (aim0 - hand) / T - 0.5f * g * T;
            ElementFX.Flash(hand, P.chargeSize * 2.2f, P.theme, 0.05f);
            float tf = 0, carry = 0, travelled = 0;
            Vector3 prev = hand, aim = aim0;
            while (true)
            {
                if (tgt) lastKnown = tgt.position + targetOffset;
                aim = Surface(tgt, lastKnown, hand);
                tf = Mathf.Min(tf + Time.deltaTime, T);
                float s = tf / T;
                Vector3 pos = hand + v0 * tf + 0.5f * g * tf * tf + (aim - aim0) * (s * s * (3 - 2 * s));
                Vector3 vel = v0 + g * tf;
                Vector3 d = vel.sqrMagnitude > 1e-6f ? vel.normalized : (aim - hand).normalized;
                float seg = Vector3.Distance(prev, pos);
                carry += seg;
                float spacing = Mathf.Max(0.01f, P.trailSpacing);
                int emits = 0;
                while (carry >= spacing && emits++ < 64)                         // trail: fill in by distance (frame-rate independent); at most 64 per frame so a tiny spacing can't hang
                {
                    carry -= spacing;
                    float back = seg > 1e-5f ? carry / seg : 0;
                    EmitTrail(Vector3.Lerp(pos, prev, Mathf.Clamp01(back)), vel, d, travelled + seg - carry);
                }
                if (carry >= spacing) carry %= spacing;
                travelled += seg; prev = pos;
                if (tf >= T) break;                                            // the contact frame is handled by the impact (orb, flash and body switch on the same frame)
                orb.position = pos;
                float flick = P.trail == TrailStyle.EmberSmoke ? 1 + 0.12f * Mathf.Sin(tf * 60) + 0.06f * Mathf.Sin(tf * 137) : 1 + 0.04f * Mathf.Sin(tf * 30);
                orb.localScale = Vector3.one * P.flightSize * flick;
                ElementFX.Face(orb, P.spinDegPerSec * tf);
                yield return null;
            }

            // 3) Impact
            orb.gameObject.SetActive(false);
            if (P.cutTrailOnHit) ElementFX.CutTrail(P.orb, 0.04f);              // orb is gone: cut the trail within 1 frame (only for elements with the toggle on)
            Vector3 hitDir = (v0 + g * T).normalized;
            float hitTime = Time.time;
            Hit(tgt, lastKnown, aim, hitDir);
            yield return Linger(tgt, lastKnown, aim, hitDir);
            while (Time.time - hitTime < P.decalLife) yield return null;   // the skill finishes only after the ground mark has fully faded
        }

        void EmitTrail(Vector3 p, Vector3 vel, Vector3 d, float travelled)
        {
            switch (P.trail)
            {
                case TrailStyle.Droplets:   // water: droplets fling off carrying some of the velocity and fall under gravity
                    ElementFX.Drop(p + Random.insideUnitSphere * 0.08f, vel * Random.Range(0.1f, 0.25f) + Random.insideUnitSphere * 0.5f + Vector3.down * 0.5f,
                                   Random.Range(0.05f, 0.09f), Random.Range(0.45f, 0.7f), Color.Lerp(P.theme, Color.white, 0.3f), P.matter);
                    break;
                case TrailStyle.EmberSmoke: // fire: embers drift up + flame afterimages (no smoke in flight: small puffs read as grey rubble at a distance)
                    ElementFX.Spark(p + Random.insideUnitSphere * 0.08f, Vector3.up * Random.Range(1.0f, 2.2f) + Random.insideUnitSphere * 0.5f,
                                    Random.Range(0.04f, 0.08f), Random.Range(0.35f, 0.6f), Color.Lerp(P.theme, new Color(1, 0.9f, 0.5f), 0.4f));
                    ElementFX.TrailPuff(P.orb, p, P.flightSize * Random.Range(0.45f, 0.65f), 0.12f);
                    break;
                case TrailStyle.ToxicDrip:  // poison: drips fall one by one + an occasional small bubble (no smoke: reads as soot from afar)
                    ElementFX.TrailPuff(P.orb, p, P.flightSize * Random.Range(0.45f, 0.6f), 0.14f);   // afterimages of the poison orb join into a continuous stream (not scattered dots)
                    if (Random.value < 0.35f)
                        ElementFX.Drop(p + Random.insideUnitSphere * 0.06f, vel * 0.05f + Vector3.down * 0.6f, Random.Range(0.06f, 0.1f), 0.7f, P.theme, P.matter);
                    if (Random.value < 0.15f)
                        ElementFX.Bubble(p + Random.insideUnitSphere * 0.1f, Vector3.up * 0.3f, Random.Range(0.07f, 0.11f), 0.5f, Color.Lerp(P.theme, Color.white, 0.3f), P.matter);
                    break;
                case TrailStyle.Helix:      // wind: sheared airflow dashes (most velocity flung backward, stretched into dashes along the path), a few spiralling around the axis
                {
                    Vector3 side = Vector3.Cross(d, Vector3.up).normalized, up = Vector3.Cross(side, d);
                    float a = travelled * 9f + (Random.value < 0.5f ? 0 : Mathf.PI);
                    Vector3 r = side * Mathf.Cos(a) + up * Mathf.Sin(a);
                    ElementFX.Streak(p + r * Random.Range(0.12f, 0.28f), -d * Random.Range(5f, 8f) + Vector3.Cross(d, r) * 1.5f, 0.05f, 0.12f, Color.Lerp(P.theme, Color.white, 0.25f));
                    if (Random.value < 0.3f) ElementFX.TrailPuff(P.orb, p, P.flightSize * 0.45f, 0.1f);
                    break;
                }
            }
        }

        // ───────────────────────── Impact ─────────────────────────
        void Notify(Transform tgt, Vector3 p, Vector3 dir, float power)
        {
            if (!tgt) return;
            var hit = new ElementHit { element = P, point = p, direction = dir, power = power, source = this };
            foreach (var r in tgt.GetComponentsInParent<IElementHitReceiver>()) r.OnElementHit(hit);
        }

        /// <summary>
        /// Contact burst (the 'brightest 2–3 frames'): every element gets a small white-hot core + directional sparks + a short-range point light at the target's centre,
        /// plus the element-specific contact accent (profile.contact). tick = damage tick: only a small core + small star + a few sparks.
        /// </summary>
        void Burst(Vector3 p, Vector3 dir, float power, Vector3 center, bool tick = false)
        {
            var cam = Camera.main;
            Vector3 toCam = cam ? (cam.transform.position - p).normalized : -dir;
            Vector3 front = p + toCam * 0.3f;
            ElementFX.Flash(front, P.flashSize * 0.5f * Mathf.Lerp(0.6f, 1f, power), Color.white, 0.06f);
            // white-hot core: additive white is invisible on a white target, so the core is a small cel star (white core + element colour + matching dark rim), lit for only 2 frames
            ElementFX.Shape(P.star, front, P.flashSize * (tick ? 0.5f : 1.0f), 0.08f);
            ElementFX.LightFlash(center, P.theme, P.lightIntensity * power, P.lightRange, tick ? 0.08f : 0.12f);
            Vector3 fwd = Vector3.ProjectOnPlane(dir, Vector3.up).normalized;
            Color hot = Color.Lerp(P.theme, Color.white, 0.25f);
            int n = ElementFX.Count(Mathf.RoundToInt(P.sparkCount * (tick ? 0.35f : power)));
            for (int i = 0; i < n; i++)          // directional spray along the hit direction (not a symmetric sphere), fast then slowing
            {
                Vector3 sd = (fwd * Random.Range(-0.3f, 0.5f) + Random.insideUnitSphere * 0.9f + Vector3.up * Random.Range(0.1f, 0.5f)).normalized;
                ElementFX.Streak(p, sd * Random.Range(6f, 11f), Random.Range(0.05f, 0.08f), Random.Range(0.14f, 0.24f), hot);
                ElementFX.Spark(p, sd * Random.Range(3f, 7f), Random.Range(0.06f, 0.11f), Random.Range(0.3f, 0.5f), P.theme);
            }
            if (tick) return;
            switch (P.contact)
            {
                case ContactAccent.Star: break;                                                          // core star only
                case ContactAccent.FoamRing: StartCoroutine(PlaneRing(front, Vector3.Slerp(-fwd, toCam, 0.6f).normalized, 0.3f, 1.6f, 0.16f, true)); break;   // opens toward the camera so it reads as a ring
                case ContactAccent.AirRing:
                    StartCoroutine(PlaneRing(p, Vector3.Slerp(Vector3.up, toCam, 0.45f).normalized, 0.6f, 2.6f, 0.2f, false));
                    for (int i = 0, m = ElementFX.Count(12); i < m; i++)                                  // airflow lines flung sideways + dust
                    {
                        Vector3 sd = Vector3.ProjectOnPlane(Random.onUnitSphere, Vector3.up).normalized;
                        ElementFX.Streak(p, sd * Random.Range(7f, 11f), 0.06f, 0.25f, Color.Lerp(P.theme, Color.white, 0.4f));
                        ElementFX.Smoke(ElementFX.GroundAt(p) + sd * 0.3f + Vector3.up * 0.1f, sd * Random.Range(1.5f, 2.5f) + Vector3.up * 0.3f, Random.Range(0.35f, 0.5f), 0.6f, new Color(0.78f, 0.74f, 0.64f, 0.35f), P.smoke);
                    }
                    break;
                case ContactAccent.ArcBurst: StartCoroutine(ArcBurst(p, toCam)); break;
            }
        }

        static Mesh ringQuad;
        static Mesh RingQuad()
        {
            if (ringQuad) return ringQuad;
            ringQuad = new Mesh { name = "RingQuad" };
            ringQuad.vertices = new[] { new Vector3(-0.5f, 0, -0.5f), new Vector3(0.5f, 0, -0.5f), new Vector3(-0.5f, 0, 0.5f), new Vector3(0.5f, 0, 0.5f) };
            ringQuad.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 1), new Vector2(1, 1) };
            ringQuad.uv2 = new[] { Vector2.one * 0.5f, Vector2.one * 0.5f, Vector2.one * 0.5f, Vector2.one * 0.5f };
            ringQuad.colors = new[] { Color.white, Color.white, Color.white, Color.white };
            ringQuad.normals = new[] { Vector3.up, Vector3.up, Vector3.up, Vector3.up };
            ringQuad.triangles = new[] { 0, 2, 1, 1, 2, 3 };
            ringQuad.RecalculateBounds();
            return ringQuad;
        }

        // ring opening in the plane defined by normal (water: foam ring along the hit surface that breaks into droplets; wind: horizontal pressure ring around the body)
        IEnumerator PlaneRing(Vector3 p, Vector3 normal, float from, float to, float life, bool tearIntoDrops)
        {
            var r = Take(P.ring); r.CopyMesh(RingQuad());
            r.transform.position = p; r.transform.rotation = Quaternion.FromToRotation(Vector3.up, normal) * Quaternion.Euler(0, Random.Range(0, 360f), 0);
            float t = 0; bool torn = false;
            while (t < life && r)
            {
                float k = t / life;
                r.transform.localScale = Vector3.one * Mathf.Lerp(from, to, EaseOutCubic(k));
                r.Set(Mathf.Clamp01((k - 0.35f) / 0.65f), 1f);
                if (tearIntoDrops && !torn && k > 0.6f)
                {
                    torn = true;
                    for (int i = 0, n = ElementFX.Count(16); i < n; i++)
                    {
                        float ang = Random.Range(0, Mathf.PI * 2);
                        Vector3 o = r.transform.rotation * new Vector3(Mathf.Cos(ang), 0, Mathf.Sin(ang)) * to * 0.4f;
                        ElementFX.Drop(p + o, o.normalized * Random.Range(1.5f, 2.5f) + Vector3.down * 0.3f, Random.Range(0.05f, 0.09f), 0.5f, Color.Lerp(P.theme, Color.white, 0.4f), P.matter);
                    }
                }
                t += Time.deltaTime; yield return null;
            }
            Give(r);
        }

        // lightning contact: 4–5 short arcs radiating from the hit point, lit for 2 frames (not a white smoke puff)
        IEnumerator ArcBurst(Vector3 p, Vector3 toCam)
        {
            var cam = Camera.main; if (!cam) yield break;
            var arcs = new List<ShellPiece>();
            for (int i = 0; i < 4; i++) arcs.Add(Take(P.shell));
            for (int f = 0; f < 3; f++)
            {
                foreach (var a in arcs)
                {
                    if (!a) continue;
                    bool on = f < 2;
                    a.Visible = (on);
                    if (on)
                    {
                        Vector3 d = Vector3.Slerp(Random.onUnitSphere, toCam, 0.35f).normalized;
                        BoltPath.Build(a.mesh, p + toCam * 0.2f, p + toCam * 0.2f + d * Random.Range(0.4f, 0.75f), cam.transform.position, 0.07f, 1, 0.3f, 3);
                    }
                }
                yield return null;
            }
            foreach (var a in arcs) Give(a);
        }

        void Hit(Transform tgt, Vector3 lastKnown, Vector3 p, Vector3 dir)
        {
            AnyHit?.Invoke(this);
            Notify(tgt, p, dir, 1f);
            Burst(p, dir, 1f, Center(tgt, lastKnown));
            if (P.linger == LingerStyle.Drip) StartCoroutine(Streams(tgt, lastKnown, Color.Lerp(P.theme, Color.white, 0.5f), 8, 1.8f, 0.35f, P.matter, false, dir));
            // poison: no drips hanging on the face (art review: looked like a leaf stuck to the face); poisoning reads through the green flash on ticks + the bubbling pool
            Quaternion frame = Quaternion.LookRotation(Vector3.ProjectOnPlane(-dir, Vector3.up).normalized, Vector3.up);
            ElementFX.Body(P.impact, p + frame * P.impactOffset, Vector3.up * P.impactRise, P.impactSize, P.impactLife);
            switch (P.extra)
            {
                case ImpactExtra.CrownSplash: StartCoroutine(Crown(p, dir)); break;
                case ImpactExtra.Fireball: FireBurst(p); break;
                case ImpactExtra.Splat: Splat(tgt, lastKnown, p, dir); break;
                case ImpactExtra.Funnel: StartCoroutine(Funnel(tgt, p)); break;
                case ImpactExtra.Arcs: StartCoroutine(Arcs(tgt, lastKnown, 1.7f)); break;
            }
            ElementFX.GroundDecal(P.decal, Center(tgt, lastKnown), P.decalSize, P.decalLife, P.decalTint);   // ground mark directly below the target
            HitFeel.Stop(P.hitStop);
            HitFeel.Shake(P.shake, P.shakeTime);
            if (P.ticks > 0) StartCoroutine(Ticks(tgt, lastKnown, dir));
        }

        /// <param name="raise">Extra height for ticks (m): while the water column lifts the target, ticks land at the lifted position</param>
        /// <param name="splashOnly">Splash only (while held up by the column): no star, since a star on the body looks like a misplaced sticker</param>
        /// <param name="raiseUntil">raise applies only before this time (Time.time): after the lift, ticks return to ground height instead of hitting mid-air</param>
        IEnumerator Ticks(Transform tgt, Vector3 lastKnown, Vector3 dir, float raise = 0f, bool splashOnly = false, float raiseUntil = float.MaxValue)
        {
            for (int i = 0; i < P.ticks; i++)
            {
                yield return new WaitForSeconds(P.tickInterval);
                Vector3 c = Center(tgt, lastKnown) + Vector3.up * (Time.time < raiseUntil ? raise : 0f) + Random.onUnitSphere * targetRadius * 0.8f;
                Vector3 d = P.extra == ImpactExtra.Funnel ? Vector3.up : dir;
                Notify(tgt, c, d, 0.35f);
                if (splashOnly)
                    for (int k = 0, n = ElementFX.Count(8); k < n; k++)
                        ElementFX.Drop(c, Random.insideUnitSphere * 1.5f + Vector3.up * Random.Range(1f, 2f), Random.Range(0.05f, 0.08f), 0.5f, Color.Lerp(P.theme, Color.white, 0.3f), P.matter);
                else Burst(c, d, 0.45f, Center(tgt, lastKnown), true);          // tick: small core + small star + a few sparks + target flashes the element colour
            }
        }

        // water: two crown-shaped water sheets open from the hit surface toward the caster → droop under gravity → break into falling droplets
        /// <param name="droop">Sheets droop and sink under gravity (crown hitting the body); a crown from a ground eruption opens flat along the ground without drooping (otherwise it flips into a downward funnel, like the column stabbed into the ground)</param>
        /// <param name="life">Crown life (s): a landing crown must be quick (about 0.28 s), or the target looks like it is sitting in a blue bowl</param>
        IEnumerator Crown(Vector3 p, Vector3 dir, float scale = 1f, bool droop = true, float life = 0.62f)
        {
            Vector3 axis = (Vector3.ProjectOnPlane(-dir, Vector3.up).normalized * 0.75f + Vector3.up * 0.65f).normalized;
            var a = Take(P.shell); a.CopyMesh(CrownMesh());
            var b = Take(P.shell); b.CopyMesh(CrownMesh());
            float spinB = Random.Range(20f, 40f);
            float t = 0;
            bool dropped = false;
            while (t < life && a && b)
            {
                float k = t / life;
                for (int i = 0; i < 2; i++)
                {
                    var piece = i == 0 ? a : b;
                    float kk = Mathf.Clamp01((t - i * 0.05f) / life);
                    float open = EaseOutCubic(Mathf.Clamp01(kk / 0.32f));
                    Vector3 ax = droop ? Vector3.Slerp(axis, Vector3.down, kk * kk * 0.55f) : axis;   // droop under gravity
                    piece.transform.position = p + (droop ? Vector3.down * 0.4f * kk * kk : Vector3.zero);
                    piece.transform.rotation = Quaternion.FromToRotation(Vector3.up, ax) * Quaternion.Euler(0, i * spinB, 0);
                    float sc = (i == 0 ? 0.8f : 0.58f) * scale;                                  // don't cover the target's face
                    piece.transform.localScale = new Vector3(sc * (0.45f + 0.75f * open), sc * (0.25f + 0.85f * open), sc * (0.45f + 0.75f * open));
                    piece.Set(Mathf.Clamp01((kk - 0.3f) / 0.7f), 0.88f);                      // translucent (target shows through); holes open and it breaks up after 0.3
                }
                if (!dropped && k > 0.35f)                                                       // sheet breaks → a ring of droplets falls outward and down (not tossed up)
                {
                    dropped = true;
                    for (int i = 0, n = ElementFX.Count(22); i < n; i++)
                    {
                        float ang = Random.Range(0, Mathf.PI * 2);
                        Vector3 rim = Quaternion.FromToRotation(Vector3.up, axis) * new Vector3(Mathf.Cos(ang), 0.9f, Mathf.Sin(ang)) * 0.8f * scale;
                        Vector3 v = Vector3.ProjectOnPlane(rim, Vector3.up).normalized * Random.Range(1.2f, 2.4f) + Vector3.up * Random.Range(-0.5f, 0.6f);
                        ElementFX.Drop(p + rim, v, Random.Range(0.06f, 0.11f), Random.Range(0.45f, 0.65f), Color.Lerp(P.theme, Color.white, 0.25f), P.matter);
                    }
                }
                t += Time.deltaTime; yield return null;
            }
            Give(a); Give(b);
        }

        static Mesh crownMesh, ribbonA, ribbonB, ribbonC;
        static Mesh CrownMesh() => crownMesh ? crownMesh : crownMesh = MeshBuilder.Build("Crown", 48, 8, (u, v) =>
        {
            float a = u * Mathf.PI * 2;
            float r = Mathf.Lerp(0.22f, 0.8f, Mathf.Pow(v, 0.8f));                 // flared: wider toward the top
            float h = 0.9f * v * (1 - 0.18f * v);
            return new Vector3(r * Mathf.Cos(a), h, r * Mathf.Sin(a));
        }, 2f, 1f, wrapU: true);

        // fire: embers shoot up out of frame (negative gravity, bright head on top), a few fast rising fire streaks
        void FireBurst(Vector3 p)
        {
            Color ember = Color.Lerp(P.theme, new Color(1, 0.85f, 0.4f), 0.5f);
            for (int i = 0, n = ElementFX.Count(30); i < n; i++)
                ElementFX.Ember(p + Random.insideUnitSphere * 0.35f, Random.insideUnitSphere * 2.2f + Vector3.up * Random.Range(2.5f, 5f), Random.Range(0.07f, 0.13f), Random.Range(1.2f, 1.9f), ember);
            // small fireballs splashing along the ground: same cartoon atlas as the main fireball (same outline, shading, burning into curling smoke), spreading to both sides behind the target
            // (art review: soft grey smoke pushed along the ground read as a sticker and clashed with the cartoon fireball style; also keep it out of the foreground)
            Vector3 gp = ElementFX.GroundAt(p);
            Vector3 back = -LingerToCam(gp);
            for (int i = 0, n = ElementFX.Count(3); i < n; i++)
            {
                Vector3 o = Quaternion.Euler(0, Mathf.Lerp(-75f, 75f, n > 1 ? i / (n - 1f) : 0.5f) + Random.Range(-10f, 10f), 0) * back;
                ElementFX.Body(P.impact, gp + o * Random.Range(0.55f, 0.75f) + Vector3.up * 0.3f, o * 0.6f + Vector3.up * P.impactRise * 0.8f, P.impactSize * Random.Range(0.32f, 0.4f), P.impactLife * 0.7f);
            }
        }

        // poison: slams down from above → splatter (purple rim, green core) → sticky strands run down the target
        void Splat(Transform tgt, Vector3 lastKnown, Vector3 p, Vector3 dir)
        {
            for (int i = 0, n = ElementFX.Count(18); i < n; i++)
            {
                Vector3 v = Random.insideUnitSphere * 1.6f + Vector3.up * Random.Range(0.4f, 1.4f) + Vector3.ProjectOnPlane(-dir, Vector3.up).normalized * 0.6f;
                ElementFX.Drop(p + Random.insideUnitSphere * 0.2f, v, Random.Range(0.07f, 0.13f), Random.Range(0.6f, 0.9f), i % 3 == 0 ? P.dark * 1.6f : P.theme, P.matter);   // one in three is a plum-purple drop
            }
            Vector3 c = Center(tgt, lastKnown);
            var cam = Camera.main;
            Vector3 toCam = cam ? Vector3.ProjectOnPlane(cam.transform.position - c, Vector3.up).normalized : -dir;
            // the running strands are handled by Streams (3 continuous sticky strands, not short lines scattered all over the body)
        }

        // wind: three 3D airflow bands spin around the target (a funnel, narrow at the bottom and wide at the top, from the ground up over the head), then tear apart from bottom to top and dissipate
        IEnumerator Funnel(Transform tgt, Vector3 p)
        {
            Vector3 g = ElementFX.GroundAt(p);
            var ribbons = new[] { Take(P.shell), Take(P.shell), Take(P.shell) };
            ribbons[0].CopyMesh(RibbonMesh(ref ribbonA, 0f, 1.25f));
            ribbons[1].CopyMesh(RibbonMesh(ref ribbonB, 0.33f, 1.05f));
            ribbons[2].CopyMesh(RibbonMesh(ref ribbonC, 0.66f, 0.9f));
            float life = 1.3f, t = 0, ang = 0;
            while (t < life)
            {
                float k = t / life;
                if (tgt) g = ElementFX.GroundAt(tgt.position);
                ang += Mathf.Lerp(720f, 220f, k) * Time.deltaTime;                         // fast then slowing
                float grow = EaseOutBack(Mathf.Clamp01(t / 0.18f), 1.4f);
                for (int i = 0; i < 3; i++)
                {
                    var r = ribbons[i];
                    if (!r) continue;
                    r.transform.position = g;
                    r.transform.rotation = Quaternion.Euler(0, -ang * (1 + i * 0.15f) + i * 120, 0);
                    r.transform.localScale = new Vector3(grow, Mathf.Lerp(0.6f, 1f, grow), grow);
                    r.Set(Mathf.Clamp01((k - 0.35f - i * 0.04f) / 0.5f), 1f - Mathf.SmoothStep(0, 1, (k - 0.75f) / 0.2f));   // tears from the bottom up from 0.35, then fades out as a whole instead of vanishing in one frame
                }
                if (Random.value < Time.deltaTime * 14 * (1 - k))                            // dust swept up from the ground, spiralling outward
                {
                    Vector3 o = new Vector3(Random.Range(-1f, 1f), 0, Random.Range(-1f, 1f)).normalized;
                    ElementFX.Smoke(g + o * 0.5f + Vector3.up * 0.1f, Vector3.Cross(Vector3.up, o) * 2.2f + o * 0.8f + Vector3.up * 0.4f, Random.Range(0.35f, 0.5f), 0.7f, new Color(0.78f, 0.74f, 0.64f, 0.28f), P.smoke);
                }
                if (Random.value < Time.deltaTime * 24 * (1 - k))                            // swept-up leaves / debris
                    ElementFX.Spark(g + Random.insideUnitSphere * 0.9f + Vector3.up * Random.Range(0.2f, 1.8f), Vector3.Cross(Vector3.up, Random.onUnitSphere) * 5f + Vector3.up * 2f, 0.07f, 0.35f, Color.Lerp(P.theme, Color.white, 0.3f));
                t += Time.deltaTime; yield return null;
            }
            foreach (var r in ribbons) Give(r);
        }

        static Mesh RibbonMesh(ref Mesh cache, float phase, float turns)
        {
            if (cache) return cache;
            float ph = phase;
            cache = MeshBuilder.Build("WindRibbon", 96, 4, (u, v) =>
            {
                float h = 0.1f + 1.0f * u;                                                     // from the lower body to the shoulders, keeping the face clear
                float r = Mathf.Lerp(0.42f, 1.05f, Mathf.Pow(u, 1.2f));                       // narrow at the bottom, wide at the top
                float a = (u * turns + ph) * Mathf.PI * 2;
                Vector3 c = new Vector3(r * Mathf.Cos(a), h, r * Mathf.Sin(a));
                return c + Vector3.up * (v - 0.5f) * Mathf.Lerp(0.26f, 0.44f, u);             // band widens toward the top
            }, 1f, 1f, alpha: (u, v) => 1f);
            // uv: u along the band (texture U), v across; uv2.y = height parameter (the material uses it for bottom-to-top erosion)
            var uv2 = cache.uv2; for (int i = 0; i < uv2.Length; i++) uv2[i] = new Vector2(uv2[i].x, uv2[i].x); cache.uv2 = uv2;
            return cache;
        }

        // arcs: crawl over the camera-facing side of the target (3 at once, reshaped every 1–2 frames), occasionally jumping to the ground, thinning out over time (usable by any element: ImpactExtra.Arcs)
        IEnumerator Arcs(Transform tgt, Vector3 lastKnown, float dur)
        {
            var cam = Camera.main; if (!cam) yield break;
            var arcs = new List<ShellPiece>(); var glows = new List<ShellPiece>();
            for (int i = 0; i < 3; i++) { arcs.Add(Take(P.shell)); glows.Add(P.glow ? Take(P.glow) : null); }
            var ground = Take(P.shell);
            float t = 0; int frame = 0;
            while (t < dur)
            {
                float k = t / dur;
                Vector3 c = Center(tgt, lastKnown);
                Vector3 toCam = (cam.transform.position - c).normalized;
                for (int i = 0; i < arcs.Count; i++)
                {
                    if (!arcs[i]) continue;
                    if ((frame + i) % 2 != 0) continue;                                   // each arc reshapes every 2 frames, the three staggered
                    bool show = i == 0 ? Random.value < 1.3f - k * 0.6f : Random.value < 1.1f - k * (1.1f + i * 0.3f);   // thinning out, but the first arc stays until the end
                    arcs[i].Visible = show; if (glows[i]) glows[i].Visible = show;
                    if (!show) continue;
                    // both ends on the camera-facing surface of the target (never floating in the air), chord 40–90 cm, shorter over time
                    Vector3 BelowHead(Vector3 d) { d.y = Mathf.Min(d.y, -0.05f) ; return d.normalized; }   // arcs stay below eye level (keep the face clear for the hit reaction)
                    Vector3 a = c + BelowHead(Vector3.Slerp(Random.onUnitSphere, toCam, 0.6f)) * targetRadius * 1.05f, b = a;
                    for (int tries = 0; tries < 8; tries++)
                    {
                        b = c + BelowHead(Vector3.Slerp(Random.onUnitSphere, toCam, 0.6f)) * targetRadius * 1.05f;
                        float len = Vector3.Distance(a, b);
                        if (len > 0.4f * (1 - k * 0.4f) && len < 0.9f) break;
                    }
                    BoltPath.Build(arcs[i].mesh, a, b, cam.transform.position, 0.085f, 1, 0.22f, 4, glows[i] ? glows[i].mesh : null, 3.2f);
                    if (Random.value < 0.5f) for (int j = 0; j < 3; j++) ElementFX.Spark(a, Random.insideUnitSphere * 3f, 0.06f, 0.18f, P.theme);
                }
                bool jump = frame % 4 == 1 && Random.value < 1f - k * 0.7f;                        // occasionally one jumps to the ground
                ground.Visible = (jump);
                if (jump)
                {
                    Vector3 gp = ElementFX.GroundAt(c) + new Vector3(Random.Range(-0.4f, 0.4f), 0.02f, Random.Range(-0.4f, 0.4f));
                    BoltPath.Build(ground.mesh, c + toCam * targetRadius, gp, cam.transform.position, 0.085f, 1, 0.2f, 4);
                    ElementFX.Shape(P.star, gp + Vector3.up * 0.05f, 0.35f, 0.05f);                // on the frame it hits the ground, flash at the crack
                }
                frame++; t += Time.deltaTime; yield return null;
            }
            foreach (var a in arcs) Give(a); foreach (var g in glows) Give(g); Give(ground);
        }

        // ───────────────────────── Eruption (water column) ─────────────────────────
        // column atlas timing (profile.columnFrames) and the collapse moment (profile.columnHoldEnd) live in config, so swapping the atlas only changes data
        /// <summary>
        /// Charge → the water orb lobs low and dives in at the target's feet (cue: a small crown splashes up on landing) → a water ring spreads on the ground and bubbles as a warning →
        /// eruption (the brightest frame: white flash at the root + ground shock ring + radial splashes + water streaks shooting up the column) → the target is lifted to the top and held →
        /// the top collapses like an umbrella, rain falls from it and the target drops with it → wet ground.
        /// The column root sits on the ground behind the target (profile.columnBehind, from the camera direction at the moment of eruption; with an orbiting camera the root may end up off to the side):
        /// the target hides only the middle of the column, the column stays connected from the ground to the target's feet, and the face is always visible.
        /// columnFront (optional): an extra translucent front layer on top.
        /// </summary>
        IEnumerator Eruption(Transform tgt, Vector3 lastKnown, float charge, int stamp, List<Object> pieces)
        {
            var orb = ElementFX.Quad("Orb_" + P.displayName, P.orb, null);   // world space: a scaled caster rig must not scale the orb
            pieces.Add(orb.gameObject); spawned.Add(orb.gameObject);
            orb.localScale = Vector3.zero;
            yield return Charge(orb, charge, stamp);

            // 1) the water orb lobs low and dives in at the target's feet (landing on the caster's side of the target so the landing is visible)
            Vector3 hand = Hand;
            Vector3 gp = ElementFX.GroundAt(Center(tgt, lastKnown));
            Vector3 toHand = Vector3.ProjectOnPlane(hand - gp, Vector3.up).normalized;
            Vector3 entry = gp + toHand * targetRadius * 0.9f;
            float T = Mathf.Max(0.12f, Vector3.Distance(hand, entry) / Mathf.Max(0.5f, P.speed));
            Vector3 g = Physics.gravity * P.gravityScale + Vector3.down * (P.lift > 0 ? 8f * P.lift / (T * T) : 0f);   // same arc parameters as the projectile
            Vector3 v0 = (entry - hand) / T - 0.5f * g * T;                    // analytic trajectory: lands exactly on entry after T seconds
            ElementFX.Flash(hand, P.chargeSize * 2.2f, P.theme, 0.05f);
            float tf = 0, carry = 0, spacing = Mathf.Max(0.01f, P.trailSpacing); Vector3 prev = hand;
            while (tf < T)
            {
                tf = Mathf.Min(tf + Time.deltaTime, T);
                Vector3 pos = hand + v0 * tf + 0.5f * g * tf * tf, vel = v0 + g * tf;
                float seg = Vector3.Distance(prev, pos);
                carry += seg;
                for (int n = 0; carry >= spacing && n < 64; n++)                 // trail filled in by distance and interpolated along this frame's path (same as the projectile)
                {
                    carry -= spacing;
                    EmitTrail(Vector3.Lerp(pos, prev, seg > 1e-5f ? Mathf.Clamp01(carry / seg) : 0), vel, vel.normalized, 0);
                }
                if (carry >= spacing) carry %= spacing;
                prev = pos;
                orb.position = pos; orb.localScale = Vector3.one * P.flightSize * Mathf.Lerp(1f, 0.7f, tf / T);
                ElementFX.Face(orb, P.spinDegPerSec * tf);
                yield return null;
            }
            orb.gameObject.SetActive(false);

            // column root: from directly below the target, shift back by columnBehind (away from the camera, along the ground), so the column draws behind the target while the root, puddle and water rings share one spot on the ground
            var cam = Camera.main;
            Vector3 CamFlat(Vector3 at) => cam ? Vector3.ProjectOnPlane(cam.transform.position - at, Vector3.up).normalized : toHand;
            Vector3 Base(Vector3 under) => ElementFX.GroundAt(under - CamFlat(under) * P.columnBehind);
            Vector3 bp = Base(gp);

            // 2) dive: small crown + droplets splashing up; warning: a water ring spreads at the root + bubbles + a slight tremor
            if (P.extra == ImpactExtra.CrownSplash) StartCoroutine(Crown(entry + Vector3.up * 0.03f, Vector3.down, 0.55f, false));
            ElementFX.Shape(P.star, entry + Vector3.up * 0.15f, P.flashSize * 0.5f, 0.06f);
            for (int i = 0, n = ElementFX.Count(12); i < n; i++)
                ElementFX.Drop(entry + Random.insideUnitSphere * 0.1f, Random.insideUnitSphere * 1.2f + Vector3.up * Random.Range(1.5f, 2.6f), Random.Range(0.05f, 0.08f), 0.45f, Color.Lerp(P.theme, Color.white, 0.3f), P.matter);
            float decalLife = P.decalLife + P.warnTime + P.columnLife * 0.5f;    // the wet mark lasts from the dive until after the column has collapsed
            ElementFX.GroundDecal(P.decal, bp, P.decalSize, decalLife, P.decalTint);   // wet mark centred on the column root (the column bursts out of the puddle, and the target lands back in it)
            float decalStart = Time.time;
            if (P.ring) StartCoroutine(PlaneRing(bp + Vector3.up * 0.04f, Vector3.up, 0.3f, 1.4f, P.warnTime + 0.2f, false));
            HitFeel.Shake(P.shake * 0.3f, P.warnTime);
            float w = 0;
            while (w < P.warnTime)
            {
                if (tgt) { gp = ElementFX.GroundAt(Center(tgt, lastKnown = tgt.position + targetOffset)); bp = Base(gp); }
                for (int i = ElementFX.Rate(40, Time.deltaTime); i > 0; i--)
                    ElementFX.Bubble(bp + new Vector3(Random.Range(-0.5f, 0.5f), 0.04f, Random.Range(-0.5f, 0.5f)), Vector3.up * Random.Range(0.4f, 0.9f), Random.Range(0.08f, 0.14f), 0.35f, Color.Lerp(P.theme, Color.white, 0.35f), P.matter);
                w += Time.deltaTime; yield return null;
            }

            // 3) eruption: the brightest frame of the sequence: white flash at the root + star + ground shock ring + radial splashes + water streaks shooting up the column; the target is lifted
            float hitTime = Time.time, hold = P.columnLife * P.columnHoldEnd;
            Vector3 sunk = bp + Vector3.down * P.columnHeight * P.columnRootInset;  // in the atlas the column root is not at the very bottom of the cell: sink it so the root touches the ground
            ElementFX.Column(P.impact, sunk, P.columnHeight, P.columnAspect, P.columnLife, P.columnFrames);
            if (P.columnFront) ElementFX.Column(P.columnFront, sunk, P.columnHeight, P.columnAspect, P.columnLife, P.columnFrames);
            Vector3 c = Center(tgt, lastKnown);
            Vector3 toCam = CamFlat(gp);
            Vector3 root = gp + Vector3.up * P.flashSize * 0.85f + toCam * targetRadius;   // root burst in front of the target's feet; centre raised above the flash radius so the quad doesn't cut into the ground and get a straight clipped edge
            AnyHit?.Invoke(this);
            bool lifted = false;
            if (tgt) foreach (var r in tgt.GetComponentsInParent<IElementHitReceiver>())
            {
                r.OnElementHit(new ElementHit { element = P, point = root, direction = Vector3.up, power = 1f, lift = P.columnLift, liftTime = hold, liftShift = Vector3.ProjectOnPlane(bp - gp, Vector3.up), liftGravity = P.columnFallGravity, source = this });   // lift over the column (horizontal shift only, so height doesn't change on slopes)
                lifted = true;
            }
            float landAt = 0f;
            if (lifted && P.columnLift > 0)                                         // only a lifted target lands back in the puddle: play the landing ring after the lift ends + the free-fall time
            {
                landAt = hold + Mathf.Sqrt(2f * P.columnLift / Mathf.Max(1f, P.columnFallGravity));
                StartCoroutine(LandingSplash(bp, landAt));
            }
            ElementFX.Flash(root, P.flashSize * 1.6f, Color.white, 0.07f);             // soft radial flash only (an outlined small star reads as a round sticker here)
            ElementFX.LightFlash(gp + Vector3.up * 1.2f, P.theme, P.lightIntensity, P.lightRange, 0.25f);
            if (P.ring) StartCoroutine(PlaneRing(bp + Vector3.up * 0.06f, Vector3.up, 0.6f, 2.4f, 0.3f, true));   // ground shock ring: fast, short, breaks into droplets
            if (P.extra == ImpactExtra.CrownSplash) StartCoroutine(Crown(bp + Vector3.up * 0.05f, Vector3.down, 1.2f, false));
            float colW = P.columnHeight * P.columnAspect;
            for (int i = 0, n = ElementFX.Count(P.sparkCount * 2); i < n; i++)      // radial splashes: outward along the ground, slightly upward
            {
                Vector3 o = Quaternion.Euler(0, Random.Range(0, 360f), 0) * Vector3.forward;
                ElementFX.Drop(bp + o * colW * 0.2f + Vector3.up * 0.1f, o * Random.Range(2.5f, 4.5f) + Vector3.up * Random.Range(1.5f, 3f), Random.Range(0.06f, 0.11f), Random.Range(0.5f, 0.75f), Color.Lerp(P.theme, Color.white, 0.3f), P.matter);
            }
            for (int i = 0, n = ElementFX.Count(10); i < n; i++)                  // water streaks shooting up the column (sense of speed)
            {
                Vector3 o = Quaternion.Euler(0, Random.Range(0, 360f), 0) * Vector3.forward * colW * Random.Range(0.12f, 0.22f);
                ElementFX.Streak(bp + o + Vector3.up * Random.Range(0.1f, 0.8f), Vector3.up * Random.Range(10f, 15f), Random.Range(0.06f, 0.09f), Random.Range(0.18f, 0.28f), Color.Lerp(P.theme, Color.white, 0.45f));
            }
            HitFeel.Stop(P.hitStop);
            HitFeel.Shake(P.shake, P.shakeTime);
            if (P.ticks > 0) StartCoroutine(Ticks(tgt, lastKnown, Vector3.up, P.columnLift, true, hitTime + hold));

            // 4) the top collapses like an umbrella: rain falls from the rim (staggered over 0.35 s, not all at once), the target drops back to the ground, then water runs down its body
            while (Time.time - hitTime < hold) yield return null;
            Vector3 rim = bp + Vector3.up * P.columnHeight * P.columnRim;          // actual rim height (not the column top)
            for (float r = 0; r < 0.35f; r += Time.deltaTime)
            {
                for (int i = ElementFX.Rate(110, Time.deltaTime); i > 0; i--)
                {
                    Vector3 o = Quaternion.Euler(0, Random.Range(0, 360f), 0) * Vector3.forward * colW * Random.Range(0.25f, 0.45f);
                    ElementFX.Drop(rim + o + Vector3.down * r * 2f, o.normalized * Random.Range(0.2f, 0.6f) + Vector3.down * Random.Range(1f, 2f), Random.Range(0.06f, 0.1f), Random.Range(0.7f, 1f), Color.Lerp(P.theme, Color.white, 0.3f), P.matter);
                }
                yield return null;
            }
            Vector3 flat = Vector3.ProjectOnPlane(c - hand, Vector3.up).normalized;
            if (P.linger == LingerStyle.Drip) StartCoroutine(Streams(tgt, lastKnown, Color.Lerp(P.theme, Color.white, 0.5f), 6, 0.8f, 0.35f, P.matter, false, flat));
            yield return Linger(tgt, lastKnown, c, flat);
            while (Time.time - hitTime < Mathf.Max(P.columnLife, landAt + 0.4f) || Time.time - decalStart < decalLife) yield return null;   // finished only when the column, landing ring and ground mark have all faded
        }

        IEnumerator LandingSplash(Vector3 at, float delay)
        {
            if (delay > 0) yield return new WaitForSeconds(delay);
            // only a flat ring on the ground (spreading out, breaking into droplets) + droplets splashing outward; a 3D crown around the target's base reads as 'sitting in a blue bowl'
            if (P.ring) StartCoroutine(PlaneRing(at + Vector3.up * 0.05f, Vector3.up, 0.6f, 2.2f, 0.3f, true));
            for (int i = 0, n = ElementFX.Count(14); i < n; i++)
            {
                Vector3 o = Quaternion.Euler(0, (i + Random.value) * 360f / n, 0) * Vector3.forward;
                ElementFX.Drop(at + o * 0.4f + Vector3.up * 0.05f, o * Random.Range(1.8f, 3f) + Vector3.up * Random.Range(1f, 2f), Random.Range(0.05f, 0.09f), 0.5f, Color.Lerp(P.theme, Color.white, 0.3f), P.matter);
            }
        }

        // ───────────────────────── Lightning (instant) ─────────────────────────
        IEnumerator Lightning(Transform tgt, Vector3 lastKnown, float charge, int stamp, List<Object> pieces)
        {
            var cam = Camera.main;
            if (!cam) { Debug.LogError("[ElementSkill] lightning needs a camera to face", this); yield break; }
            var orb = ElementFX.Quad("Orb_" + P.displayName, P.orb, null);   // world space: a scaled caster rig must not scale the orb
            pieces.Add(orb.gameObject); spawned.Add(orb.gameObject);
            var micro = Take(P.shell);
            float t = 0; int frame = 0;
            // 1) crackling charge in the palm: small orb + a new small arc every two or three frames
            while (!ChargeDone(t, charge, stamp))
            {
                Vector3 h = Hand;
                orb.position = h; orb.localScale = Vector3.one * P.chargeSize * (0.7f + 0.3f * Mathf.Clamp01(t / charge)) * (1 + 0.15f * Mathf.Sin(t * 70));
                ElementFX.Face(orb, Random.Range(0, 360f));
                bool show = frame % 3 != 2;
                micro.Visible = (show);
                if (show) BoltPath.Build(micro.mesh, h + Random.insideUnitSphere * 0.08f, h + Random.onUnitSphere * Random.Range(0.25f, 0.45f), cam.transform.position, 0.06f, 1, 0.25f, 3);
                for (int i = ElementFX.Rate(25, Time.deltaTime); i > 0; i--) ElementFX.Spark(h + Random.insideUnitSphere * 0.2f, Random.insideUnitSphere * 2.5f, 0.05f, 0.12f, P.theme);
                frame++; t += Time.deltaTime; yield return null;
            }
            orb.gameObject.SetActive(false); Give(micro);

            // 2) strikes scheduled in frames: main strike on frames 0–1, return stroke on frame 3, after-flash on frame 6 (each strike is guaranteed to be drawn, each with a different path)
            //    Timing is counted in frames so every strike is visible for at least 1 frame at any frame rate; the whole sequence is about 0.12 s at 60 fps, 0.23 s at 30 fps.
            Vector3 hand = Hand;
            Vector3 aim = Surface(tgt, lastKnown, hand);
            Vector3 dir = (aim - hand).normalized;
            var bolt = Take(P.shell);
            var glow = P.glow ? Take(P.glow) : null;
            int[] strikeFrames = { 0, 1, 3, 6 };
            float[] width = { 0.3f, 0.28f, 0.24f, 0.2f };
            float[] power = { 1f, 0f, 0.6f, 0.45f };
            int si = 0;
            float hitTime = Time.time;
            for (int f = 0; f <= 7; f++)
            {
                hand = Hand;                                                    // the bolt root stays attached to the hand (the hand is moving)
                if (tgt) { lastKnown = tgt.position + targetOffset; aim = Surface(tgt, lastKnown, hand); }
                bool on = si < strikeFrames.Length && strikeFrames[si] == f;
                bolt.Visible = (on); if (glow) glow.Visible = on;
                if (on)
                {
                    BoltPath.Build(bolt.mesh, hand, aim, cam.transform.position, width[si], si == 0 ? 3 : 2, 0.13f, 5, glow ? glow.mesh : null);
                    bolt.Set(0, 1f);
                    if (f == 0) { Hit(tgt, lastKnown, aim, dir); ElementFX.Flash(hand, P.chargeSize * 2.5f, P.theme, 0.05f); }
                    else if (power[si] > 0) { Notify(tgt, aim, dir, power[si]); Burst(aim, dir, power[si], Center(tgt, lastKnown), true); }
                    si++;
                }
                yield return null;
            }
            Give(bolt); Give(glow);
            yield return Linger(tgt, lastKnown, aim, dir);
            while (Time.time - hitTime < P.decalLife) yield return null;
        }

        // a few streams down the camera-facing side of the target: each has a fixed start point that emits a drop every few frames.
        // sticky=false (water): small droplets slide quickly down the body and fall under gravity once they leave the lower edge, reading as flowing water.
        // sticky=true (poison): thick poison first clings and stretches, then drops faster and faster, reading as sticky strands.
        IEnumerator Streams(Transform tgt, Vector3 lastKnown, Color col, int count, float dur, float startH, Material mat, bool sticky, Vector3 hitDir)
        {
            var cam = Camera.main;
            var offs = new Vector3[count];
            // start points on the half facing away from the caster (the face looks toward the caster): streams run from the side / back of the head and never over the eyes
            Vector3 c0 = Center(tgt, lastKnown);
            Vector3 toCam0 = cam ? Vector3.ProjectOnPlane(cam.transform.position - c0, Vector3.up).normalized : Vector3.back;
            float away = Mathf.Sign(Vector3.Dot(Vector3.Cross(Vector3.up, toCam0), hitDir) + 1e-4f);
            for (int i = 0; i < count; i++) offs[i] = new Vector3(away * Mathf.Lerp(0.2f, 0.7f, (i + Random.value * 0.5f) / count), startH + Random.Range(-0.25f, 0.1f), 0);   // keep the three apart instead of merging into one
            float t = 0, next = 0;
            while (t < dur)
            {
                if (t >= next)
                {
                    next = t + (sticky ? Random.Range(0.16f, 0.22f) : Random.Range(0.08f, 0.12f));   // poison: drop by drop, each stream staggered
                    Vector3 c = Center(tgt, lastKnown);
                    Vector3 toCam = cam ? Vector3.ProjectOnPlane(cam.transform.position - c, Vector3.up).normalized : Vector3.back;
                    Vector3 side = Vector3.Cross(Vector3.up, toCam);
                    for (int i = 0; i < count; i++)
                    {
                        if (sticky && Mathf.Repeat(t / 0.5f + i / (float)count, 1f) > 0.3f) continue;     // poison: three staggered streams, one drop per stream every 0.5 s
                        if (Random.value < t / dur * 0.6f) continue;                                  // thinning out
                        Vector3 o = side * offs[i].x * targetRadius + Vector3.up * offs[i].y * targetRadius;
                        float surf = Mathf.Sqrt(Mathf.Max(0.05f, 1 - (offs[i].x * offs[i].x + offs[i].y * offs[i].y) * 0.8f));
                        Vector3 p = c + o + toCam * targetRadius * (surf + 0.12f);
                        if (sticky) ElementFX.Goo(p, Vector3.down * 0.1f, 0.16f, 0.55f, col, mat);   // heavy drop head with a short tail
                        else
                        {
                            bool big = Random.value < 0.25f;                                       // an occasional big droplet (with highlight) that stretches as it leaves the lower edge and falls into the water stain
                            ElementFX.Drop(p, Vector3.down * Random.Range(0.8f, 1.3f) + toCam * 0.15f, big ? 0.12f : Random.Range(0.06f, 0.09f), Random.Range(0.5f, 0.7f), big ? Color.Lerp(col, Color.white, 0.4f) : col, mat);
                        }
                    }
                }
                t += Time.deltaTime; yield return null;
            }
        }

        // ───────────────────────── Linger ─────────────────────────
        static Vector3 LingerToCam(Vector3 at)
        {
            var cam = Camera.main;
            Vector3 d = cam ? Vector3.ProjectOnPlane(cam.transform.position - at, Vector3.up) : Vector3.back;
            return d.sqrMagnitude > 1e-6f ? d.normalized : Vector3.back;
        }

        IEnumerator Linger(Transform tgt, Vector3 lastKnown, Vector3 p, Vector3 dir)
        {
            float dur = P.lingerTime, t = 0;
            Vector3 gp = ElementFX.GroundAt(Center(tgt, lastKnown));
            while (t < dur)
            {
                float k = 1 - t / dur, dt = Time.deltaTime;
                Vector3 c = Center(tgt, lastKnown);
                switch (P.linger)
                {
                    case LingerStyle.Drip:     // water: a few streams slowly run down the camera-facing side, dripping from the sides and bottom edge (never onto the face), tapering off
                    {
                        var wcam = Camera.main; Vector3 wToCam = wcam ? Vector3.ProjectOnPlane(wcam.transform.position - c, Vector3.up).normalized : -dir;
                        // (the running streams are handled by Streams)
                    }
                        for (int i = ElementFX.Rate(24 * k, dt); i > 0; i--)
                        {
                            float side = Random.value < 0.5f ? -1 : 1;
                            Vector3 o = new Vector3(side * Random.Range(0.35f, 0.5f), Random.Range(-0.55f, -0.1f), Random.Range(-0.3f, 0.3f));
                            ElementFX.Drop(c + Quaternion.LookRotation(-dir) * o, Vector3.down * 0.3f, Random.Range(0.04f, 0.08f), 0.6f, Color.Lerp(P.theme, Color.white, 0.25f), P.matter);
                        }
                        break;
                    case LingerStyle.Smolder:  // fire: embers rise out of frame from the scorch mark and the target, faint smoke billows up from behind the target (in front it reads as an ink blot stuck on the body), embers in the scorch flicker 2–3 times
                        if (Random.value < dt * 2.2f * k) ElementFX.LightFlash(gp + Vector3.up * 0.2f, new Color(1f, 0.32f, 0.08f), 2f, 1.4f, 0.25f);   // reddish: orange light on greenish ground turns yellow-green
                        for (int i = ElementFX.Rate(22 * k, dt); i > 0; i--)
                            ElementFX.Ember((Random.value < 0.5f ? gp : c) + Random.insideUnitSphere * 0.5f + Vector3.up * 0.05f, Vector3.up * Random.Range(1f, 2.4f) + Random.insideUnitSphere * 0.3f, Random.Range(0.05f, 0.09f), Random.Range(1.0f, 1.6f), P.theme);
                        for (int i = ElementFX.Rate(5 * k, dt); i > 0; i--)
                            ElementFX.Smoke(gp - LingerToCam(gp) * (targetRadius + 0.2f) + Random.insideUnitSphere * 0.3f + Vector3.up * 0.2f, Vector3.up * Random.Range(0.8f, 1.2f), Random.Range(0.3f, 0.45f), 0.9f, new Color(0.55f, 0.5f, 0.48f, 0.3f), P.smoke);
                        break;
                    case LingerStyle.Pool:     // poison: pool bubbles (rise, swell, pop) + low ground mist spreading outward + still running down the target
                        for (int i = ElementFX.Rate(16 * k, dt); i > 0; i--)
                            ElementFX.Bubble(gp + new Vector3(Random.Range(-0.7f, 0.7f), 0.05f, Random.Range(-0.7f, 0.7f)), Vector3.up * Random.Range(0.15f, 0.35f), Random.Range(0.15f, 0.28f), Random.Range(0.6f, 0.9f), Color.Lerp(P.theme, Color.white, 0.15f), P.matter);
                        for (int i = ElementFX.Rate(7 * k, dt); i > 0; i--)
                        {
                            Vector3 o = new Vector3(Random.Range(-1f, 1f), 0, Random.Range(-1f, 1f)).normalized;
                            ElementFX.Smoke(gp + o * 0.35f + Vector3.up * 0.15f, o * Random.Range(0.4f, 0.7f) + Vector3.up * 0.04f, Random.Range(1.0f, 1.4f), Random.Range(1.2f, 1.6f), new Color(0.66f, 0.84f, 0.5f, 0.16f), P.smoke);   // faint, large mist spreading along the ground
                        }
                        var lcam = Camera.main; Vector3 lToCam = lcam ? Vector3.ProjectOnPlane(lcam.transform.position - c, Vector3.up).normalized : -dir;
                        // (strands are handled by Streams)
                        break;
                    case LingerStyle.Swirl:    // wind: leftover swirl lines wind down
                        for (int i = ElementFX.Rate(18 * k, dt); i > 0; i--)
                        {
                            float a = Random.Range(0, Mathf.PI * 2); Vector3 r = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
                            ElementFX.Streak(gp + r * 0.9f + Vector3.up * Random.Range(0.1f, 1.2f), Vector3.Cross(Vector3.up, r) * 5f + Vector3.up * 1.2f, 0.05f, 0.25f, Color.Lerp(P.theme, Color.white, 0.2f));
                        }
                        break;
                    case LingerStyle.Static:   // lightning: small sparks jumping along the ground cracks, thinning out
                        if (Random.value < dt * 14 * k)
                        {
                            Vector3 sp = gp + new Vector3(Random.Range(-0.5f, 0.5f), 0.05f, Random.Range(-0.5f, 0.5f));
                            ElementFX.Shape(P.star, sp + Vector3.up * 0.05f, Random.Range(0.25f, 0.4f), 0.08f);
                            for (int i = 0; i < 3; i++) ElementFX.Spark(sp, Random.insideUnitSphere * 2f + Vector3.up, 0.05f, 0.14f, P.theme);
                        }
                        break;
                }
                t += dt; yield return null;
            }
        }
    }
}
