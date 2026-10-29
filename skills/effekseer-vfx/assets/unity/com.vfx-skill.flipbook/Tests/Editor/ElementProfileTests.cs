using NUnit.Framework;
using UnityEngine;

namespace VfxSkill.Tests
{
    /// <summary>When a designer enters 0 / negative values in the Inspector, Validate must report them (runtime also clamps separately, so nothing loops forever).</summary>
    public class ElementProfileTests
    {
        [Test]
        public void ZeroSpeedAndSpacing_AreReported()
        {
            var p = ScriptableObject.CreateInstance<ElementProfile>();
            p.speed = 0; p.trailSpacing = 0;
            string e = p.Validate();
            StringAssert.Contains("speed", e);
            StringAssert.Contains("trailSpacing", e);
            Object.DestroyImmediate(p);
        }

        [Test]
        public void SafeValues_ReportOnlyMissingMaterials()
        {
            var p = ScriptableObject.CreateInstance<ElementProfile>();
            p.speed = 10; p.trailSpacing = 0.05f;
            string e = p.Validate();
            StringAssert.DoesNotContain("speed <", e);
            StringAssert.DoesNotContain("trailSpacing <", e);
            Object.DestroyImmediate(p);
        }
    }
}
