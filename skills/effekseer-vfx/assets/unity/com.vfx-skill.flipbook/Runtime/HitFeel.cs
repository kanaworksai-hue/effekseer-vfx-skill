using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace VfxSkill
{
    /// <summary>
    /// Layered time scale: Time.timeScale = (Paused ? 0 : BaseScale) × (in hit stop ? 0.03 : 1).
    /// For game pause / slow motion, set GameTime.Paused / GameTime.BaseScale instead of writing Time.timeScale directly.
    /// Compatibility with legacy code that bypasses this: when an external write is detected —
    ///   writing 0 → treated as pause; writing back the frozen value (the 0.03 that old pause code saved mid-freeze and restores on unpause) → treated as unpause, base scale unchanged;
    ///   any other value → treated as the new base scale. So pausing in the middle of a hit stop never leaves the game stuck at 3% speed.
    /// </summary>
    public static class GameTime
    {
        static bool paused; static float baseScale = 1f; static bool freezing;
        static float lastWritten = 1f, lastFreezeRealTime = -100f;
        public const float FrozenScale = 0.03f;
        /// <summary>Compatibility with legacy pause code that writes Time.timeScale directly (see class comment). Turn this off if your project uses 3% slow motion itself.</summary>
        public static bool AbsorbLegacyWrites = true;

        public static bool Paused { get { Sync(); return paused; } set { Sync(); paused = value; Apply(); } }
        public static float BaseScale { get { Sync(); return baseScale; } set { Sync(); baseScale = Mathf.Max(0, value); Apply(); } }
        /// <summary>Hit stop flag (driven by HitFeel; tests may set it directly).</summary>
        public static bool Freezing
        {
            get => freezing;
            set { Sync(); if (freezing || value) lastFreezeRealTime = Time.realtimeSinceStartup; freezing = value; Apply(); }
        }

        /// <summary>Absorbs external writes to Time.timeScale.</summary>
        public static void Sync()
        {
            float v = Time.timeScale;
            if (Mathf.Approximately(v, lastWritten)) return;
            bool recentFreeze = freezing || Time.realtimeSinceStartup - lastFreezeRealTime < 2f;
            if (v <= 0f) paused = true;
            else if (AbsorbLegacyWrites && recentFreeze && (Mathf.Approximately(v, baseScale * FrozenScale) || Mathf.Approximately(v, FrozenScale)))
                paused = false;                                                  // old pause code restored the value it saved during the freeze
            else { paused = false; baseScale = v; }
            Apply();                                                            // write the correct value back immediately (e.g. old code restored 0.03 after the freeze had already ended)
        }

        static void Apply()
        {
            float v = paused ? 0f : baseScale * (freezing ? FrozenScale : 1f);
            Time.timeScale = v; lastWritten = v;
        }

        /// <summary>Resets to defaults (called automatically on entering Play Mode, so static state doesn't leak into the next run when domain reload is disabled).</summary>
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        public static void ResetAll() { paused = false; baseScale = 1f; freezing = false; lastFreezeRealTime = -100f; Apply(); }
    }

    /// <summary>
    /// Hit-feel service: hit stop + camera shake. A single global instance that persists across scenes and doesn't depend on any particular camera.
    /// Hit stop: timed in real seconds (recording frame interval when recording offline); total freeze within any sliding 1 s window is capped at maxFreezePerSecond, so rapid hits can't keep the game frozen;
    ///       it neither counts down nor resumes while paused. Time scale is written only through GameTime.
    /// Shake: an offset is applied before the camera renders and undone after, without touching the camera Transform, so it doesn't fight Cinemachine or other camera controllers; only the main Game camera shakes (not UI / render-texture cameras).
    /// </summary>
    public class HitFeel : MonoBehaviour
    {
        static HitFeel _inst;
        static HitFeel I
        {
            get
            {
                if (_inst) return _inst;
                var go = new GameObject("[HitFeel]") { hideFlags = HideFlags.HideAndDontSave };
                if (Application.isPlaying) DontDestroyOnLoad(go);
                _inst = go.AddComponent<HitFeel>();
                return _inst;
            }
        }

        /// <summary>Maximum total freeze within any 1 s (s).</summary>
        public static float maxFreezePerSecond = 0.15f;

        float freezeLeft, clock;
        readonly Queue<(float t, float d)> history = new Queue<(float, float)>();   // freeze amount per frame in real time (sliding window)
        float windowSum;
        float shakeAmp, shakeDur, shakeT;
        Camera shakenCam; Vector3 shakeOffset;

        /// <summary>Hit stop for seconds (real time).</summary>
        public static void Stop(float seconds)
        {
            if (seconds <= 0) return;
            var h = I;
            if (h.Budget <= 0) return;                                        // budget used up: this hit doesn't freeze and its duration isn't recorded
            h.freezeLeft = Mathf.Max(h.freezeLeft, seconds);                // new hits don't stack; they only extend to the longer one
            if (!GameTime.Freezing) GameTime.Freezing = true;
        }

        public static void Shake(float amplitude, float duration)
        {
            var h = I;
            if (amplitude < h.shakeAmp * (1 - h.shakeT / Mathf.Max(h.shakeDur, 1e-3f))) return;   // don't interrupt a stronger shake
            h.shakeAmp = amplitude; h.shakeDur = duration; h.shakeT = 0;
        }

        /// <summary>Ends hit stop and shake immediately (call on camera cuts and scene changes).</summary>
        public static void ResetAll()
        {
            if (!_inst) return;
            _inst.freezeLeft = 0; GameTime.Freezing = false;
            _inst.shakeT = _inst.shakeDur;
        }

        float Budget => maxFreezePerSecond - windowSum;
        static float RealDelta => Time.captureDeltaTime > 0 ? Time.captureDeltaTime : Time.unscaledDeltaTime;

        void Update()
        {
            GameTime.Sync();
            float d = RealDelta;
            clock += d;
            while (history.Count > 0 && history.Peek().t < clock - 1f) windowSum -= history.Dequeue().d;
            if (GameTime.Freezing)
            {
                if (GameTime.Paused) return;                                   // paused: don't count down
                freezeLeft -= d;
                history.Enqueue((clock, d)); windowSum += d;
                if (freezeLeft <= 0 || Budget <= 0) { freezeLeft = 0; GameTime.Freezing = false; }
            }
            if (shakeT < shakeDur) shakeT += d;
        }

        void OnEnable()
        {
            RenderPipelineManager.beginCameraRendering += Begin;
            RenderPipelineManager.endCameraRendering += End;
        }

        void OnDisable()
        {
            RenderPipelineManager.beginCameraRendering -= Begin;
            RenderPipelineManager.endCameraRendering -= End;
            if (GameTime.Freezing) GameTime.Freezing = false;
        }

        void Begin(ScriptableRenderContext ctx, Camera cam)
        {
            if (shakeT >= shakeDur || cam.cameraType != CameraType.Game || cam.targetTexture || cam != Camera.main) return;
            float k = 1 - shakeT / shakeDur;
            shakeOffset = (cam.transform.right * Mathf.Sin(shakeT * 90) + cam.transform.up * Mathf.Cos(shakeT * 77)) * shakeAmp * k * k;
            cam.transform.position += shakeOffset; shakenCam = cam;
        }

        void End(ScriptableRenderContext ctx, Camera cam)
        {
            if (cam != shakenCam) return;
            cam.transform.position -= shakeOffset; shakenCam = null; shakeOffset = Vector3.zero;
        }
    }
}
