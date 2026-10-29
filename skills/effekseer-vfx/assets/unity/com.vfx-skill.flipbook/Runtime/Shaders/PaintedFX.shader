// Hand-painted effect textures (e.g. AI-generated, anime-style element textures).
// Keeps the painting as is and only adds: slight flow-noise UV distortion (so painted water feels alive) + soft erosion fade-out + HDR tint.
// Meshes drive erosion with _Erosion; particles with vertex alpha (Color over Lifetime).
Shader "VfxSkill/PaintedFX"
{
    Properties
    {
        _MainTex ("Painted Texture (RGBA)", 2D) = "white" {}
        _NoiseTex ("Distortion Noise (RG)", 2D) = "gray" {}
        [HDR]_Tint ("Tint", Color) = (1.15, 1.15, 1.2, 1)
        _Distort ("UV distortion amount", Range(0, 0.05)) = 0.008
        _DistortScale ("Distortion scale (xy) scroll (zw)", Vector) = (2, 2, 0.15, -0.3)
        _Erosion ("Erosion", Range(0, 1)) = 0
        _AlphaBoost ("Alpha boost", Range(0.5, 3)) = 1.4
        _Soft ("Erosion softness", Range(0.01, 0.6)) = 0.25
        _ErodeNoise ("Erosion noise", Range(0, 1)) = 0.45
        _SoftFade ("Soft particle distance", Float) = 0.1
        _TimeOffset ("Time offset", Float) = 0
        _CamPush ("Push toward camera (m)", Float) = 0
        _Tiles ("Flipbook tiles cols/rows (particle sheet)", Vector) = (8, 8, 0, 0)
        _Grow ("Particle sheet: start scale, grow time (0 = default curve)", Vector) = (0, 0, 0, 0)
        _Flip ("Self-animated loop on a quad: cols, rows, fps (0 = off)", Vector) = (1, 1, 0, 0)
        [Toggle(_SOFTPARTICLES)] _SoftOn ("Soft particles (needs depth texture)", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 5
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 10
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 0
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite Off
            Cull [_Cull]
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #pragma shader_feature_local _SOFTPARTICLES
            #if defined(_SOFTPARTICLES)
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #endif
            TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);
            TEXTURE2D(_NoiseTex); SAMPLER(sampler_NoiseTex);
            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST, _NoiseTex_ST, _DistortScale, _Tiles, _Flip;
                half4 _Tint;
                float _Distort, _Erosion, _AlphaBoost, _Soft, _ErodeNoise, _SoftFade, _TimeOffset, _SrcBlend, _DstBlend, _Cull, _CamPush, _SoftOn;
            CBUFFER_END
            struct A { float4 pos : POSITION; float2 uv : TEXCOORD0; half4 col : COLOR; };
            struct V { float4 pos : SV_POSITION; float2 uv : TEXCOORD0; half4 col : COLOR; float4 sp : TEXCOORD1; float2 cell : TEXCOORD2; };
            V vert(A i)
            {
                V o;
                float3 w = TransformObjectToWorld(i.pos.xyz);
                float camDist = distance(_WorldSpaceCameraPos, w);
                w += (_WorldSpaceCameraPos - w) / max(camDist, 1e-4) * min(_CamPush, max(0, camDist - _ProjectionParams.y * 4));   // never push past the near plane      // push the impact flipbook toward the camera so the target model doesn't hide it; updates live as the camera moves
                o.pos = TransformWorldToHClip(w); o.uv = TRANSFORM_TEX(i.uv, _MainTex); o.col = i.col; o.sp = ComputeScreenPos(o.pos);
                o.cell = -1;                                                     // <0: plain texture, uv is the atlas uv
                if (_Flip.z > 0)                                                 // orb in flight (e.g. fireball): the quad loops the atlas itself (first cell at top left)
                {
                    float2 grid = max(_Flip.xy, 1);
                    float frames = grid.x * grid.y;
                    float f = min(floor(frac((_Time.y + _TimeOffset) * _Flip.z / frames) * frames), frames - 1);   // frac stays in 0–1 even for negative time
                    o.cell = float2(fmod(f, grid.x), grid.y - 1 - floor(f / grid.x));
                    o.uv = saturate(i.uv);                                       // cell-local uv: distortion and noise are computed within the cell, then mapped to the atlas in the fragment stage
                }
                return o;
            }
            half4 frag(V i) : SV_Target
            {
                float t = _Time.y + _TimeOffset;
                half2 n = SAMPLE_TEXTURE2D(_NoiseTex, sampler_NoiseTex, i.uv * _DistortScale.xy + _DistortScale.zw * t).rg;
                float2 uv = i.uv + (n - 0.5) * 2 * _Distort;
                if (i.cell.x >= 0) uv = (saturate(uv) + i.cell) / max(_Flip.xy, 1);      // self-looping atlas: clamp the distorted uv to this cell so it can't bleed into neighbouring frames
                half4 tex = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, uv);
                tex.a = saturate(tex.a * _AlphaBoost);                       // painted water needs more opacity on bright backgrounds
                // erosion: combine mesh _Erosion with particle vertex alpha; noise breaks up the vanishing edge
                float e = saturate(_Erosion + (1 - i.col.a));
                float m = tex.a * (1 - _ErodeNoise + _ErodeNoise * n.g * 1.6);
                // e=0 fully kept, e=1 fully gone; the threshold advances smoothly in between
                half a = tex.a * smoothstep(e, e + _Soft, m + (1 - e) * _Soft);
                #if defined(_SOFTPARTICLES)
                float2 suv = i.sp.xy / i.sp.w;
                a *= saturate((LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams) - i.sp.w) / max(_SoftFade, 1e-3));
                #endif
                half3 c = tex.rgb * i.col.rgb * _Tint.rgb;
                if (_DstBlend == 1) c *= a;
                return half4(c, a);
            }
            ENDHLSL
        }
    }
}
