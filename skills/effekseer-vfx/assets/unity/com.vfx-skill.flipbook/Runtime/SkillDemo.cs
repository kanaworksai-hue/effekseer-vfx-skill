using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// Demo driver for the scene built by "VFX Skill/3. Build demo scene": casts the listed skills in turn, or the one
    /// picked with the on-screen buttons / number keys. Not meant for games — call ElementSkill.Play() from your own code.
    /// </summary>
    public class SkillDemo : MonoBehaviour
    {
        public List<ElementSkill> skills = new List<ElementSkill>();
        [Tooltip("Cast every skill in turn, waiting this long after each one finishes (0 = only on button / key)"), Min(0f)]
        public float autoInterval = 0.8f;
        [Range(0.1f, 1f), Tooltip("Time scale while playing (slow motion to judge timing)")] public float timeScale = 1f;

        int next;
        ElementSkill current;

        IEnumerator Start()
        {
            if (autoInterval <= 0) yield break;
            while (true)
            {
                yield return new WaitForSeconds(autoInterval);
                if (autoInterval <= 0) yield break;   // a button was pressed: manual from now on
                if (skills.Count == 0) continue;
                Cast(next);
                next = (next + 1) % skills.Count;
                while (current && current.IsPlaying) yield return null;
            }
        }

        void Update()
        {
            GameTime.BaseScale = timeScale;
#if ENABLE_LEGACY_INPUT_MANAGER
            for (int i = 0; i < Mathf.Min(skills.Count, 9); i++)
                if (Input.GetKeyDown(KeyCode.Alpha1 + i)) { autoInterval = 0; Cast(i); }
#endif
        }

        public void Cast(int i)
        {
            if (i < 0 || i >= skills.Count || !skills[i] || !skills[i].profile) return;
            current = skills[i];
            current.Play();
        }

        void OnGUI()
        {
            GUILayout.BeginArea(new Rect(12, 12, 220, 40 + 30 * skills.Count));
            for (int i = 0; i < skills.Count; i++)
            {
                var s = skills[i];
                if (!s || !s.profile) continue;
                if (GUILayout.Button($"{i + 1}. {s.profile.displayName} ({s.profile.delivery})")) { autoInterval = 0; Cast(i); }
            }
            GUILayout.EndArea();
        }
    }
}
