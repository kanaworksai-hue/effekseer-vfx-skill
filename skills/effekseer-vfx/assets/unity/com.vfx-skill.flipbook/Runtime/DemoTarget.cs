using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// A hit reaction good enough to judge effects on: spring knockback, squash and stretch, a tilt away from the hit,
    /// a short flash in the element's colour, and being lifted and dropped by eruption skills (ElementHit.lift).
    /// Strength is ElementHit.power × the profile's knockback; ticks (power &lt; 1) only twitch and flash.
    /// Put it on the target's root; `visual` is the child that moves (defaults to the first child).
    /// Real games replace this with their own IElementHitReceiver (stagger, damage numbers, elemental reactions).
    /// </summary>
    public class DemoTarget : MonoBehaviour, IElementHitReceiver
    {
        public Transform visual;
        public float floatAmp = 0.0f, floatFreq = 1.6f;
        [Range(0, 1), Tooltip("How much of the element colour the body takes on a hit (white targets: keep it low)")] public float flashTint = 0.18f;

        float squash, squashVel, tilt, tiltVel, flash;
        Vector3 push, pushVel;
        float air, airVel, liftTo, liftUntil, fallG = 22f;       // lifted by a column: held at liftTo, then dropped with fallG
        Vector3 shift, shiftTo, shiftVel;                       // moved over the column while lifted, eased back after landing
        Color flashColor = Color.white;
        Vector3 baseLocal;
        Renderer[] rends;
        MaterialPropertyBlock mpb;
        static readonly int BaseId = Shader.PropertyToID("_BaseColor"), EmitId = Shader.PropertyToID("_EmissionColor");

        void Start()
        {
            if (!visual) visual = transform.childCount > 0 ? transform.GetChild(0) : transform;
            baseLocal = visual.localPosition;
            rends = visual.GetComponentsInChildren<Renderer>();
            mpb = new MaterialPropertyBlock();
        }

        public void OnElementHit(in ElementHit hit)
        {
            float k = hit.power * (hit.element ? hit.element.knockback : 1f);
            Vector3 d = hit.direction; d.y = Mathf.Max(d.y, 0);
            if (hit.lift > 0)
            {
                liftTo = Mathf.Max(liftTo, hit.lift); liftUntil = Mathf.Max(liftUntil, Time.time + hit.liftTime);
                shiftTo = transform.InverseTransformVector(hit.liftShift); if (hit.liftGravity > 0) fallG = hit.liftGravity;
            }
            else if (d.y > 0.7f) airVel = Mathf.Max(airVel, 2.3f * Mathf.Sqrt(Mathf.Max(k, 0f)));   // other upward hits: a small hop
            else pushVel += transform.InverseTransformDirection(d.normalized) * 4.5f * k;
            squashVel -= 6f * k;
            tiltVel += 300f * k * Mathf.Sign(Vector3.Dot(hit.direction, transform.forward) + 0.001f);
            flash = Mathf.Max(flash, Mathf.Lerp(0.5f, 1f, hit.power));
            flashColor = hit.element ? hit.element.theme : Color.white;
        }

        void Update()
        {
            if (!visual) return;
            float dt = Time.deltaTime;
            squashVel += (-180f * squash - 12f * squashVel) * dt; squash += squashVel * dt;
            tiltVel += (-120f * tilt - 9f * tiltVel) * dt; tilt += tiltVel * dt;
            pushVel += (-90f * push - 11f * pushVel) * dt; push += pushVel * dt;
            flash = Mathf.Max(0, flash - dt * 7f);
            if (Time.time < liftUntil)
            {
                air = Mathf.SmoothDamp(air, liftTo + 0.06f * Mathf.Sin(Time.time * 9f), ref airVel, 0.08f);
            }
            else if (air > 0 || airVel > 0)
            {
                liftTo = 0;
                airVel = Mathf.Min(airVel, 0f) - fallG * dt; air += airVel * dt;
                if (air <= 0) { air = 0; airVel = 0; squashVel -= 4f; }
            }
            if (Time.time < liftUntil || air > 0) shift = Vector3.SmoothDamp(shift, shiftTo, ref shiftVel, 0.12f);
            else { shiftTo = Vector3.zero; shift = Vector3.SmoothDamp(shift, Vector3.zero, ref shiftVel, 0.35f); }
            float s = Mathf.Clamp(squash, -0.28f, 0.3f);
            visual.localScale = new Vector3(1 - s * 0.6f, 1 + s, 1 - s * 0.6f);
            visual.localRotation = Quaternion.Euler(Mathf.Clamp(tilt, -30, 30), 0, 0);
            visual.localPosition = baseLocal + shift + Vector3.ClampMagnitude(push, 0.6f) + Vector3.up * (air + Mathf.Sin(Time.time * floatFreq * Mathf.PI * 2) * floatAmp);
            if (rends == null) return;
            Color baseC = Color.Lerp(Color.white, flashColor * 1.2f, flash * flashTint), emit = flashColor * flash * 0.2f;
            foreach (var r in rends)
            {
                if (!r) continue;
                r.GetPropertyBlock(mpb);
                mpb.SetColor(BaseId, baseC); mpb.SetColor(EmitId, emit);
                r.SetPropertyBlock(mpb);
            }
        }
    }
}
