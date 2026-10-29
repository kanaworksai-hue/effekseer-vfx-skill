using NUnit.Framework;
using UnityEngine;

namespace VfxSkill.Tests
{
    /// <summary>Eruption (water column) config checks, frame curve and atlas layout: these must not silently break when the atlas or parameters change.</summary>
    public class EruptionTests
    {
        [Test]
        public void BadEruptionValues_AreReported()
        {
            var p = ScriptableObject.CreateInstance<ElementProfile>();
            p.delivery = DeliveryType.Eruption;
            p.columnHeight = 0; p.columnLife = 0; p.warnTime = -1; p.columnLift = -1; p.knockback = -1;
            p.columnFrames = new AnimationCurve();
            string e = p.Validate();
            foreach (var what in new[] { "columnHeight", "columnLife", "warnTime", "columnLift", "knockback", "columnFrames", "impact (column)" })
                StringAssert.Contains(what, e);
            StringAssert.DoesNotContain("columnFront", e);                      // the front layer is optional
            Object.DestroyImmediate(p);
        }

        [Test]
        public void DefaultColumnCurve_StartsAt0_EndsAt1_AndNeverGoesBack()
        {
            var p = ScriptableObject.CreateInstance<ElementProfile>();
            var c = p.columnFrames;
            Assert.AreEqual(0f, c.Evaluate(0f), 1e-4f);
            Assert.AreEqual(1f, c.Evaluate(1f), 1e-4f);
            float prev = -1;
            for (int i = 0; i <= 100; i++) { float v = c.Evaluate(i / 100f); Assert.GreaterOrEqual(v, prev - 1e-3f, $"frame curve goes backwards at {i}%"); prev = v; }
            Assert.That(p.columnHoldEnd, Is.InRange(0.05f, 0.95f));
            Object.DestroyImmediate(p);
        }

        [Test]
        public void LinearCurve_HasSegmentSlopes()
        {
            var c = ElementProfile.LinearCurve(0, 0, 0.5f, 0.25f, 1, 1);
            Assert.AreEqual(0.125f, c.Evaluate(0.25f), 1e-3f);                  // first segment slope is 0.5: the midpoint lies exactly on the line (flat tangents would sag below it)
            Assert.AreEqual(0.625f, c.Evaluate(0.75f), 1e-3f);
            Assert.AreEqual(0.5f, c.keys[1].inTangent, 1e-4f); Assert.AreEqual(1.5f, c.keys[1].outTangent, 1e-4f);
        }

    }
}
