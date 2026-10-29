using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// Base of a skill component. Put it on the caster (or a cast point); transform.forward is the cast direction.
    /// Play() casts once at `target` (or at `fallbackTarget` when there is none). Spawned objects are cleaned up when the
    /// skill finishes or the component is disabled.
    /// </summary>
    public abstract class SkillBase : MonoBehaviour
    {
        [Header("Target")]
        public Transform target;
        [Tooltip("Aim point relative to the target's pivot (the centre of its body)")]
        public Vector3 targetOffset = new Vector3(0, 1.0f, 0);
        [Tooltip("Aim point relative to the caster when there is no target")]
        public Vector3 fallbackTarget = new Vector3(0, 1.0f, 7f);
        [Tooltip("Casting hand relative to the caster (used when no CastDriver tracks a real hand bone)")]
        public Vector3 handOffset = new Vector3(0.0f, 1.25f, 0.55f);
        public bool playOnStart;

        public bool IsPlaying { get; protected set; }
        public event Action Finished;

        protected readonly List<UnityEngine.Object> spawned = new List<UnityEngine.Object>();

        protected Vector3 TargetPos => target ? target.position + targetOffset : transform.TransformPoint(fallbackTarget);
        protected Vector3 HandPos => transform.TransformPoint(handOffset);

        void Start() { if (playOnStart) Play(); }

        public void Play(Transform newTarget)
        {
            target = newTarget;
            Play();
        }

        public virtual void Play()
        {
            StopAllCoroutines();
            Cleanup();
            StartCoroutine(Runner());
        }

        IEnumerator Runner()
        {
            IsPlaying = true;
            yield return Run();
            Cleanup();
            IsPlaying = false;
            Finished?.Invoke();
        }

        protected abstract IEnumerator Run();

        protected void RaiseFinished() => Finished?.Invoke();

        protected virtual void Cleanup()
        {
            foreach (var o in spawned) if (o) Destroy(o);
            spawned.Clear();
        }

        protected virtual void OnDisable() { Cleanup(); IsPlaying = false; }

        public static float EaseOutBack(float x, float s = 1.70158f) { x -= 1; return x * x * ((s + 1) * x + s) + 1; }
        public static float EaseOutCubic(float x) { x = 1 - x; return 1 - x * x * x; }
        public static float EaseInCubic(float x) => x * x * x;
        public static float EaseInOut(float x) => x * x * (3 - 2 * x);
    }
}
