// Cel shading for optional rigged stand-in characters. One shader, three roles (skin / hair / cloth) set by uniforms:
// a two-tone light ramp with a tinted shadow instead of PBR, a lit-side rim, and an optional hair highlight band.
shader_type spatial;
render_mode diffuse_lambert, specular_disabled, cull_back;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap_anisotropic;
uniform vec4 albedo_tint : source_color = vec4(1.0);
// Ramp: where the shadow edge sits on N·L (−1..1) and how soft it is.
uniform float shade_threshold : hint_range(-1.0, 1.0) = 0.05;
uniform float shade_softness : hint_range(0.001, 0.5) = 0.04;
// Shadow colour multiplies the albedo: skin goes warm, cloth and hair go cool.
uniform vec4 shadow_color : source_color = vec4(0.72, 0.68, 0.82, 1.0);
// The ramp does not fall off with angle, so stacked lights add up fast: the key (directional) light gets full
// weight, point lights (fill, hit flash) a fraction, and the whole result is scaled to stay under the glow threshold.
uniform float light_scale : hint_range(0.0, 2.0) = 0.5;
uniform float point_light_weight : hint_range(0.0, 1.0) = 0.4;
uniform float rim_strength : hint_range(0.0, 2.0) = 0.25;
uniform float rim_power : hint_range(0.5, 8.0) = 3.0;
// Hair: a hard-edged highlight band around the half vector.
uniform float highlight_strength : hint_range(0.0, 2.0) = 0.0;
uniform float highlight_size : hint_range(0.0, 0.5) = 0.06;
// Mixed parts (arm + glove, leg + stocking): pixels whose colour reads as skin take the skin shadow instead.
uniform bool skin_from_color = false;
uniform vec4 skin_shadow_color : source_color = vec4(0.96, 0.74, 0.72, 1.0);
uniform float skin_softness : hint_range(0.001, 0.5) = 0.12;

varying float skin;

float skin_likelihood(vec3 c) {
	// Light skin tones: warm hue (red > green > blue), low-mid saturation, bright.
	float mx = max(c.r, max(c.g, c.b));
	float mn = min(c.r, min(c.g, c.b));
	float sat = (mx - mn) / max(mx, 1e-4);
	float warm = step(c.b, c.g) * step(c.g, c.r);
	return warm * smoothstep(0.55, 0.7, mx) * smoothstep(0.06, 0.14, sat) * (1.0 - smoothstep(0.45, 0.6, sat));
}

void fragment() {
	vec4 c = texture(albedo_texture, UV) * albedo_tint;
	ALBEDO = c.rgb;
	ROUGHNESS = 1.0;
	METALLIC = 0.0;
	skin = skin_from_color ? skin_likelihood(c.rgb) : 0.0;
}

void light() {
	float ndl = dot(NORMAL, LIGHT);
	float softness = mix(shade_softness, skin_softness, skin);
	float lit = smoothstep(shade_threshold - softness, shade_threshold + softness, ndl) * ATTENUATION;
	vec3 ramp = mix(mix(shadow_color.rgb, skin_shadow_color.rgb, skin), vec3(1.0), lit);
	float weight = light_scale * (LIGHT_IS_DIRECTIONAL ? 1.0 : point_light_weight);
	DIFFUSE_LIGHT += LIGHT_COLOR * ramp * weight / PI;
	if (LIGHT_IS_DIRECTIONAL) {
		float rim = pow(1.0 - clamp(dot(NORMAL, VIEW), 0.0, 1.0), rim_power) * rim_strength * lit;
		DIFFUSE_LIGHT += LIGHT_COLOR * rim * light_scale / PI;
	}
	if (highlight_strength > 0.0) {
		vec3 h = normalize(VIEW + LIGHT);
		float band = smoothstep(1.0 - highlight_size, 1.0 - highlight_size * 0.6, dot(NORMAL, h));
		SPECULAR_LIGHT += LIGHT_COLOR * band * highlight_strength * lit * weight * (1.0 - skin) / PI;
	}
}
