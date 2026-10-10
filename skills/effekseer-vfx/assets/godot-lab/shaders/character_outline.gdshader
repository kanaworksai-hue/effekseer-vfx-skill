// Inverted-hull outline for the demo characters (next pass of character_toon): back faces pushed out along
// the normal, drawn as a darkened version of the surface colour so lines read as ink, not as a black border.
shader_type spatial;
render_mode unshaded, cull_front, depth_draw_opaque;

uniform sampler2D albedo_texture : source_color, filter_linear_mipmap;
// In model units; the characters are 1 unit tall before the Lab's 1.75 scale.
uniform float width : hint_range(0.0, 0.02) = 0.0022;
uniform float darken : hint_range(0.0, 1.0) = 0.35;

void vertex() {
	VERTEX += NORMAL * width;
}

void fragment() {
	ALBEDO = texture(albedo_texture, UV).rgb * darken;
}
