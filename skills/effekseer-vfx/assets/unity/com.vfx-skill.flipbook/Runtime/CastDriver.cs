using System;
using System.Collections;
using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// Cast animation adapter: Legacy Animation (e.g. a GLB imported via glTFast) or Animator (Mecanim).
    /// Release moment:
    ///   · Legacy: if the cast clip has an Animation Event with function name "Release", its time is used, otherwise releaseTime; converted to seconds via castStart / speed.
    ///   · Animator: the cast state's clip must have a "Release" event. The skill waits for it (ReleasedSince) and falls back to releaseTime / speed only if it never arrives.
    ///     The Animator's overall speed is changed only during the cast and restored after release.
    /// </summary>
    public class CastDriver : MonoBehaviour
    {
        [Header("Legacy Animation (GLB)")]
        public Animation legacy;
        public string castClip = "cast_a_spell";
        public string idleClip = "idle";
        [Header("Animator (Mecanim)")]
        public Animator animator;
        public string castTrigger = "Cast";
        [Header("Timing")]
        [Tooltip("Release moment in the cast clip (seconds at clip speed 1); a Release event on the clip takes precedence")] public float releaseTime = 2.5f;
        [Tooltip("Legacy: start playing the clip from this time (skips the idle stance at the start)")] public float castStart = 0.6f;
        public float speed = 1.8f;
        [Tooltip("Hand bone the orb is released from (empty = a fixed point in front of the caster)")] public Transform hand;
        public Vector3 handOffset = new Vector3(0, 0, 0.1f);

        /// <summary>Called when the "Release" animation event fires.</summary>
        public event Action Released;
        int releaseCount;
        float savedAnimatorSpeed = 1f;
        Coroutine restore;

        public Vector3 HandPosition => hand ? hand.position + transform.TransformDirection(handOffset) : transform.TransformPoint(new Vector3(0, 1.1f, 0.5f));
        public bool UsesReleaseEvent => !UsesLegacy && animator;
        bool UsesLegacy => legacy && legacy[castClip] != null;
        /// <summary>Current Release count; a skill stores it, and once ReleasedSince(n) is true the release has happened.</summary>
        public int ReleaseStamp => releaseCount;
        public bool ReleasedSince(int stamp) => releaseCount > stamp;

        /// <summary>Starts the cast and returns the expected seconds until release (for Animator this is the fallback timeout).</summary>
        public float Cast(float speedScale = 1f)
        {
            float spd = speed * Mathf.Max(0.1f, speedScale);
            if (UsesLegacy)
            {
                var st = legacy[castClip];
                st.speed = spd; st.wrapMode = WrapMode.Once;
                legacy.CrossFade(castClip, 0.12f); st.time = castStart;
                if (legacy[idleClip] != null) legacy.CrossFadeQueued(idleClip, 0.35f, QueueMode.CompleteOthers);
                return Mathf.Max(0.15f, (EventTime(st.clip) - castStart) / spd);
            }
            if (animator)
            {
                if (restore == null) savedAnimatorSpeed = animator.speed;
                else StopCoroutine(restore);
                float scale = spd / Mathf.Max(speed, 1e-3f);
                animator.speed = savedAnimatorSpeed * scale;
                animator.SetTrigger(castTrigger);
                float delay = Mathf.Max(0.15f, releaseTime / spd);
                restore = StartCoroutine(RestoreSpeed(delay + 0.6f));
                return delay;
            }
            return 0.4f;
        }

        IEnumerator RestoreSpeed(float after)
        {
            yield return new WaitForSeconds(after);
            if (animator) animator.speed = savedAnimatorSpeed;
            restore = null;
        }

        void OnDisable() { if (restore != null && animator) animator.speed = savedAnimatorSpeed; restore = null; }

        float EventTime(AnimationClip clip)
        {
            foreach (var e in clip.events) if (e.functionName == "Release") return e.time;
            return releaseTime;
        }

        // Animation Event receiver (called by both Legacy and Animator)
        public void Release() { releaseCount++; Released?.Invoke(); }
    }
}
