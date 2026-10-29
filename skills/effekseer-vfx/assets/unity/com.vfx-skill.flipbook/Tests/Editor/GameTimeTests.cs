using NUnit.Framework;
using UnityEngine;

namespace VfxSkill.Tests
{
    /// <summary>Layered time scale: hit stop and pause / slow motion never overwrite each other (regression test for a blocking issue found in technical review).</summary>
    public class GameTimeTests
    {
        [SetUp] public void Reset() => GameTime.ResetAll();
        [TearDown] public void Restore() => GameTime.ResetAll();

        [Test]
        public void FreezeThenRelease_RestoresBaseScale()
        {
            GameTime.BaseScale = 0.5f;
            GameTime.Freezing = true;
            Assert.AreEqual(0.5f * GameTime.FrozenScale, Time.timeScale, 1e-5f);
            GameTime.Freezing = false;
            Assert.AreEqual(0.5f, Time.timeScale, 1e-5f);
        }

        [Test]
        public void PauseViaApi_DuringFreeze_ResumesToBaseNotFrozen()
        {
            GameTime.Freezing = true;
            GameTime.Paused = true;
            GameTime.Freezing = false;            // hit stop ends while paused
            Assert.AreEqual(0f, Time.timeScale);
            GameTime.Paused = false;
            Assert.AreEqual(1f, Time.timeScale, 1e-5f);
        }

        [Test]
        public void LegacyPauseCode_SavesFrozenValue_DoesNotGetStuck()
        {
            GameTime.Freezing = true;
            float saved = Time.timeScale;         // old pause code: save the current value (= 0.03)
            Time.timeScale = 0f;                  // then write 0
            GameTime.Freezing = false;            // the hit stop service ends the freeze while paused
            Assert.AreEqual(0f, Time.timeScale, "must stay 0 while paused");
            Time.timeScale = saved;               // old code restores the saved 0.03
            GameTime.Sync();
            Assert.IsFalse(GameTime.Paused);
            Assert.AreEqual(1f, GameTime.BaseScale, 1e-5f, "the frozen value must not be taken as the new base scale");
            GameTime.Freezing = false;            // back to normal speed on the next write
            Assert.AreEqual(1f, Time.timeScale, 1e-5f);
        }

        [Test]
        public void ProjectSlowMotionAtThreePercent_NotMistakenForResume_WhenLegacyRuleOff()
        {
            GameTime.AbsorbLegacyWrites = false;
            try
            {
                GameTime.Freezing = true; GameTime.Freezing = false;
                Time.timeScale = GameTime.FrozenScale;     // the project's own 3% slow motion
                GameTime.Sync();
                Assert.AreEqual(GameTime.FrozenScale, GameTime.BaseScale, 1e-5f);
            }
            finally { GameTime.AbsorbLegacyWrites = true; }
        }

        [Test]
        public void ExternalSlowMotion_IsAdoptedAsBase()
        {
            Time.timeScale = 0.25f;               // slow motion written directly from elsewhere
            GameTime.Freezing = true;
            Assert.AreEqual(0.25f * GameTime.FrozenScale, Time.timeScale, 1e-5f);
            GameTime.Freezing = false;
            Assert.AreEqual(0.25f, Time.timeScale, 1e-5f);
        }
    }
}
