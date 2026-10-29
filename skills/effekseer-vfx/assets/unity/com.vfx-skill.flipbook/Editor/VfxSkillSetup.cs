using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.Universal;

namespace VfxSkill.EditorTools
{
    /// <summary>
    /// Shared materials every skill uses (sparks, contact flash, neutral smoke, droplets) and the URP depth texture
    /// soft particles need. Textures come from `vfx unity-install`, which writes procedural sheets and masks into
    /// Assets/VfxSkill/Generated/Textures; nothing here is painted.
    /// </summary>
    public static class VfxSkillSetup
    {
        public const string Root = "Assets/VfxSkill";
        public const string TexDir = Root + "/Generated/Textures/";
        public const string SharedDir = Root + "/Resources/VfxSkill/";   // ElementFX loads these by name at run time
        public const string SkillDir = Root + "/Skills/";

        [MenuItem("VFX Skill/1. Setup shared materials")]
        public static void Setup()
        {
            Folder(SharedDir); Folder(SkillDir);
            var part = Shader.Find("VfxSkill/ParticleSoft");
            var painted = Shader.Find("VfxSkill/PaintedFX");
            if (!part || !painted) { Debug.LogError("[VfxSkill] shaders not found: is the package installed under Packages/?"); return; }
            Particle(SharedDir + "M_Spark.mat", part, "T_Flash", Color.white, false, 0.05f);
            Particle(SharedDir + "M_Flash.mat", part, "T_Flash", new Color(1f, 1.2f, 1.5f, 1), true, 0.1f);
            Painted(SharedDir + "M_Smoke.mat", painted, "T_Smoke_2x2", 0.004f, 0.35f, true);
            Painted(SharedDir + "M_Drop.mat", painted, "T_Drop_2x2", 0f, 0.2f, true);
            EnableDepthTexture();
            AssetDatabase.SaveAssets();
            Debug.Log("[VfxSkill] shared materials ready in " + SharedDir);
        }

        /// <summary>Create an asset folder (and its parents) the AssetDatabase knows about, so CreateAsset can write into it.</summary>
        public static void Folder(string assetDir)
        {
            assetDir = assetDir.TrimEnd('/');
            if (AssetDatabase.IsValidFolder(assetDir)) return;
            string parent = Path.GetDirectoryName(assetDir).Replace('\\', '/');
            Folder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(assetDir));
        }

        public static Texture2D Tex(string name)
        {
            var t = AssetDatabase.LoadAssetAtPath<Texture2D>(TexDir + name + ".png");
            if (!t) Debug.LogWarning("[VfxSkill] missing generated texture " + name + " — run `vfx unity-install <project>` again");
            return t;
        }

        /// <summary>Create (or refresh) a material at `path`. Properties are set before CreateAsset: a material saved
        /// first and edited afterwards can lose its textures on the next asset operation.</summary>
        public static Material Mat(string path, Shader sh, System.Action<Material> fill)
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            bool fresh = !m;
            if (fresh) m = new Material(sh); else m.shader = sh;
            fill(m);
            if (fresh) AssetDatabase.CreateAsset(m, path); else EditorUtility.SetDirty(m);
            return m;
        }

        public static void Soft(Material m, float fade)
        {
            m.SetFloat("_SoftFade", Mathf.Max(fade, 0.0001f));
            bool on = fade > 0.001f;
            m.SetFloat("_SoftOn", on ? 1 : 0);
            if (on) m.EnableKeyword("_SOFTPARTICLES"); else m.DisableKeyword("_SOFTPARTICLES");
        }

        public static Material Particle(string path, Shader sh, string tex, Color c, bool additive, float soft) => Mat(path, sh, m =>
        {
            m.SetTexture("_MainTex", Tex(tex));
            m.SetColor("_Color", c);
            Soft(m, soft);
            m.SetFloat("_SrcBlend", (float)(additive ? BlendMode.One : BlendMode.SrcAlpha));
            m.SetFloat("_DstBlend", (float)(additive ? BlendMode.One : BlendMode.OneMinusSrcAlpha));
        });

        public static Material Painted(string path, Shader sh, Texture2D tex, float distort, float soft, bool particle) => Mat(path, sh, m =>
        {
            m.SetTexture("_MainTex", tex);
            m.SetTexture("_NoiseTex", Tex("T_FlowNoise"));
            m.SetFloat("_Distort", distort);
            m.SetFloat("_Soft", soft);
            Soft(m, particle ? 0.12f : 0.01f);
            m.SetColor("_Tint", particle ? new Color(1.0f, 1.05f, 1.1f, 1) : new Color(1.1f, 1.12f, 1.15f, 1));
        });

        public static Material Painted(string path, Shader sh, string tex, float distort, float soft, bool particle) => Painted(path, sh, Tex(tex), distort, soft, particle);

        /// <summary>A StylizedShell material: a greyscale distance mask drawn as core / body / dark rim, eroded by a threshold.</summary>
        public static Material Shell(string path, string mask, Color core, Color body, Color rim, float cutoff = 0.06f, float rimWidth = 0.05f,
                                     float coreLevel = 0.5f, float noise = 0.15f, Vector2 scroll = default, float erodeDir = 0f) =>
            Mat(path, Shader.Find("VfxSkill/StylizedShell"), m =>
            {
                m.SetTexture("_MainTex", Tex(mask));
                m.SetTexture("_NoiseTex", Tex("T_FlowNoise"));
                m.SetColor("_Core", core); m.SetColor("_Body", body); m.SetColor("_Rim", rim);
                m.SetFloat("_Cutoff", cutoff); m.SetFloat("_RimWidth", rimWidth); m.SetFloat("_CoreLevel", coreLevel);
                m.SetFloat("_NoiseAmt", noise); m.SetVector("_Scroll", new Vector4(scroll.x, scroll.y, 0, 0));
                m.SetFloat("_ErodeDir", erodeDir);
                Soft(m, 0f);
            });

        /// <summary>Soft particles need the camera depth texture: turn it on for every URP asset the project's quality levels
        /// use (a separate mobile asset without it would fade soft particles out on device), and nothing else.</summary>
        static void EnableDepthTexture()
        {
            var assets = new System.Collections.Generic.HashSet<UniversalRenderPipelineAsset>();
            if (GraphicsSettings.defaultRenderPipeline is UniversalRenderPipelineAsset d) assets.Add(d);
            for (int i = 0; i < QualitySettings.count; i++)
                if (QualitySettings.GetRenderPipelineAssetAt(i) is UniversalRenderPipelineAsset q) assets.Add(q);
            foreach (var a in assets)
                if (!a.supportsCameraDepthTexture) { a.supportsCameraDepthTexture = true; EditorUtility.SetDirty(a); Debug.Log("[VfxSkill] depth texture enabled on " + a.name); }
        }
    }

    /// <summary>
    /// Import rules for the textures this package uses. Flipbook sheets (Assets/VfxSkill/Flipbooks/, or any texture
    /// with a .flipbook.json sidecar): no mipmaps (a 6 px gutter does not survive low mips), clamped, never rescaled to a
    /// power of two (8×5 and 8×7 sheets would shift every cell), up to 4096 on desktop and 2048 on mobile.
    /// Generated masks are linear data; the rest are colour.
    /// </summary>
    public class VfxSkillTextureRules : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            bool flipbook = assetPath.Contains("/VfxSkill/Flipbooks/") || File.Exists(Path.ChangeExtension(assetPath, ".flipbook.json"));
            bool generated = assetPath.StartsWith(VfxSkillSetup.TexDir);
            if (!flipbook && !generated) return;
            var ti = (TextureImporter)assetImporter;
            string n = Path.GetFileNameWithoutExtension(assetPath);
            bool mask = generated && n.StartsWith("T_Mask");
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = !mask && n != "T_FlowNoise";
            ti.alphaIsTransparency = !mask;
            ti.alphaSource = TextureImporterAlphaSource.FromInput;
            ti.wrapMode = n == "T_FlowNoise" || n == "T_MaskRibbon" || n == "T_MaskCrown" ? TextureWrapMode.Repeat : TextureWrapMode.Clamp;
            ti.mipmapEnabled = !flipbook;
            if (flipbook) ti.npotScale = TextureImporterNPOTScale.None;
            ti.maxTextureSize = flipbook ? 4096 : 2048;
            ti.textureCompression = TextureImporterCompression.CompressedHQ;
            foreach (var platform in new[] { "Android", "iPhone" })
                ti.SetPlatformTextureSettings(new TextureImporterPlatformSettings
                {
                    name = platform, overridden = true, maxTextureSize = flipbook ? 2048 : 1024,
                    format = TextureImporterFormat.ASTC_6x6, compressionQuality = 50,
                });
        }
    }
}
