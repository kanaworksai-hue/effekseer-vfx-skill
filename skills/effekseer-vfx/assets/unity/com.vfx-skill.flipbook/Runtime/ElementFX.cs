using System.Collections.Generic;
using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// Particle hub for element skills. All particles are world-space and emitted manually; materials are referenced directly by ElementProfile (no lookup by string).
    /// Layer roles (see effekseer-vfx craft/layering):
    ///   core   = contact flash / sparks (additive, small area, lit for only 2 frames)
    ///   body   = impact flipbooks, water crown / wind band / lightning shells (alpha-blended three-tone cel colour that doesn't wash out on bright backgrounds)
    ///   matter = smoke / poison mist / water droplets / poison drips / bubbles (alpha-blended, with weight)
    ///   ground = ground decals (scorch / poison pool / water stain / cracks / wind streaks), fading out by erosion
    /// Budget: density (0–1) scales all rate-based particle counts; maxParticleSize limits the screen share of large quads (mobile overdraw).
    /// </summary>
    [DefaultExecutionOrder(-100)]
    public class ElementFX : MonoBehaviour
    {
        static ElementFX _inst;
        public static ElementFX I
        {
            get
            {
                if (_inst) return _inst;
                _inst = FindAnyObjectByType<ElementFX>();
                if (!_inst) _inst = new GameObject("ElementFX").AddComponent<ElementFX>();
                return _inst;
            }
        }

        [Tooltip("Ground height when there is no collider")] public float groundY = 0f;
        [Tooltip("Layers for ground detection (only Default by default; characters, hit targets and objects with rigidbodies are skipped)")] public LayerMask groundMask = 1;
        [Range(0.1f, 1f), Tooltip("Quality: multiplier for rate-based particle counts (0.5 on low-end devices)")] public float density = 1f;
        [SerializeField, Range(0.2f, 2f), Tooltip("Maximum fraction of screen height a single particle may cover")] float maxScreenSize = 0.9f;
        /// <summary>Maximum screen share of a single particle (runtime changes apply to all systems immediately, except decals).</summary>
        public float MaxScreenSize
        {
            get => maxScreenSize;
            set { maxScreenSize = value; foreach (var r in GetComponentsInChildren<ParticleSystemRenderer>(true)) if (!r.name.StartsWith("Decal_") && !r.name.StartsWith("Column_")) r.maxParticleSize = value; }
        }
        [Tooltip("Maximum concurrent impact bodies of the same kind (at the limit Unity drops the newly emitted one)")] public int maxBodiesPerElement = 32;
        [Header("Hit lights")]
        [Tooltip("Theme-coloured point light on hit (per-pixel lighting has a cost on mobile; turn off on low quality)")] public bool hitLights = true;
        [Range(0, 4), Tooltip("Maximum concurrent hit lights; 1 by default on mobile")] public int maxHitLights = 4;

        ParticleSystem sparks, streaks, flash, smoke, drops, bubbles, goo, embers;
        readonly Dictionary<Material, ParticleSystem> shapes = new Dictionary<Material, ParticleSystem>();
        readonly List<Light> lights = new List<Light>();
        readonly List<float> lightEnd = new List<float>(), lightLife = new List<float>(), lightPeak = new List<float>();
        readonly Dictionary<Material, ParticleSystem> flipbooks = new Dictionary<Material, ParticleSystem>();
        readonly Dictionary<Material, ParticleSystem> columns = new Dictionary<Material, ParticleSystem>();
        readonly Dictionary<Material, ParticleSystem> trails = new Dictionary<Material, ParticleSystem>();
        readonly Dictionary<Material, ParticleSystem> decals = new Dictionary<Material, ParticleSystem>();
        readonly List<ShellPiece> shellPool = new List<ShellPiece>();
        readonly Dictionary<(ParticleSystem, Material), ParticleSystem> variants = new Dictionary<(ParticleSystem, Material), ParticleSystem>();
        static Mesh quad;
        /// <summary>Maximum screen share allowed for the column (water column): single layer, shown only for ~2 s on hit; verify mobile overdraw on device.</summary>
        const float ColumnMaxScreen = 1.6f;
        static readonly RaycastHit[] hits = new RaycastHit[8];

        static Material Res(string n) => Resources.Load<Material>("VfxSkill/" + n);

        void Awake()
        {
            if (_inst && _inst != this) { Destroy(gameObject); return; }
            _inst = this;
            if (Application.isMobilePlatform) maxHitLights = Mathf.Min(maxHitLights, 1);
            Build();
            PrewarmLights();
        }

        // Warm-up: create the lights at startup, place them right in front of the camera and light them at tiny intensity for 2 frames, so shader variants with additional lights compile at load and the first hit doesn't hitch.
        // Objects that appear later still compile when first lit; in production also prewarm with ShaderVariantCollection / GraphicsStateCollection.
        void PrewarmLights()
        {
            if (!hitLights) return;
            EnsureLights();
            var cam = Camera.main;
            for (int i = 0; i < lights.Count; i++)
            {
                var l = lights[i];
                l.transform.position = cam ? cam.transform.position + cam.transform.forward * 3f : Vector3.zero;
                l.intensity = 0.01f; l.range = 4f; l.enabled = true;
                lightEnd[i] = Time.time + 0.1f; lightLife[i] = 0.1f; lightPeak[i] = 0.01f;
            }
        }

        void EnsureLights()
        {
            while (lights.Count < maxHitLights)
            {
                var l = new GameObject("HitLight").AddComponent<Light>(); l.transform.SetParent(transform, false);
                l.type = LightType.Point; l.shadows = LightShadows.None; l.enabled = false;
                lights.Add(l); lightEnd.Add(0); lightLife.Add(1); lightPeak.Add(0);
            }
        }

        ParticleSystem PS(string name, Material mat, int max, ParticleSystemRenderMode mode)
        {
            if (!mat) Debug.LogError($"[ElementFX] {name}: material missing");
            var go = new GameObject(name); go.transform.SetParent(transform, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var m = ps.main; m.playOnAwake = false; m.simulationSpace = ParticleSystemSimulationSpace.World;
            m.maxParticles = max; m.startSpeed = 0; m.scalingMode = ParticleSystemScalingMode.Shape;
            var em = ps.emission; em.enabled = false;
            var sh = ps.shape; sh.enabled = false;
            var r = go.GetComponent<ParticleSystemRenderer>();
            r.sharedMaterial = mat; r.renderMode = mode; r.sortMode = ParticleSystemSortMode.Distance;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            r.maxParticleSize = maxScreenSize;
            ps.Play();
            return ps;
        }

        static AnimationCurve Curve(params float[] tv) { var c = new AnimationCurve(); for (int i = 0; i < tv.Length; i += 2) c.AddKey(tv[i], tv[i + 1]); return c; }
        static Gradient Fade(float inT, float hold)
        {
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                      new[] { new GradientAlphaKey(inT > 0 ? 0 : 1, 0), new GradientAlphaKey(1, Mathf.Max(inT, 0.001f)), new GradientAlphaKey(1, hold), new GradientAlphaKey(0, 1) });
            return g;
        }
        static void Drag(ParticleSystem ps, float drag)
        {
            var lv = ps.limitVelocityOverLifetime; lv.enabled = true; lv.drag = drag; lv.multiplyDragByParticleSize = false; lv.limit = 80;
        }
        static void Sheet(ParticleSystem ps, int n)
        {
            var ts = ps.textureSheetAnimation; ts.enabled = true; ts.numTilesX = n; ts.numTilesY = n;
            ts.frameOverTime = new ParticleSystem.MinMaxCurve(0); ts.startFrame = new ParticleSystem.MinMaxCurve(0, n * n - 0.01f);
        }

        void Build()
        {
            // core: small sparks, fast then slowing (drag)
            // sparks / speed lines use alpha-blended saturated colour: additive is invisible on bright backgrounds and white targets
            sparks = PS("Sparks", Res("M_Spark"), 3000, ParticleSystemRenderMode.Billboard);
            { var c = sparks.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0.25f);
              var sz = sparks.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 1, 1, 0.15f));
              Drag(sparks, 3f); }
            // speed lines: stretched bright streaks (directional spray along the trajectory on hit)
            streaks = PS("Streaks", Res("M_Spark"), 2000, ParticleSystemRenderMode.Stretch);
            { var c = streaks.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0.2f);
              var r = streaks.GetComponent<ParticleSystemRenderer>(); r.velocityScale = 0.05f; r.lengthScale = 2f;
              Drag(streaks, 2.5f); }
            // contact flash: lives about 2 frames, grows fast then vanishes
            flash = PS("Flash", Res("M_Flash"), 100, ParticleSystemRenderMode.Billboard);
            { var c = flash.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0.3f);
              var sz = flash.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 0.6f, 1, 1.25f)); }
            // matter: translucent smoke puffs / poison mist, slowly expanding and slowing down
            smoke = PS("Smoke", Res("M_Smoke"), 800, ParticleSystemRenderMode.Billboard);   // neutral grey smoke, tinted by vertex colour
            { Sheet(smoke, 2);
              var c = smoke.colorOverLifetime; c.enabled = true; c.color = Fade(0.15f, 0.3f);
              var sz = smoke.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 0.5f, 0.3f, 0.9f, 1, 1.4f));
              var rot = smoke.rotationOverLifetime; rot.enabled = true; rot.z = new ParticleSystem.MinMaxCurve(-0.6f, 0.6f);
              var m = smoke.main; m.startRotation = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
              Drag(smoke, 1.2f); }
            // matter: water droplets / poison drips (affected by gravity)
            drops = PS("Drops", Res("M_Drop"), 1500, ParticleSystemRenderMode.Billboard);
            { Sheet(drops, 2);
              var m = drops.main; m.gravityModifier = 1f;
              var c = drops.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0.75f);
              var sz = drops.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 1, 0.8f, 0.9f, 1, 0.4f)); }
            // matter: bubbles (poison pool), slowly rising and growing, then a final swell and pop
            bubbles = PS("Bubbles", Res("M_Drop"), 300, ParticleSystemRenderMode.Billboard);
            { Sheet(bubbles, 2);
              var c = bubbles.colorOverLifetime; c.enabled = true; c.color = Fade(0.1f, 0.85f);
              var sz = bubbles.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 0.3f, 0.8f, 1f, 0.92f, 1.35f, 1, 0f));
              Drag(bubbles, 2f); }
            // core: embers with negative gravity, drifting up and slowly shrinking (fire physics: heat rises)
            embers = PS("Embers", Res("M_Spark"), 600, ParticleSystemRenderMode.Billboard);
            { var m = embers.main; m.gravityModifier = -0.35f;
              var c = embers.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0.6f);
              var sz = embers.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 1, 1, 0.25f));
              var no = embers.noise; no.enabled = true; no.strength = 0.6f; no.frequency = 1.2f;
              Drag(embers, 0.8f); }
            // matter: sticky poison strands (stretched, slowly running down the surface)
            goo = PS("Goo", Res("M_Drop"), 400, ParticleSystemRenderMode.Stretch);
            { Sheet(goo, 2);
              var m = goo.main; m.gravityModifier = 1.1f;                      // viscous: starts slow and speeds up, about 0.5 s from the top to the lower edge
              var r = goo.GetComponent<ParticleSystemRenderer>(); r.velocityScale = 0.1f; r.lengthScale = 1.3f;   // short tail: at most about 1/3 of the body
              var c = goo.colorOverLifetime; c.enabled = true; c.color = Fade(0.05f, 0.8f);
              var sz = goo.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 0.6f, 0.5f, 1f, 1, 0.7f));
              Drag(goo, 0.5f); }
        }

        /// <summary>Cel shape particles (impact star / shock ring): StylizedShell material, vertex alpha 1→0 = erosion progress (the thinnest points break first).</summary>
        ParticleSystem Shape(Material mat)
        {
            if (shapes.TryGetValue(mat, out var ps) && ps) return ps;
            ps = PS("Shape_" + mat.name, mat, 40, ParticleSystemRenderMode.Billboard);
            var c = ps.colorOverLifetime; c.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                      new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(0.85f, 0.4f), new GradientAlphaKey(0, 1) });
            c.color = g;
            bool star = mat.name.EndsWith("_Star");   // CreateElementSkill names contact stars M_<Skill>_Star
            var sz = ps.sizeOverLifetime; sz.enabled = true;
            sz.size = new ParticleSystem.MinMaxCurve(1, star ? Curve(0, 1f, 0.5f, 0.6f, 1, 0.2f)       // star (contact white core): largest on the first frame, shrinking each frame
                                                             : Curve(0, 0.45f, 0.25f, 0.9f, 1, 1.15f)); // shock ring: snaps open, then keeps growing slowly
            shapes[mat] = ps;
            return ps;
        }

        ParticleSystem Flipbook(Material mat)
        {
            if (flipbooks.TryGetValue(mat, out var ps) && ps) return ps;
            ps = PS("Flip_" + mat.name, mat, maxBodiesPerElement, ParticleSystemRenderMode.Billboard);
            var ts = ps.textureSheetAnimation; ts.enabled = true; SetTiles(ts, mat);
            ts.animation = ParticleSystemAnimationType.WholeSheet;
            ts.frameOverTime = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, 0, 1, 1));
            var c = ps.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0.85f);   // erode once more at the end so it never pops out
            Vector4 grow = mat.HasProperty("_Grow") ? mat.GetVector("_Grow") : Vector4.zero;   // the material can request a 'snap-grow from small' (for atlases whose first frame is already full size, e.g. explosions)
            var sz = ps.sizeOverLifetime; sz.enabled = true;
            sz.size = new ParticleSystem.MinMaxCurve(1, grow.x > 0 && grow.y > 0 ? Curve(0, grow.x, grow.y, 1f, 1, 1.15f) : Curve(0, 0.85f, 0.2f, 1f, 1, 1.2f));   // the body keeps growing and spreading instead of fading in place
            flipbooks[mat] = ps;
            return ps;
        }

        /// <summary>Atlas layout: the material's _Tiles (columns, rows); 8×8 if absent.</summary>
        static void SetTiles(ParticleSystem.TextureSheetAnimationModule ts, Material mat)
        {
            Vector4 t = mat && mat.HasProperty("_Tiles") ? mat.GetVector("_Tiles") : new Vector4(8, 8, 0, 0);
            ts.numTilesX = Mathf.Max(1, (int)t.x); ts.numTilesY = Mathf.Max(1, (int)t.y);
        }

        /// <summary>
        /// Vertical flipbook column (water column): faces the camera around Y only, with its bottom edge pinned to the emit point (the column grows out of the ground and doesn't tip over in high-angle shots).
        /// frames: life fraction → frame progress (fast surge, hold, collapse), from ElementProfile.columnFrames; only the first call per material takes effect.
        /// </summary>
        ParticleSystem Columns(Material mat, AnimationCurve frames)
        {
            if (columns.TryGetValue(mat, out var ps) && ps) return ps;
            ps = PS("Column_" + mat.name, mat, 8, ParticleSystemRenderMode.VerticalBillboard);
            var m = ps.main; m.startSize3D = true;
            var r = ps.GetComponent<ParticleSystemRenderer>(); r.pivot = new Vector3(0, 0.5f, 0); r.maxParticleSize = ColumnMaxScreen;   // the column is meant to extend past the frame; not limited by MaxScreenSize (otherwise it suddenly shrinks in close-ups)
            var ts = ps.textureSheetAnimation; ts.enabled = true; SetTiles(ts, mat);
            ts.animation = ParticleSystemAnimationType.WholeSheet;
            ts.frameOverTime = new ParticleSystem.MinMaxCurve(1, frames != null && frames.length >= 2 ? frames : AnimationCurve.Linear(0, 0, 1, 1));
            var c = ps.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0.92f);
            columns[mat] = ps;
            return ps;
        }

        public static void Column(Material mat, Vector3 basePos, float height, float aspect, float life, AnimationCurve frames = null)
        {
            if (!mat) return;
            var e = P(basePos, Vector3.zero, height, life, Color.white);
            e.startSize3D = new Vector3(height * aspect, height, 1);
            I.Columns(mat, frames).Emit(e, 1);
        }

        /// <summary>The same particle system with a different material (an element's own smoke / droplet texture); cloned on demand and cached.</summary>
        ParticleSystem Variant(ParticleSystem baseSys, Material mat)
        {
            if (!mat) return baseSys;
            if (variants.TryGetValue((baseSys, mat), out var ps) && ps) return ps;
            ps = Instantiate(baseSys, transform);
            ps.name = baseSys.name + "_" + mat.name;
            ps.GetComponent<ParticleSystemRenderer>().sharedMaterial = mat;
            ps.Play();
            variants[(baseSys, mat)] = ps;
            return ps;
        }

        ParticleSystem Trail(Material mat)
        {
            if (trails.TryGetValue(mat, out var ps) && ps) return ps;
            ps = PS("Trail_" + mat.name, mat, 400, ParticleSystemRenderMode.Billboard);
            var c = ps.colorOverLifetime; c.enabled = true; c.color = Fade(0, 0f);
            var sz = ps.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 1, 1, 0.3f));
            trails[mat] = ps;
            return ps;
        }

        ParticleSystem Decal(Material mat)
        {
            if (decals.TryGetValue(mat, out var ps) && ps) return ps;
            ps = PS("Decal_" + mat.name, mat, 40, ParticleSystemRenderMode.HorizontalBillboard);
            var r = ps.GetComponent<ParticleSystemRenderer>(); r.sortingFudge = 50; r.maxParticleSize = 5;   // draw ground decals first; decals lie flat on the ground and aren't limited by screen share
            var c = ps.colorOverLifetime; c.enabled = true; c.color = Fade(0.05f, 0.4f);   // vertex alpha drives PaintedFX erosion: breaks up and fades, always ending at 0
            var sz = ps.sizeOverLifetime; sz.enabled = true; sz.size = new ParticleSystem.MinMaxCurve(1, Curve(0, 0.5f, 0.1f, 1f, 1, 1.06f));
            decals[mat] = ps;
            return ps;
        }

        /// <summary>Clears all effects. Call only when no skill is playing (e.g. camera cuts, scene changes), otherwise a playing skill loses the shells it borrowed.</summary>
        public void ClearAll()
        {
            foreach (var p in new[] { sparks, streaks, flash, smoke, drops, bubbles, goo, embers }) if (p) p.Clear();
            foreach (var d in new[] { flipbooks, columns, trails, decals, shapes }) foreach (var p in d.Values) if (p) p.Clear();
            foreach (var l in lights) if (l) l.enabled = false;
            foreach (var p in variants.Values) if (p) p.Clear();
            foreach (var s in shellPool) if (s) s.Release();
        }

        /// <summary>Converts a rate (per second) × density into this frame's emit count (stochastic rounding, accurate on average).</summary>
        public static int Rate(float perSecond, float dt)
        {
            float n = perSecond * dt * (_inst ? _inst.density : 1f);
            int k = Mathf.FloorToInt(n);
            if (Random.value < n - k) k++;
            return k;
        }

        /// <summary>Burst count scaled by the quality budget (at least 1).</summary>
        public static int Count(int n) => n <= 0 ? 0 : Mathf.Max(1, Mathf.RoundToInt(n * (_inst ? _inst.density : 1f)));

        /// <summary>Ground point directly below p: only hits groundMask layers, skipping characters / hit targets / objects with rigidbodies; falls back to groundY if nothing is hit.</summary>
        public static Vector3 GroundAt(Vector3 p)
        {
            var g = I;
            int n = Physics.RaycastNonAlloc(p + Vector3.up * 2f, Vector3.down, hits, 20f, g.groundMask, QueryTriggerInteraction.Ignore);
            float best = float.MaxValue; Vector3 point = default; bool found = false;
            for (int i = 0; i < n; i++)
            {
                var c = hits[i].collider;
                if (c.attachedRigidbody || c.GetComponentInParent<IElementHitReceiver>() != null || c.GetComponentInParent<CharacterController>()) continue;
                if (hits[i].distance < best) { best = hits[i].distance; point = hits[i].point; found = true; }
            }
            if (found) return point;
            p.y = g.groundY; return p;
        }

        static ParticleSystem.EmitParams P(Vector3 p, Vector3 v, float s, float l, Color c, float rot = 0)
            => new ParticleSystem.EmitParams { position = p, velocity = v, startSize = s, startLifetime = l, startColor = c, rotation = rot, applyShapeToPosition = false };

        public static void Spark(Vector3 p, Vector3 v, float s, float l, Color c) => I.sparks.Emit(P(p, v, s, l, c), 1);
        public static void Streak(Vector3 p, Vector3 v, float s, float l, Color c) => I.streaks.Emit(P(p, v, s, l, c), 1);
        /// <summary>Contact flash: 0.06 s by default ≈ 2 frames (30 fps).</summary>
        public static void Flash(Vector3 p, float s, Color c, float l = 0.06f) => I.flash.Emit(P(p, Vector3.zero, s, l, Color.Lerp(c, Color.white, 0.55f)), 1);
        public static void Smoke(Vector3 p, Vector3 v, float s, float l, Color c, Material mat = null) => I.Variant(I.smoke, mat).Emit(P(p, v, s, l, c, Random.Range(0, 360f)), 1);
        public static void Drop(Vector3 p, Vector3 v, float s, float l, Color c, Material mat = null) => I.Variant(I.drops, mat).Emit(P(p, v, s, l, c), 1);
        public static void Bubble(Vector3 p, Vector3 v, float s, float l, Color c, Material mat = null) => I.Variant(I.bubbles, mat).Emit(P(p, v, s, l, c), 1);
        public static void Ember(Vector3 p, Vector3 v, float s, float l, Color c) => I.embers.Emit(P(p, v, s, l, c), 1);
        public static void Goo(Vector3 p, Vector3 v, float s, float l, Color c, Material mat = null) => I.Variant(I.goo, mat).Emit(P(p, v, s, l, c), 1);
        /// <summary>Cel shape (impact star / shock ring) with a very short life (0.1–0.25 s).</summary>
        public static void Shape(Material mat, Vector3 p, float size, float life, float rot = -1) { if (mat) I.Shape(mat).Emit(P(p, Vector3.zero, size, life, Color.white, rot < 0 ? Random.Range(0, 360f) : rot), 1); }

        /// <summary>Real light on hit: a theme-coloured point light that flares instantly and decays fast (lights the target and the ground).</summary>
        public static void LightFlash(Vector3 p, Color c, float intensity, float range, float life)
        {
            var g = I;
            if (!g.hitLights) return;
            g.EnsureLights();                                                    // also works if hitLights is turned on at runtime
            if (g.lights.Count == 0 || g.maxHitLights <= 0) return;
            int idx = 0; float oldest = float.MaxValue;                      // prefer an idle light; if all are busy, reuse the one that goes out soonest
            for (int i = 0; i < Mathf.Min(g.lights.Count, g.maxHitLights); i++)
            {
                if (!g.lights[i]) continue;
                float end = g.lights[i].enabled ? g.lightEnd[i] : float.MinValue;
                if (end < oldest) { oldest = end; idx = i; }
            }
            var lt = g.lights[idx];
            lt.transform.position = p; lt.color = c; lt.range = range; lt.intensity = intensity; lt.enabled = true;
            g.lightEnd[idx] = Time.time + life; g.lightLife[idx] = life; g.lightPeak[idx] = intensity;
        }

        void Update()
        {
            for (int i = 0; i < lights.Count; i++)
            {
                if (!lights[i] || !lights[i].enabled) continue;
                if (i >= maxHitLights || !hitLights) { lights[i].enabled = false; continue; }
                float k = (lightEnd[i] - Time.time) / Mathf.Max(lightLife[i], 1e-3f);
                if (k <= 0) { lights[i].enabled = false; continue; }
                lights[i].intensity = lightPeak[i] * k * k;
            }
        }
        static ParticleSystem.Particle[] cutBuf;
        /// <summary>Cuts the trail on hit: afterimages of this material keep at most maxRemain seconds of remaining life (so the trail doesn't keep pouring into the blast after the orb is gone).</summary>
        public static void CutTrail(Material mat, float maxRemain)
        {
            if (!mat || !I.trails.TryGetValue(mat, out var ps) || !ps) return;
            int n = ps.particleCount; if (n == 0) return;
            if (cutBuf == null || cutBuf.Length < n) cutBuf = new ParticleSystem.Particle[Mathf.NextPowerOfTwo(n)];
            n = ps.GetParticles(cutBuf, n);
            for (int i = 0; i < n; i++) cutBuf[i].remainingLifetime = Mathf.Min(cutBuf[i].remainingLifetime, maxRemain);
            ps.SetParticles(cutBuf, n);
        }

        public static void TrailPuff(Material mat, Vector3 p, float s, float l) { if (mat) I.Trail(mat).Emit(P(p, Vector3.zero, s, l, new Color(1, 1, 1, 0.6f), Random.Range(0, 360f)), 1); }

        /// <summary>Ground decal: placed on the raycast ground and fully eroded by the end of its life.</summary>
        public static void GroundDecal(Material mat, Vector3 p, float size, float life, Color tint)
        {
            if (!mat) return;
            p = GroundAt(p) + Vector3.up * 0.02f;
            I.Decal(mat).Emit(P(p, Vector3.zero, size, life, tint, Random.Range(0, 360f)), 1);
        }

        /// <summary>Impact flipbook (body). The push toward the camera is done in the shader via the material's _CamPush and updates live with the camera.</summary>
        public static void Body(Material mat, Vector3 p, Vector3 velocity, float size, float life)
        {
            if (!mat) return;
            I.Flipbook(mat).Emit(P(p, velocity, size, life, Color.white, Random.Range(-10f, 10f)), 1);
        }

        /// <summary>Camera-facing quad (the orb in flight).</summary>
        public static Transform Quad(string name, Material mat, Transform parent)
        {
            if (!quad)
            {
                quad = new Mesh { name = "ElementQuad" };
                quad.vertices = new[] { new Vector3(-0.5f, -0.5f, 0), new Vector3(0.5f, -0.5f, 0), new Vector3(-0.5f, 0.5f, 0), new Vector3(0.5f, 0.5f, 0) };
                quad.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 1), new Vector2(1, 1) };
                quad.colors = new[] { Color.white, Color.white, Color.white, Color.white };
                quad.triangles = new[] { 0, 2, 1, 1, 2, 3 };
                quad.RecalculateNormals(); quad.RecalculateBounds();
            }
            var go = new GameObject(name);
            go.transform.SetParent(parent, true);
            go.AddComponent<MeshFilter>().sharedMesh = quad;
            var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = mat;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return go.transform;
        }

        public static void Face(Transform t, float spinDeg)
        {
            var cam = Camera.main; if (!cam) return;
            t.rotation = Quaternion.LookRotation(t.position - cam.transform.position, cam.transform.up) * Quaternion.Euler(0, 0, spinDeg);
        }

        /// <summary>Takes a shell from the pool (water crown / wind band / lightning); call Release() when done. Hide it (flicker) with Visible; it won't be lent to anyone else.</summary>
        public static ShellPiece Shell(Material mat)
        {
            var g = I;
            foreach (var s in g.shellPool) if (s && !s.InUse) { s.Init(mat); return s; }
            var p = ShellPiece.Create(g.transform);
            g.shellPool.Add(p); p.Init(mat);
            return p;
        }
    }

    /// <summary>Pooled shell: its own Mesh + MaterialPropertyBlock (erosion, opacity).</summary>
    public class ShellPiece : MonoBehaviour
    {
        public Mesh mesh;
        /// <summary>Currently borrowed (regardless of visibility).</summary>
        public bool InUse { get; private set; }
        /// <summary>For flicker: toggles rendering only, without returning it to the pool.</summary>
        public bool Visible { get => mr.enabled; set => mr.enabled = value; }
        MeshRenderer mr;
        MaterialPropertyBlock mpb;
        static readonly int ErosionId = Shader.PropertyToID("_Erosion"), OpacityId = Shader.PropertyToID("_Opacity");

        public static ShellPiece Create(Transform parent)
        {
            var go = new GameObject("Shell"); go.transform.SetParent(parent, false);
            var p = go.AddComponent<ShellPiece>();
            p.mesh = new Mesh { name = "ShellMesh" }; p.mesh.MarkDynamic();
            go.AddComponent<MeshFilter>().sharedMesh = p.mesh;
            p.mr = go.AddComponent<MeshRenderer>();
            p.mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; p.mr.receiveShadows = false;
            p.mpb = new MaterialPropertyBlock();
            return p;
        }

        public void Init(Material mat)
        {
            mr.sharedMaterial = mat;
            transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity); transform.localScale = Vector3.one;
            Set(0, 1);
            InUse = true; mr.enabled = true;
            gameObject.SetActive(true);
        }

        public void Release() { InUse = false; gameObject.SetActive(false); }

        void OnDestroy() { if (mesh) Destroy(mesh); }   // the mesh is created per piece, not an asset: free it with the scene

        public void Set(float erosion, float opacity)
        {
            mpb.SetFloat(ErosionId, erosion); mpb.SetFloat(OpacityId, opacity);
            mr.SetPropertyBlock(mpb);
        }

        public void CopyMesh(Mesh src)
        {
            mesh.Clear();
            mesh.vertices = src.vertices; mesh.uv = src.uv; mesh.uv2 = src.uv2; mesh.colors = src.colors;
            mesh.normals = src.normals; mesh.triangles = src.triangles; mesh.RecalculateBounds();
        }
    }
}
