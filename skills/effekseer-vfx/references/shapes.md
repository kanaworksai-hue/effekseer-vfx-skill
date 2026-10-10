# Volume and occlusion

Decide the body's volume first: ice spikes are crystals, a pillar is a procedural cylinder, a shock wave is a tilted
ring or thin shell, an accretion disk is far half ring + core + near half ring. Keep camera-facing sprites for
flashes, smoke and shapes that should face the camera. Look in the standard camera and the optional close view
(`vfx review --view close`), but the library baseline stays the standard combat staging.

Measured here: sphere depth works differently from cylinders (size spheres with scale); the Cone tip direction must
not be guessed (crystals use a Cylinder with an end radius); Model layers cannot rely on ZWrite, so occlusion follows
list order. Fresnel `begin`/`end` and `pow` behave as documented in [engine conventions](engine-conventions.md), not
as their names suggest.

Large shells and columns must not become translucent solid domes. Check outline, inner transparency and character
visibility first, then brightness; a full-screen glow does not hide a shape problem. A dark core must read on the
default stage, and check a bright background too (`--bright`).

Prefer the existing Ring, Model, UV scroll and dissolve features. Custom meshes are a later asset path: first show
that no primitive can express the shape, then verify export, UVs and that resources travel with the package. Never
patch the official renderer to work around an unverified assumption.

## Choose the volume from the standard camera

| Main shape | Construction available here | Spatial relation to check |
|---|---|---|
| slash | pivot with a tilted Ring or a fixed-plane arc | the arc passes through the point of action with space inside it |
| explosion | `billow`, a rising body, tilted waves and ground matter | it has a landing point and height; near and far layers separate |
| dark core | far half ring, core, near half ring in that order | the front half passes in front of the core, the back half is hidden by it |
| ice crystal | six-sided prism with a point, shards and cold mist | tip direction and facet light differ; the shatter is more than bright dots |
| sustained shell | fresnel outline, surface motion, fragment exit | character inside, shell surface and background each readable |
| light pillar | cylinder, static alpha gradient and scrolling streaks | top and bottom fade naturally; no UV seam through the body |

In the standard camera a low ground ring may read as a thin line, and lovely close-up detail may vanish at combat
distance. Build sideways or upward volume before adding more surface texture. The close view helps find problems; it
does not replace the standard camera for scale.

When layers overlap front to back, arrange draw order first, then verify in the image. A full shell outline drawn in
front of every fragment re-closes the gaps that should appear; dark smoke drawn in front of the fire hides the
saturated body that should remain. Correct geometry can still read wrong because of order.
