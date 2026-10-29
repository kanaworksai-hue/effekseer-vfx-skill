using UnityEngine;

namespace VfxSkill
{
    public enum DeliveryType { Projectile, Instant, Eruption }
    public enum TrailStyle { None, Droplets, EmberSmoke, ToxicDrip, Helix }
    public enum ImpactExtra { None, CrownSplash, Fireball, Splat, Funnel, Arcs }
    public enum LingerStyle { None, Drip, Smolder, Pool, Swirl, Static }
    /// <summary>Element-specific shape at the moment of contact (so the five elements don't share one generic 'hit stamp').</summary>
    public enum ContactAccent { None, Star, FoamRing, AirRing, ArcBurst }

    /// <summary>
    /// All data for one element skill: textures/materials, trajectory, trail, impact, linger, hit feel.
    /// Adding an element = creating a new ElementProfile asset (Create → VfxSkill → Element Profile),
    /// picking existing Trail/Impact/Linger styles and filling in values; code is needed only for a brand-new kind of motion (add a style).
    /// </summary>
    [CreateAssetMenu(menuName = "VfxSkill/Element Profile", fileName = "EP_NewElement")]
    public class ElementProfile : ScriptableObject
    {
        [Header("Identity")]
        public string displayName = "Element";
        [Tooltip("Main colour (sparks, flashes, target hit tint)")] public Color theme = Color.white;
        [Tooltip("Dark rim colour (ink rim, residue)")] public Color dark = Color.black;

        [Header("Materials")]
        public Material orb;
        public Material impact;
        public Material decal;
        [Tooltip("StylizedShell material for the extra impact shells (water crown / wind bands / lightning strip)")] public Material shell;
        [Tooltip("Lightning glow (soft strip)")] public Material glow;
        [Tooltip("Contact burst: star (StylizedShell)")] public Material star;
        [Tooltip("Contact burst: shock ring (StylizedShell)")] public Material ring;
        [Tooltip("Optional: this element's smoke (empty = shared neutral grey smoke)")] public Material smoke;
        [Tooltip("Optional: this element's droplets / drips / bubbles (empty = shared ones)")] public Material matter;

        [Header("Charge & delivery")]
        public DeliveryType delivery = DeliveryType.Projectile;
        [Tooltip("Cast animation speed multiplier (rhythm differs: lightning fast, poison slow)"), Min(0.1f)] public float castSpeed = 1f;
        [Tooltip("Orb size in the palm while charging (m)")] public float chargeSize = 0.32f;
        [Tooltip("Orb size in flight (m)")] public float flightSize = 0.6f;
        [Tooltip("m/s"), Min(0.5f)] public float speed = 10f;
        [Tooltip("Gravity multiplier")] public float gravityScale = 0.45f;
        [Tooltip("Extra lift at the apex of the arc (m)")] public float lift = 0.5f;
        public float spinDegPerSec = 600f;

        [Header("Eruption (delivery = Eruption: a column bursting up beneath the target)")]
        [Tooltip("Optional: column front layer (translucent, drawn over the target). Empty = a single column layer drawn behind the target (face stays visible). The column itself uses impact")] public Material columnFront;
        [Tooltip("Column height (m)")] public float columnHeight = 3.4f;
        [Tooltip("How high the target is lifted off the ground (m); held there until the column top collapses")] public float columnLift = 1.4f;
        [Tooltip("Gravity for the target's fall after the lift (m/s², cartoon gravity is faster than the real 9.8): the landing crown is timed from it"), Min(1f)] public float columnFallGravity = 22f;
        [Tooltip("How far behind the target the column root sits (m, along the ground, away from the camera at the moment of eruption): the column draws behind the target yet still grows out of the ground (pushing it back in the material does not work: from a high angle the root would float above the ground)"), Range(0f, 3f)] public float columnBehind = 0.6f;
        [Tooltip("Canopy rim height (fraction of column height): rain falls from here when it collapses"), Range(0f, 1f)] public float columnRim = 0.5f;
        [Tooltip("Distance from the column root to the bottom of its atlas cell (fraction of column height, gutter included): the column is sunk into the ground by this much so the root sits on the ground (otherwise it floats, leaving a strip of dry ground between it and the puddle)"), Range(0f, 0.5f)] public float columnRootInset = 0f;
        [Tooltip("Atlas cell width / height")] public float columnAspect = 0.545f;
        [Tooltip("Total column duration (s): surge up → hold → collapse → ground splash"), Min(0.2f)] public float columnLife = 2.4f;
        [Tooltip("Column atlas timing: x = life fraction 0–1, y = frame progress 0–1 (fast surge, hold, collapse). Retune this curve to the new source video when swapping the atlas")]
        public AnimationCurve columnFrames = LinearCurve(0, 0, 0.1f, 0.143f, 0.4f, 0.5f, 0.54f, 0.73f, 1, 1);
        [Tooltip("Life fraction where the lift ends and the rain starts: slightly before the hold segment of columnFrames ends (0.4), so the target starts falling and the column top collapses right after instead of hanging in the air"), Range(0.05f, 0.95f)] public float columnHoldEnd = 0.34f;
        [Tooltip("Warning time after the orb dives into the ground and before the column erupts (s): ground bubbles, a water ring spreads"), Min(0f)] public float warnTime = 0.35f;

        [Header("Trail (emitted by distance, frame-rate independent)")]
        public TrailStyle trail = TrailStyle.Droplets;
        [Tooltip("Distance between trail emissions (m)"), Min(0.01f)] public float trailSpacing = 0.06f;
        [Tooltip("Cut this trail's afterimages on hit (fire: once the orb is gone the trail must not keep pouring into the blast). Note: cut per material, so with rapid casts of the same element it also cuts the trail of a shot still in flight")] public bool cutTrailOnHit = false;

        [Header("Aim")]
        [Tooltip("Hit point height offset (m): different elements hit different parts of the target")] public float aimHeight = 0f;
        [Tooltip("Drops onto the target from above (poison's high lob): the hit point is on top of the target")] public bool fromAbove = false;

        [Header("Impact")]
        public ImpactExtra extra = ImpactExtra.None;
        [Tooltip("Impact flipbook size (m). Keep it under 1.4x the target, or it covers the hit reaction")] public float impactSize = 2.2f;
        [Tooltip("Impact flipbook duration (s)")] public float impactLife = 1.4f;
        [Tooltip("Upward drift speed of the whole impact flipbook (m/s); fire smoke should rise")] public float impactRise = 0f;
        [Tooltip("Flipbook centre offset from the hit point (target-local: x right, y up, z toward the caster)")] public Vector3 impactOffset = Vector3.zero;
        [Tooltip("Element-specific contact accent: water = foam ring opening along the hit surface, wind = pressure ring around the body, lightning = short radiating arcs, fire / poison = small star")] public ContactAccent contact = ContactAccent.Star;
        [Tooltip("Contact flash size (m); lasts only 2 frames")] public float flashSize = 0.9f;
        public int sparkCount = 14;

        [Tooltip("Hit light: theme-coloured point light intensity / range")] public float lightIntensity = 6f;
        public float lightRange = 4f;

        [Header("Ground")]
        public float decalSize = 1.6f;
        [Tooltip("Decal colour multiplier (darken fire scorch marks)")] public Color decalTint = Color.white;
        [Tooltip("Decal life (s); the skill is not finished until it has fully faded"), Min(0f)] public float decalLife = 1.8f;

        [Header("Linger")]
        public LingerStyle linger = LingerStyle.None;
        [Min(0f)] public float lingerTime = 1.2f;

        [Header("Hit feel")]
        [Tooltip("Hit stop (real seconds, frame-rate independent)"), Min(0f)] public float hitStop = 0.08f;
        public float shake = 0.12f;
        public float shakeTime = 0.25f;
        [Tooltip("Hit strength (knockback / squash)"), Min(0f)] public float knockback = 1f;
        [Tooltip(">0: hold the target's hit reaction for at least this long (s), e.g. fire that keeps burning around the head should keep the reaction until it is gone; 0 = the target's own default duration"), Min(0f)] public float reactTime = 0f;
        [Tooltip("Extra damage-over-time ticks (poison, wind)")] public int ticks = 0;
        [Min(0.05f)] public float tickInterval = 0.35f;

        /// <summary>Polyline curve (each segment's tangents = its slope): frame progress advances at a steady rate without stalling at keys. Arguments are (time, value) pairs.</summary>
        public static AnimationCurve LinearCurve(params float[] tv)
        {
            int n = tv.Length / 2; var keys = new Keyframe[n];
            for (int i = 0; i < n; i++)
            {
                float inT = i > 0 ? (tv[2 * i + 1] - tv[2 * i - 1]) / Mathf.Max(1e-5f, tv[2 * i] - tv[2 * i - 2]) : 0;
                float outT = i < n - 1 ? (tv[2 * i + 3] - tv[2 * i + 1]) / Mathf.Max(1e-5f, tv[2 * i + 2] - tv[2 * i]) : 0;
                keys[i] = new Keyframe(tv[2 * i], tv[2 * i + 1], inT, outT);
            }
            return new AnimationCurve(keys);
        }

        /// <summary>Checks that the materials required by the chosen styles are assigned and values are in safe ranges; returns a list of problems (empty = OK). Runtime clamps again where the values are used.</summary>
        public string Validate()
        {
            var sb = new System.Text.StringBuilder();
            void Need(Object o, string what) { if (!o) sb.Append(what).Append("; "); }
            // value ranges: 0 or negatives would make flight / trails loop forever
            void Range(float v, float min, string what) { if (!(v >= min)) sb.Append(what).Append(" < ").Append(min).Append("; "); }
            Need(decal, "decal"); Need(star, "star (contact core)");
            if (contact == ContactAccent.FoamRing || contact == ContactAccent.AirRing) Need(ring, "ring");
            if (delivery == DeliveryType.Projectile) Need(orb, "orb");
            if (delivery == DeliveryType.Instant) { Need(orb, "orb (palm charge)"); Need(shell, "shell (bolt)"); }
            if (delivery == DeliveryType.Eruption)
            {
                Need(orb, "orb (dives into the ground)"); Need(impact, "impact (column)");
                Range(columnHeight, 0.1f, "columnHeight"); Range(columnAspect, 0.05f, "columnAspect"); Range(columnLife, 0.2f, "columnLife");
                Range(warnTime, 0f, "warnTime"); Range(columnLift, 0f, "columnLift"); Range(columnFallGravity, 1f, "columnFallGravity"); Range(columnBehind, 0f, "columnBehind"); Range(columnRim, 0f, "columnRim"); Range(speed, 0.5f, "speed"); Range(trailSpacing, 0.01f, "trailSpacing");
                if (columnFrames == null || columnFrames.length < 2) sb.Append("columnFrames (needs ≥2 keys); ");
            }
            if (extra == ImpactExtra.CrownSplash || extra == ImpactExtra.Funnel || extra == ImpactExtra.Arcs || contact == ContactAccent.ArcBurst) Need(shell, "shell (" + extra + ")");
            if (impactLife > 0) Need(impact, "impact");
            if (delivery == DeliveryType.Projectile) { Range(speed, 0.5f, "speed"); Range(trailSpacing, 0.01f, "trailSpacing"); }
            Range(castSpeed, 0.1f, "castSpeed"); Range(tickInterval, 0.05f, "tickInterval"); Range(knockback, 0f, "knockback");
            return sb.ToString();
        }

        void OnValidate() { var e = Validate(); if (e.Length > 0) Debug.LogWarning($"[ElementProfile] {name}: {e}", this); }
    }

    /// <summary>Full info for one element hit (replaces string-based SendMessage).</summary>
    public struct ElementHit
    {
        public ElementProfile element;
        public Vector3 point, direction;
        [Tooltip("1 = main hit; <1 = tick / follow-up hit")] public float power;
        [Tooltip(">0: lift the target this high off the ground (m), hold for liftTime seconds, then let it fall freely (the water column lifting the target); receivers that do not support it may ignore it")] public float lift;
        public float liftTime;
        [Tooltip("Horizontal shift of the target during the lift (world space): moves it over the column, then eases back after landing")] public Vector3 liftShift;
        [Tooltip("Fall gravity after the lift (m/s²): the skill times the landing splash with the same value, and the receiver falls with it")] public float liftGravity;
        public Component source;
    }

    /// <summary>Add to the target (or one of its parents) to receive element hits; use element to drive elemental reactions.</summary>
    public interface IElementHitReceiver
    {
        void OnElementHit(in ElementHit hit);
    }
}
