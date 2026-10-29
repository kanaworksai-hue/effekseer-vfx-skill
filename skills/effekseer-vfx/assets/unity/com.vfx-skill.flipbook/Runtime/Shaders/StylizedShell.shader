// Cel-shaded mesh effects (water crown, wind bands, lightning): greyscale shape mask + hard threshold.
// Mask value = distance from the edge. Below the threshold is transparent; just above it is a dark band (ink rim), the middle is the saturated body, the thickest part is a white-hot core.
// Erosion (_Erosion + vertex alpha) raises the threshold: the thinnest parts vanish first and the edge stays hard (hand-drawn-animation style dissipation).
// Same rule as the value ramp of the flipbook grade (vfx video-grade), so meshes and flipbooks share one look.
Shader "VfxSkill/StylizedShell"
{
    Properties
    {
        _MainTex ("Shape Mask (A)", 2D) = "white" {}
        _NoiseTex ("Breakup Noise (R)", 2D) = "gray" {}
        [HDR]_Core ("Core", Color) = (1, 1, 1, 1)
        [HDR]_Body ("Body", Color) = (0.2, 0.55, 1, 1)
        _Rim ("Rim (ink)", Color) = (0.03, 0.12, 0.35, 1)
        _Cutoff ("Base cutoff", Range(0, 0.9)) = 0.12
        _RimWidth ("Rim width", Range(0, 0.4)) = 0.1
        _CoreLevel ("Core level", Range(0.3, 1.01)) = 0.82
        _Erosion ("Erosion", Range(0, 1)) = 0
        _ErodeDir ("Erode bottom-up (uv2.y)", Range(-1, 1)) = 0
        _NoiseAmt ("Noise breakup", Range(0, 1)) = 0.35
        _NoiseScale ("Noise scale (xy) scroll (zw)", Vector) = (3, 1.5, 0.2, -0.4)
        _Scroll ("Mask UV scroll (xy)", Vector) = (0, 0, 0, 0)
        _Opacity ("Opacity", Range(0, 1)) = 1
        _CamPush ("Push toward camera (m)", Float) = 0
        _SoftFade ("Soft particle distance", Float) = 0.15
        [Toggle(_SOFTPARTICLES)] _SoftOn ("Soft particles (needs depth texture)", Float) = 1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            Blend SrcAlpha OneMinusSrcAlpha
            ZWrite Off
            Cull [_Cull]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma shader_feature_local _SOFTPARTICLES
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #if defined(_SOFTPARTICLES)
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #endif
            TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);
            TEXTURE2D(_NoiseTex); SAMPLER(sampler_NoiseTex);
            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST, _NoiseTex_ST, _NoiseScale, _Scroll;
                half4 _Core, _Body, _Rim;
                float _Cutoff, _RimWidth, _CoreLevel, _Erosion, _ErodeDir, _NoiseAmt, _Opacity, _CamPush, _SoftFade, _SoftOn, _Cull;
            CBUFFER_END
            struct A { float4 pos : POSITION; float2 uv : TEXCOORD0; float2 uv2 : TEXCOORD1; half4 col : COLOR; };
            struct V { float4 pos : SV_POSITION; float4 uv : TEXCOORD0; half4 col : COLOR; float4 sp : TEXCOORD1; };
            V vert(A i)
            {
                V o;
                float3 w = TransformObjectToWorld(i.pos.xyz);
                float camDist = distance(_WorldSpaceCameraPos, w);
                w += (_WorldSpaceCameraPos - w) / max(camDist, 1e-4) * min(_CamPush, max(0, camDist - _ProjectionParams.y * 4));   // never push past the near plane      // sorting / intersection: push slightly toward the camera instead of a fixed offset baked in at emit time
                o.pos = TransformWorldToHClip(w);
                o.uv = float4(TRANSFORM_TEX(i.uv, _MainTex), i.uv2);
                o.col = i.col; o.sp = ComputeScreenPos(o.pos);
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                float t = _Time.y;
                float m = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, i.uv.xy + _Scroll.xy * t).a;
                float n = SAMPLE_TEXTURE2D(_NoiseTex, sampler_NoiseTex, i.uv.xy * _NoiseScale.xy + _NoiseScale.zw * t).r;
                float e = saturate(_Erosion + (1 - i.col.a));
                e = saturate(e + _ErodeDir * e * (0.5 - i.uv.w) * 1.6);    // directional erosion: >0 dissolves from the bottom first
                float thr = _Cutoff + e * (1.02 - _Cutoff);
                float s = m - (n - 0.5) * _NoiseAmt * (0.35 + e);
                float aa = max(fwidth(s) * 1.2, 1e-3);
                half a = smoothstep(thr, thr + aa, s);
                float rimW = _RimWidth * (1 - 0.85 * e);                    // the rim thins as it erodes, so a dissolving shape never turns entirely dark
                half rim = 1 - smoothstep(thr + rimW, thr + rimW + aa, s);
                // the core appears only in the original core area and always inside the rim; it shrinks during erosion so what remains never turns entirely core-coloured
                half core = smoothstep(_CoreLevel + e * 0.3, _CoreLevel + e * 0.3 + aa, s) * smoothstep(thr + rimW + 0.04, thr + rimW + 0.04 + aa, s);
                half3 c = lerp(lerp(_Body.rgb, _Core.rgb, core), _Rim.rgb, rim);
                a *= _Opacity;
                #if defined(_SOFTPARTICLES)
                float2 suv = i.sp.xy / i.sp.w;
                a *= saturate((LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams) - i.sp.w) / max(_SoftFade, 1e-3));
                #endif
                return half4(c, a);
            }
            ENDHLSL
        }
    }
}
