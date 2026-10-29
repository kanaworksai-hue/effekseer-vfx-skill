using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace VfxSkill.EditorTools
{
    /// <summary>
    /// What one skill is made of. The window edits one; agents write the same fields as JSON and run
    /// <c>Unity -batchmode -projectPath P -executeMethod VfxSkill.EditorTools.CreateElementSkill.FromCommandLine -vfxSpec spec.json -quit</c>.
    /// Texture fields are asset paths (Assets/VfxSkill/Flipbooks/...); enum fields are their names.
    /// </summary>
    [Serializable]
    public class SkillSpec
    {
        public string name = "Fire";
        public Color theme = new Color(1f, 0.5f, 0.12f), dark = new Color(0.32f, 0.05f, 0.03f);
        public string delivery = nameof(DeliveryType.Projectile);
        public string orb, body, decal;
        public Vector2Int orbGrid = new Vector2Int(1, 1), bodyGrid = new Vector2Int(8, 8);
        public int orbFps = 24;
        [Tooltip("Eruption only: stretch the column sideways so it reads wider than the target")] public float columnWidthScale = 1.6f;
        public string extra = nameof(ImpactExtra.None), contact = nameof(ContactAccent.Star), trail = nameof(TrailStyle.EmberSmoke), linger = nameof(LingerStyle.Smolder);

        public T Enum<T>(string value, T fallback) where T : struct => System.Enum.TryParse(value, true, out T v) ? v : fallback;
    }

    /// <summary>
    /// Turns processed sheets into a playable skill: materials (orb, body flipbook, ground decal, contact star / ring,
    /// mesh shell) plus an ElementProfile asset with defaults for the chosen delivery. Everything else is tuned on the
    /// profile afterwards; only a new kind of motion needs code (a new enum value in ElementProfile and its case in
    /// ElementSkill).
    /// </summary>
    public class CreateElementSkill : EditorWindow
    {
        SkillSpec spec = new SkillSpec();
        Texture2D orb, body, decal;

        [MenuItem("VFX Skill/2. Create element skill from flipbooks")]
        static void Open() => GetWindow<CreateElementSkill>("Create element skill").minSize = new Vector2(420, 520);

        void OnGUI()
        {
            EditorGUILayout.HelpBox("Sheets come from `vfx video-flipbook` + `vfx video-grade` (copy them in with `vfx unity-export`, " +
                                    "which also writes the grid). The body flipbook is the effect's main shape; the orb is what flies or charges.", MessageType.Info);
            spec.name = EditorGUILayout.TextField("Name", spec.name);
            spec.theme = EditorGUILayout.ColorField("Theme colour", spec.theme);
            spec.dark = EditorGUILayout.ColorField("Dark rim colour", spec.dark);
            var delivery = (DeliveryType)EditorGUILayout.EnumPopup(new GUIContent("Delivery", "Projectile flies; Instant connects (lightning); Eruption bursts from the ground under the target"),
                                                                   spec.Enum(spec.delivery, DeliveryType.Projectile));
            spec.delivery = delivery.ToString();
            EditorGUILayout.Space();
            orb = Field("Orb (projectile / palm charge)", orb, ref spec.orbGrid);
            spec.orbFps = EditorGUILayout.IntSlider(new GUIContent("Orb loop fps", "Used when the orb is a looping flipbook (grid > 1×1)"), spec.orbFps, 6, 60);
            body = Field(delivery == DeliveryType.Eruption ? "Column flipbook (body)" : "Impact flipbook (body)", body, ref spec.bodyGrid);
            if (delivery == DeliveryType.Eruption)
                spec.columnWidthScale = EditorGUILayout.Slider(new GUIContent("Column width scale", "Stretch the column sideways so it reads wider than the target"), spec.columnWidthScale, 1f, 2.5f);
            decal = (Texture2D)EditorGUILayout.ObjectField("Ground decal (optional)", decal, typeof(Texture2D), false);
            EditorGUILayout.Space();
            spec.extra = EditorGUILayout.EnumPopup("Impact extra (mesh shell)", spec.Enum(spec.extra, ImpactExtra.None)).ToString();
            spec.contact = EditorGUILayout.EnumPopup("Contact accent", spec.Enum(spec.contact, ContactAccent.Star)).ToString();
            spec.trail = EditorGUILayout.EnumPopup("Trail", spec.Enum(spec.trail, TrailStyle.EmberSmoke)).ToString();
            spec.linger = EditorGUILayout.EnumPopup("Linger", spec.Enum(spec.linger, LingerStyle.Smolder)).ToString();
            EditorGUILayout.Space();
            using (new EditorGUI.DisabledScope(!orb || !body || string.IsNullOrWhiteSpace(spec.name)))
                if (GUILayout.Button("Create materials + ElementProfile", GUILayout.Height(32)))
                {
                    spec.orb = AssetDatabase.GetAssetPath(orb); spec.body = AssetDatabase.GetAssetPath(body); spec.decal = decal ? AssetDatabase.GetAssetPath(decal) : null;
                    var p = Create(spec);
                    Selection.activeObject = p; EditorGUIUtility.PingObject(p);
                }
        }

        Texture2D Field(string label, Texture2D tex, ref Vector2Int grid)
        {
            var t = (Texture2D)EditorGUILayout.ObjectField(label, tex, typeof(Texture2D), false);
            if (t && t != tex && TryReadGrid(AssetDatabase.GetAssetPath(t), out var g)) grid = g;   // the sidecar from `vfx unity-export` knows the grid
            grid = EditorGUILayout.Vector2IntField("   grid (cols, rows)", grid);
            grid = Vector2Int.Max(grid, Vector2Int.one);
            return t;
        }

        static bool TryReadGrid(string texturePath, out Vector2Int grid)
        {
            grid = Vector2Int.one;
            string json = Path.ChangeExtension(texturePath, ".flipbook.json");
            if (string.IsNullOrEmpty(texturePath) || !File.Exists(json)) return false;
            var data = JsonUtility.FromJson<Sidecar>(File.ReadAllText(json));
            if (data?.grid == null || data.grid.Length < 2) return false;
            grid = new Vector2Int(data.grid[0], data.grid[1]);
            return true;
        }

        [Serializable] class Sidecar { public int[] grid; public int[] cell; public float bottom_inset; }

        static bool TryReadSidecar(string texturePath, out Sidecar data)
        {
            data = null;
            string json = string.IsNullOrEmpty(texturePath) ? null : Path.ChangeExtension(texturePath, ".flipbook.json");
            if (json == null || !File.Exists(json)) return false;
            data = JsonUtility.FromJson<Sidecar>(File.ReadAllText(json));
            return data != null;
        }

        /// <summary>Starting values for a new profile, from skills that passed review: a video body is already a full
        /// effect, so it stays smaller than the target (it must not hide the hit reaction), rises out of the face, and gets
        /// no hit-stop (hit-stop freezes the flipbook's first cells into a flat card).</summary>
        static void Defaults(ElementProfile p, DeliveryType delivery, SkillSpec spec)
        {
            p.flashSize = 1.1f; p.sparkCount = 16; p.decalSize = 1.8f; p.decalLife = 2.3f; p.lingerTime = 1.3f;
            if (delivery == DeliveryType.Eruption)
            {
                p.castSpeed = 1.1f; p.chargeSize = 0.3f; p.flightSize = 0.5f; p.speed = 12f; p.gravityScale = 0.5f; p.lift = 0.3f;
                p.columnHeight = 4f; p.columnLift = 1.5f; p.columnLife = 1.4f; p.columnBehind = 0.35f; p.columnHoldEnd = 0.5f;
                p.impactLife = 1f; p.lightIntensity = 3f; p.lightRange = 2.6f; p.decalSize = 2.4f; p.decalLife = 2.4f;
                p.hitStop = 0.06f; p.shake = 0.16f; p.shakeTime = 0.3f; p.knockback = 1.3f;
            }
            else
            {
                p.castSpeed = 0.85f; p.chargeSize = 0.4f; p.flightSize = 0.85f; p.speed = 14f; p.gravityScale = 0.02f; p.lift = 0f;
                p.spinDegPerSec = spec.orbGrid.x * spec.orbGrid.y > 1 ? 0f : 500f;   // a looping orb sheet already churns; spinning it turns flames upside down
                p.impactSize = 1.8f; p.impactLife = 2f; p.impactRise = 1.1f; p.impactOffset = new Vector3(0, 0.15f, -0.2f); p.aimHeight = -0.3f;
                p.lightIntensity = 6f; p.lightRange = 3.2f; p.reactTime = 1.5f;
                p.cutTrailOnHit = spec.Enum(spec.trail, TrailStyle.EmberSmoke) == TrailStyle.EmberSmoke;
                p.hitStop = 0f; p.shake = 0.24f; p.shakeTime = 0.32f; p.knockback = 1.1f;
            }
        }

        /// <summary>Batch entry point: reads the SkillSpec JSON named by -vfxSpec, creates the skill, then rebuilds the demo scene.</summary>
        public static void FromCommandLine()
        {
            var args = Environment.GetCommandLineArgs();
            int i = Array.IndexOf(args, "-vfxSpec");
            if (i < 0 || i + 1 >= args.Length) throw new ArgumentException("pass -vfxSpec <spec.json>");
            string specPath = Path.GetFullPath(args[i + 1]);   // relative paths resolve against the Unity project, not the caller
            if (!File.Exists(specPath)) throw new FileNotFoundException($"-vfxSpec {specPath} not found (pass an absolute path)");
            var spec = JsonUtility.FromJson<SkillSpec>(File.ReadAllText(specPath));
            var p = Create(spec);
            string issues = p.Validate();
            if (issues.Length > 0) throw new InvalidOperationException($"{AssetDatabase.GetAssetPath(p)}: {issues}");
            DemoSceneBuilder.Build();
        }

        public static ElementProfile Create(SkillSpec spec)
        {
            var orb = AssetDatabase.LoadAssetAtPath<Texture2D>(spec.orb);
            var body = AssetDatabase.LoadAssetAtPath<Texture2D>(spec.body);
            var decal = string.IsNullOrEmpty(spec.decal) ? null : AssetDatabase.LoadAssetAtPath<Texture2D>(spec.decal);
            if (!orb || !body) throw new FileNotFoundException($"orb '{spec.orb}' and body '{spec.body}' must be texture assets");
            if (TryReadGrid(spec.orb, out var og)) spec.orbGrid = og;
            if (TryReadGrid(spec.body, out var bg)) spec.bodyGrid = bg;
            if (!AssetDatabase.LoadAssetAtPath<Material>(VfxSkillSetup.SharedDir + "M_Spark.mat")) VfxSkillSetup.Setup();

            var delivery = spec.Enum(spec.delivery, DeliveryType.Projectile);
            Color theme = spec.theme, dark = spec.dark;
            string safe = string.Concat(spec.name.Split(Path.GetInvalidFileNameChars())).Replace(' ', '_');
            string dir = VfxSkillSetup.SkillDir + safe + "/";
            VfxSkillSetup.Folder(dir);
            var painted = Shader.Find("VfxSkill/PaintedFX");
            Color core = Color.Lerp(theme, Color.white, 0.85f);

            var orbMat = VfxSkillSetup.Painted(dir + $"M_{safe}_Orb.mat", painted, orb, 0.004f, 0.3f, false);
            // a looping orb sheet animates itself; a single image must switch it off again (the material may be re-created)
            orbMat.SetVector("_Flip", spec.orbGrid.x * spec.orbGrid.y > 1 ? new Vector4(spec.orbGrid.x, spec.orbGrid.y, spec.orbFps, 0) : new Vector4(1, 1, 0, 0));
            if (spec.orbGrid.x * spec.orbGrid.y > 1) orbMat.SetFloat("_Distort", 0.002f);

            bool eruption = delivery == DeliveryType.Eruption;
            var bodyMat = VfxSkillSetup.Painted(dir + $"M_{safe}_Body.mat", painted, body, 0f, 0.2f, true);
            bodyMat.SetVector("_Tiles", new Vector4(spec.bodyGrid.x, spec.bodyGrid.y, 0, 0));
            bodyMat.SetFloat("_ErodeNoise", 0.25f);
            bodyMat.SetFloat("_CamPush", eruption ? 0f : 0.55f);   // impacts float to the target's surface; a column stands on the ground behind it
            if (!eruption) bodyMat.SetVector("_Grow", new Vector4(0.3f, 0.07f, 0, 0));   // video bursts start full size: snap up from 30 %

            var decalMat = VfxSkillSetup.Painted(dir + $"M_{safe}_Decal.mat", painted, decal ? decal : VfxSkillSetup.Tex("T_Decal"), 0.002f, 0.35f, false);
            decalMat.SetFloat("_ErodeNoise", 0.6f); decalMat.SetFloat("_AlphaBoost", 1.2f); VfxSkillSetup.Soft(decalMat, 0);
            if (!decal) decalMat.SetColor("_Tint", Color.Lerp(dark, Color.black, 0.3f) * 1.4f);
            EditorUtility.SetDirty(orbMat); EditorUtility.SetDirty(bodyMat); EditorUtility.SetDirty(decalMat);   // edited after Mat() saved them

            var extra = spec.Enum(spec.extra, ImpactExtra.None);
            if (eruption && extra == ImpactExtra.None) extra = ImpactExtra.CrownSplash;
            var star = VfxSkillSetup.Shell(dir + $"M_{safe}_Star.mat", "T_MaskHitStar", Color.white, theme, dark);
            var ring = VfxSkillSetup.Shell(dir + $"M_{safe}_Ring.mat", "T_MaskRing", Color.white, Color.Lerp(theme, Color.white, 0.6f), theme, 0.08f, 0.06f, 1.01f, 0.35f);
            bool funnel = extra == ImpactExtra.Funnel;
            string shellMask = funnel ? "T_MaskRibbon" : extra == ImpactExtra.Arcs || delivery == DeliveryType.Instant ? "T_MaskBoltStrip" : "T_MaskCrown";
            var shell = VfxSkillSetup.Shell(dir + $"M_{safe}_Shell.mat", shellMask, core, theme, dark, 0.06f, 0.05f, 0.5f, 0.2f,
                                            funnel ? new Vector2(-0.6f, 0) : Vector2.zero, funnel ? 1f : 0f);
            var glow = VfxSkillSetup.Particle(dir + $"M_{safe}_Glow.mat", Shader.Find("VfxSkill/ParticleSoft"), "T_MaskBoltStrip", new Color(theme.r, theme.g, theme.b, 0.42f), false, 0f);

            string path = dir + $"EP_{safe}.asset";
            var p = AssetDatabase.LoadAssetAtPath<ElementProfile>(path);
            bool fresh = !p;
            if (fresh) p = CreateInstance<ElementProfile>();
            if (fresh) Defaults(p, delivery, spec);   // never overwrite numbers someone already tuned
            p.displayName = spec.name; p.theme = theme; p.dark = dark; p.delivery = delivery;
            p.orb = orbMat; p.impact = bodyMat; p.decal = decalMat; p.star = star; p.ring = ring; p.shell = shell; p.glow = glow;
            p.extra = extra; p.contact = spec.Enum(spec.contact, ContactAccent.Star);
            p.trail = spec.Enum(spec.trail, TrailStyle.EmberSmoke); p.linger = spec.Enum(spec.linger, LingerStyle.Smolder);
            if (eruption)
            {
                p.columnAspect = body.width / (float)spec.bodyGrid.x / (body.height / (float)spec.bodyGrid.y) * spec.columnWidthScale;
                if (TryReadSidecar(spec.body, out var side) && side.bottom_inset > 0) p.columnRootInset = side.bottom_inset;   // root sits on the ground, not above it
            }
            if (fresh) AssetDatabase.CreateAsset(p, path); else EditorUtility.SetDirty(p);
            AssetDatabase.SaveAssets();
            string issues = p.Validate();
            Debug.Log($"[VfxSkill] created {path}" + (issues.Length > 0 ? " — check: " + issues : ""));
            return p;
        }
    }

    /// <summary>A throwaway stage to judge skills on: ground, light, a caster and a target, and every ElementProfile under Assets/VfxSkill/Skills.</summary>
    public static class DemoSceneBuilder
    {
        public const string ScenePath = VfxSkillSetup.Root + "/Demo/VfxSkillDemo.unity";

        [MenuItem("VFX Skill/3. Build demo scene")]
        public static void Build()
        {
            if (!Application.isBatchMode && !EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene);
            var lit = Shader.Find("Universal Render Pipeline/Lit");
            var sun = new GameObject("Sun").AddComponent<Light>(); sun.type = LightType.Directional; sun.shadows = LightShadows.Soft;
            sun.transform.rotation = Quaternion.Euler(50, -30, 0);
            RenderSettings.ambientMode = AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.62f, 0.72f, 0.9f); RenderSettings.ambientEquatorColor = new Color(0.5f, 0.52f, 0.55f); RenderSettings.ambientGroundColor = new Color(0.3f, 0.28f, 0.26f);
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane); ground.name = "Ground"; ground.transform.localScale = Vector3.one * 10;
            ground.GetComponent<Renderer>().sharedMaterial = Lit(lit, new Color(0.42f, 0.45f, 0.42f), "M_Ground");

            var caster = new GameObject("Caster");   // root on the ground: skills measure the hand and aim from the feet
            Capsule("Visual", Vector3.zero, Lit(lit, new Color(0.95f, 0.75f, 0.25f), "M_Caster")).transform.SetParent(caster.transform, false);
            var target = new GameObject("Target"); target.transform.SetPositionAndRotation(new Vector3(0, 0, 4.5f), Quaternion.Euler(0, 180, 0));
            var tv = Capsule("Visual", Vector3.zero, Lit(lit, new Color(0.92f, 0.92f, 0.95f), "M_Target")); tv.transform.SetParent(target.transform, false);
            target.AddComponent<DemoTarget>().visual = tv.transform;

            var cam = new GameObject("Main Camera").AddComponent<Camera>(); cam.tag = "MainCamera";
            cam.transform.position = new Vector3(-5.6f, 1.7f, 2.6f); cam.transform.LookAt(new Vector3(0, 1.1f, 2.4f)); cam.fieldOfView = 50;
            var fx = new GameObject("ElementFX").AddComponent<ElementFX>(); fx.groundY = 0;

            var demo = caster.AddComponent<SkillDemo>();
            foreach (var guid in AssetDatabase.FindAssets("t:ElementProfile", new[] { VfxSkillSetup.SkillDir.TrimEnd('/') }))
            {
                var p = AssetDatabase.LoadAssetAtPath<ElementProfile>(AssetDatabase.GUIDToAssetPath(guid));
                var s = caster.AddComponent<ElementSkill>(); s.profile = p; s.target = target.transform; s.targetOffset = new Vector3(0, 1f, 0); s.targetRadius = 0.5f;
                demo.skills.Add(s);
            }
            VfxSkillSetup.Folder(Path.GetDirectoryName(ScenePath));
            EditorSceneManager.SaveScene(scene, ScenePath);
            Debug.Log($"[VfxSkill] {ScenePath} with {demo.skills.Count} skill(s). Enter Play mode: skills cast in turn; click a button (or 1–9 with the legacy Input Manager) to pick one.");
        }

        // Saved as assets so the scene keeps its colours after reopening (in-memory materials are lost with the scene).
        static Material Lit(Shader lit, Color c, string name)
        {
            string path = VfxSkillSetup.Root + "/Demo/" + name + ".mat";
            VfxSkillSetup.Folder(VfxSkillSetup.Root + "/Demo");
            return VfxSkillSetup.Mat(path, lit, m => m.SetColor("_BaseColor", c));
        }

        static GameObject Capsule(string name, Vector3 pos, Material mat)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Capsule); go.name = name; go.transform.position = pos + Vector3.up;
            UnityEngine.Object.DestroyImmediate(go.GetComponent<Collider>());
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go;
        }
    }
}
