using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// Procedural meshes for the element skills. All are parametric surfaces pos(u, v):
    /// u ∈ [0,1] along the main direction (around / length), v ∈ [0,1] along the secondary direction (height / width).
    /// Normals and tangents come from finite differences (tangent = ∂pos/∂u, which anisotropic highlights in a shader rely on).
    /// Without flipping, normal = ∂v × ∂u, so surfaces parameterised by (azimuth, height) face outward; Tube/Ring need flip.
    /// </summary>
    public static class MeshBuilder
    {
        public delegate Vector3 Surface(float u, float v);

        public static Mesh Build(string name, int nu, int nv, Surface f, float uRepeat, float vRepeat,
                                 bool wrapU = false, bool flip = false, System.Func<float, float, float> alpha = null)
        {
            int cols = nu + 1, rows = nv + 1;
            var pos = new Vector3[cols * rows];
            var col = new Color[pos.Length];
            var uv2 = new Vector2[pos.Length];
            var nrm = new Vector3[pos.Length];
            var tan = new Vector4[pos.Length];
            var uv = new Vector2[pos.Length];
            const float e = 1e-3f;
            for (int j = 0; j < rows; j++)
            for (int i = 0; i < cols; i++)
            {
                float u = (float)i / nu, v = (float)j / nv;
                int k = j * cols + i;
                pos[k] = f(u, v);
                float u0 = wrapU ? u - e : Mathf.Max(0, u - e), u1 = wrapU ? u + e : Mathf.Min(1, u + e);
                float v0 = Mathf.Max(0, v - e), v1 = Mathf.Min(1, v + e);
                // Note: Vector3.Normalize returns 0 for vectors shorter than 1e-5, which finite differences on small meshes can fall below, so everything is normalised by hand
                Vector3 du = SafeNorm(f(u1, v) - f(u0, v), Vector3.zero);
                Vector3 dv = SafeNorm(f(u, v1) - f(u, v0), Vector3.zero);
                Vector3 n = SafeNorm(Vector3.Cross(dv, du), Vector3.up);   // fall back to up at degenerate points such as poles
                if (flip) n = -n;
                nrm[k] = n;
                Vector3 t = du == Vector3.zero ? Vector3.right : du;
                // Unity convention: B = cross(N, T) * w; here w makes B point along +v
                tan[k] = new Vector4(t.x, t.y, t.z, flip ? 1 : -1);
                uv[k] = new Vector2(u * uRepeat, v * vRepeat);
                uv2[k] = new Vector2(u, v);                                   // normalised parameter coordinates (for shape masks)
                col[k] = new Color(1, 1, 1, alpha != null ? Mathf.Clamp01(alpha(u, v)) : 1f);   // vertex alpha: fade at the ends
            }
            var tris = new int[nu * nv * 6];
            int ti = 0;
            for (int j = 0; j < nv; j++)
            for (int i = 0; i < nu; i++)
            {
                int a = j * cols + i, b = a + 1, c = a + cols, d = c + 1;
                if (!flip) { tris[ti++] = a; tris[ti++] = c; tris[ti++] = b; tris[ti++] = b; tris[ti++] = c; tris[ti++] = d; }
                else       { tris[ti++] = a; tris[ti++] = b; tris[ti++] = c; tris[ti++] = b; tris[ti++] = d; tris[ti++] = c; }
            }
            var m = new Mesh { name = name };
            if (pos.Length > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            m.vertices = pos; m.normals = nrm; m.tangents = tan; m.uv = uv; m.uv2 = uv2; m.colors = col; m.triangles = tris;
            m.RecalculateBounds();
            return m;
        }

        static Vector3 SafeNorm(Vector3 v, Vector3 fallback)
        {
            float m = Mathf.Sqrt(v.x * v.x + v.y * v.y + v.z * v.z);
            return m > 1e-12f ? v / m : fallback;
        }

        static float TwoPi => Mathf.PI * 2;

        /// <summary>Hemisphere shield with its base at y=0.</summary>
    }
}
