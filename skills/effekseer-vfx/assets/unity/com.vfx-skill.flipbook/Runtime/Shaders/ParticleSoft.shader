// Shared particle shader for splashes / mist / ripples (URP)
// vertex colour × texture × HDR colour; soft particles (fade where they intersect the scene); fade near the camera
Shader "VfxSkill/ParticleSoft"
{
    Properties
    {
        _MainTex ("Texture", 2D) = "white" {}
        [HDR]_Color ("Color", Color) = (1, 1, 1, 1)
        _SoftFade ("Soft Particle Distance", Float) = 0.3
        _CameraFade ("Camera Near Fade", Float) = 0.6
        _AlphaPow ("Alpha Power", Float) = 1
        [Toggle(_SOFTPARTICLES)] _SoftOn ("Soft particles (needs depth texture)", Float) = 1
        [Enum(UnityEngine.Rendering.BlendMode)] _SrcBlend ("Src Blend", Float) = 5
        [Enum(UnityEngine.Rendering.BlendMode)] _DstBlend ("Dst Blend", Float) = 10
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" "PreviewType" = "Plane" }
        Pass
        {
            Name "ParticleForward"
            Tags { "LightMode" = "UniversalForward" }
            Blend [_SrcBlend] [_DstBlend]
            ZWrite Off
            Cull Off

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #pragma shader_feature_local _SOFTPARTICLES
            #if defined(_SOFTPARTICLES)
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #endif

            TEXTURE2D(_MainTex); SAMPLER(sampler_MainTex);
            CBUFFER_START(UnityPerMaterial)
                float4 _MainTex_ST;
                half4 _Color;
                float _SoftFade, _CameraFade, _AlphaPow, _SrcBlend, _DstBlend, _SoftOn;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; };
            struct Varyings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; half4 color : COLOR; float4 screenPos : TEXCOORD1; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.uv = TRANSFORM_TEX(v.uv, _MainTex);
                o.color = v.color;
                o.screenPos = ComputeScreenPos(o.positionCS);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                half4 tex = SAMPLE_TEXTURE2D(_MainTex, sampler_MainTex, i.uv);
                half4 c = tex * i.color * _Color;
                c.a = pow(saturate(c.a), _AlphaPow);
                float z = i.screenPos.w;
                #if defined(_SOFTPARTICLES)
                float2 suv = i.screenPos.xy / i.screenPos.w;
                float sceneZ = LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams);
                c.a *= saturate((sceneZ - z) / max(_SoftFade, 1e-3));
                #endif
                c.a *= saturate((z - _ProjectionParams.y) / max(_CameraFade, 1e-3));
                // with additive blending, multiply alpha into the colour
                if (_DstBlend == 1) c.rgb *= c.a;
                return c;
            }
            ENDHLSL
        }
    }
}
