using NUnit.Framework;
using UnityEngine;

namespace VfxSkill.Tests
{
    /// <summary>Shell pool: a shell that is borrowed but temporarily hidden (flickering) must not be lent to anyone else (regression test for a blocking issue found in technical review).</summary>
    public class ShellPoolTests
    {
        [Test]
        public void HiddenShell_IsNotHandedOutAgain()
        {
            var hub = new GameObject("ElementFX_Test").AddComponent<ElementFX>();
            try
            {
                var a = ElementFX.Shell(null);
                a.Visible = false;                       // flickering: hidden but still in use
                var b = ElementFX.Shell(null);
                Assert.AreNotSame(a, b);
                a.Release();
                var c = ElementFX.Shell(null);
                Assert.AreSame(a, c, "should be reused after release");
            }
            finally { Object.DestroyImmediate(hub.gameObject); }
        }
    }
}
