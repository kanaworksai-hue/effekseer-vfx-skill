using System.Collections.Generic;
using UnityEngine;

namespace VfxSkill
{
    /// <summary>
    /// Procedural lightning: midpoint displacement builds an uneven jagged trunk plus 2–3 tapering forks, output as a camera-facing strip mesh.
    /// Across the strip v ∈ [0,1] (with the ridge mask of T_MaskBoltStrip, StylizedShell yields a white core + violet glow + dark rim);
    /// along the strip u follows the path. Every call makes a new path (each strike has a different shape).
    /// </summary>
    public static class BoltPath
    {
        static readonly List<Vector3> pts = new List<Vector3>();
        static readonly List<float> wid = new List<float>();
        static readonly List<Vector3> verts = new List<Vector3>();
        static readonly List<Vector2> uvs = new List<Vector2>(), uv2s = new List<Vector2>();
        static readonly List<Color> cols = new List<Color>();
        static readonly List<int> tris = new List<int>();

        static readonly List<(List<Vector3> pts, float width, float taper)> lines = new List<(List<Vector3>, float, float)>();

        /// <summary>
        /// Writes a bolt from a to b into mesh (hard-edged white-core strip); if glow is not null, the same path is also written as a soft strip glowScale times wider (for the glow).
        /// width: trunk width (m); forks: fork count (forks are 0.35× the trunk width); jag: jaggedness (fraction of length).
        /// </summary>
        public static void Build(Mesh mesh, Vector3 a, Vector3 b, Vector3 camPos, float width, int forks, float jag = 0.12f, int depth = 5, Mesh glow = null, float glowScale = 3.2f)
        {
            lines.Clear();
            var main = Jagged(a, b, jag, depth);
            lines.Add((main, width, 1f));
            for (int f = 0; f < forks; f++)
            {
                int i = Random.Range(main.Count / 5, main.Count * 3 / 4);
                Vector3 dir = (b - a);
                float len = dir.magnitude * Random.Range(0.15f, 0.32f);
                Vector3 side = Vector3.Cross(dir, Random.onUnitSphere).normalized;
                Vector3 fd = Vector3.Slerp(dir.normalized, side, Random.Range(0.35f, 0.6f)).normalized;
                lines.Add((Jagged(main[i], main[i] + fd * len, jag * 1.2f, Mathf.Max(1, depth - 2)), width * 0.35f, 0f));
            }
            Write(mesh, camPos, 1f);
            if (glow) Write(glow, camPos, glowScale);
        }

        static void Write(Mesh mesh, Vector3 camPos, float scale)
        {
            verts.Clear(); uvs.Clear(); uv2s.Clear(); cols.Clear(); tris.Clear();
            Random.State st = Random.state; Random.InitState(1234);   // both strips get the same width jitter
            foreach (var (pts, w, taper) in lines) Strip(pts, w * scale, taper, camPos);
            Random.state = st;
            mesh.Clear();
            mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetUVs(1, uv2s); mesh.SetColors(cols); mesh.SetTriangles(tris, 0);
            mesh.RecalculateBounds();
        }

        static List<Vector3> Jagged(Vector3 a, Vector3 b, float jag, int depth)
        {
            var list = new List<Vector3> { a, b };
            float amp = (b - a).magnitude * jag;
            Vector3 axis = (b - a).normalized;
            for (int d = 0; d < depth; d++)
            {
                var next = new List<Vector3>(list.Count * 2);
                for (int i = 0; i < list.Count - 1; i++)
                {
                    next.Add(list[i]);
                    float t = Random.Range(0.3f, 0.7f);                    // uneven segment split
                    Vector3 off = Vector3.ProjectOnPlane(Random.insideUnitSphere, axis) * amp;
                    next.Add(Vector3.Lerp(list[i], list[i + 1], t) + off);
                }
                next.Add(list[list.Count - 1]);
                list = next; amp *= 0.55f;
            }
            return list;
        }

        // Taper: startTaper=1 tapers both ends (trunk), 0 tapers only the tip (forks grow out of the trunk)
        static void Strip(List<Vector3> p, float width, float startTaper, Vector3 camPos)
        {
            int baseIdx = verts.Count, n = p.Count;
            for (int i = 0; i < n; i++)
            {
                float u = (float)i / (n - 1);
                Vector3 tan = (p[Mathf.Min(i + 1, n - 1)] - p[Mathf.Max(i - 1, 0)]).normalized;
                Vector3 toCam = (camPos - p[i]).normalized;
                Vector3 side = Vector3.Cross(tan, toCam).normalized;
                float taper = Mathf.Lerp(1f, Mathf.SmoothStep(0, 1, u / 0.15f), startTaper) * Mathf.SmoothStep(0, 1, (1 - u) / 0.3f);
                float w = width * (0.35f + 0.65f * taper) * Random.Range(0.8f, 1.15f);
                verts.Add(p[i] - side * w * 0.5f); verts.Add(p[i] + side * w * 0.5f);
                uvs.Add(new Vector2(u, 0)); uvs.Add(new Vector2(u, 1));
                uv2s.Add(new Vector2(u, u)); uv2s.Add(new Vector2(u, u));
                var c = new Color(1, 1, 1, Mathf.Lerp(0.55f, 1f, taper));      // vertex alpha: tips erode and thin out earlier
                cols.Add(c); cols.Add(c);
                if (i < n - 1)
                {
                    int k = baseIdx + i * 2;
                    tris.Add(k); tris.Add(k + 2); tris.Add(k + 1);
                    tris.Add(k + 1); tris.Add(k + 2); tris.Add(k + 3);
                }
            }
        }
    }
}
