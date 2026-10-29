# effekseer-vfx-skill

<div align="center">

<img src="docs/assets/banner-es.jpg" alt="VFX Skill: tu agente de código crea VFX de juego en tiempo real para Effekseer, Godot y Unity" width="820">

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-6b4dff?style=flat-square"></a>
  <a href="https://agentskills.io"><img alt="Agent Skill" src="https://img.shields.io/badge/Agent_Skill-Claude_Code_·_Codex_·_Cursor-19b8d6?style=flat-square"></a>
  <img alt="Effekseer 1.80" src="https://img.shields.io/badge/Effekseer-1.80-ff7d2e?style=flat-square">
  <img alt="Godot 4" src="https://img.shields.io/badge/Godot-4-478cbf?style=flat-square&logo=godotengine&logoColor=white">
  <img alt="Unity 6 URP" src="https://img.shields.io/badge/Unity_6-URP-111?style=flat-square&logo=unity">
  <a href="https://github.com/kanaworksai-hue/effekseer-vfx-skill/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/kanaworksai-hue/effekseer-vfx-skill?style=flat-square&logo=github&label=stars&color=f5c518"></a>
</p>

<p><a href="https://github.com/kanaworksai-hue"><img src="docs/brand/kanaworks-mark.png" height="22" alt="" align="absmiddle"></a>&nbsp;<a href="https://github.com/kanaworksai-hue"><b>Un proyecto de KanaWorks_AI</b></a></p>

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (Brasil)](README.pt-BR.md) | Español

</div>

> Este documento es una traducción del README en inglés. Los agentes cargan los archivos en inglés de `skills/`; si hay diferencias, prevalece la versión en inglés.

Habilidades de agente (agent skills) que permiten a un agente de programación (Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode y otros
hosts compatibles con [Agent Skills](https://agentskills.io)) crear VFX de juego en tiempo real con código, iterando como lo haría un artista de VFX:

**brief de diseño → texturas → receta en Python → compilación con EffekseerCore → filmstrip real en Godot → mirar → corregir una sola cosa → repetir → revisión independiente**

- **`effekseer-vfx`** — la habilidad de creación: reglas de oficio, convenciones verificadas de los motores Effekseer/Godot, unas 30
  primitivas de capa combinables, un linter estático, el compilador oficial de EffekseerCore con verificación por relectura save/open, un Godot Lab que
  escenifica cada efecto como un intercambio entre dos maniquíes, captura de filmstrips con marcas de píxeles, historial de iteraciones y
  evidencias a prueba de manipulación que vinculan cada revisión con la compilación exacta que vio.
- **`vfx-review`** — la habilidad de revisión: un agente distinto puntúa el filmstrip según una rúbrica fija sin ver la
  receta, porque el autor nunca califica su propio trabajo.
- **Ejemplos** — dieciséis efectos terminados con sus briefs y texturas: cuatro parejas a distancia (fuego, hielo, veneno, oscuridad:
  proyectil + impacto), uno de cada tipo de golpe, tajo, carga, escudo y curación, y un set kaiju (una carga que asciende por las
  placas dorsales, un rayo atómico que se puede barrer, una explosión fotográfica), además de tres casos diagnosticados con su antes y después.
- **Efectos grandes y realistas** — `scale='kaiju'` compila una receta a escala de personaje 40 veces más grande y 2,5 veces más lenta
  (tamaños, velocidades, gravedad, presupuestos y la cámara de revisión se ajustan en consecuencia); `beam()` crea un rayo sostenido cuyo punto final el
  juego mueve en cada fotograma (`Vfx.beam()` → `aim()` → `release()`); `charge_chain()` enciende arcos a lo largo de una cadena de
  puntos; flipbooks fotográficos de fuego, hollín y humo; partículas suaves verificadas en Forward+.
- **Combos, blockout y formas estilizadas** — un brief de secuencia vincula varios efectos a los tiempos de una
  animación de personaje y organiza el trabajo en blockout → detalle → pulido (una revisión independiente del blockout debe aprobarse antes de cualquier
  trabajo de texturas); las capturas pueden venir del propio juego; las referencias incluyen listas de qué tomar de ellas, que el revisor comprueba; `vfx
  paintover` convierte un fotograma capturado en un prompt de edición de imagen para obtener un objetivo conceptual. Primitivas estilizadas de bordes duros
  (`spiral_ribbons`, `spike_crown`, `speed_streaks`, `stylized_pair`, `sparkle`), plantillas de máscaras en escala de grises y
  feedback de pantalla (`screen=`: sacudida, impact frame, hit-stop) que el Lab reproduce y que `Vfx.screen_cue` entrega al juego.

## Tres formas de crear un efecto (novedad de la 0.3)

Se elige por efecto; nada obliga a usar una sola forma.

| Forma | Cómo | Se reproduce en |
|---|---|---|
| **Procedural** | primitivas en capas en una receta de Python, texturas pintadas, compilación con EffekseerCore, revisión en Godot (todo lo descrito arriba) | Effekseer → Godot |
| **Flipbook de vídeo** | un modelo de imagen a vídeo (verificado con Seedance 2.5; sirve cualquier modelo que admita primer y último fotograma) pinta el movimiento sobre fondo negro; `vfx video-flipbook` hace el keying, recorta, enmascara y empaqueta el clip, y `vfx video-grade` da a todas las hojas de un elemento el mismo aspecto cel-shaded | Unity (URP), o Effekseer → Godot |
| **Combinada** | la hoja es la capa principal de una receta (`video_body(...)`); las primitivas añaden el destello de contacto, chispas, anillos, grietas, decals y distorsión por calor | Effekseer → Godot, Unity |

**Lo que antes no era posible y ahora sí:**

- **Cambios de forma continuos.** Una columna de agua que sale disparada hacia arriba, eleva al objetivo por los aires y se desploma como lluvia;
  una bola de fuego que estalla y se revuelve hasta convertirse en humo gris; un orbe cuyas llamas se agitan en un bucle sin costuras. Las primitivas escalan,
  desvanecen, desplazan y erosionan una imagen; no pueden convertir fuego en humo dentro de una misma silueta. Un modelo de vídeo dibuja todos
  los fotogramas intermedios.
- **Un aspecto de anime pintado a mano en movimiento**, coherente en todo un set de elementos: una rampa de valores por elemento ajusta
  todas las hojas a los mismos escalones planos (borde oscuro, cuerpo, luz, núcleo incandescente).
- **Unity.** Antes la habilidad llegaba solo hasta Godot. `vfx unity-install <UnityProject>` añade un paquete de runtime para URP
  (habilidades `ElementProfile` basadas en datos con lanzamiento como proyectil, rayo instantáneo o erupción desde el suelo, partículas en capas,
  hit-stop, sacudida de cámara, elevación del objetivo) y sus texturas procedurales; `vfx unity-export` copia una hoja con su cuadrícula; tres
  opciones de menú (o un único comando en modo batch que un agente puede ejecutar) convierten las hojas en una habilidad jugable y una escena de demostración.
- **Reproducible a partir de una frase.** El prompt de cada clip y los parámetros de cada hoja quedan registrados en
  `vfx/video_prompts.json`, de modo que un agente puede reconstruir o variar una hoja con exactitud. Pide: *"Crea una habilidad de columna de agua a partir de un
  flipbook de vídeo y configúrala en mi proyecto de Unity."*

Guía: [`references/video-flipbook.md`](skills/effekseer-vfx/references/video-flipbook.md). La habilidad solo distribuye la
técnica: los clips, hojas y personajes que generes se quedan en tu propio proyecto.

## Requisitos

| Modo | Qué puedes hacer | Requiere |
|---|---|---|
| authoring | escribir briefs y recetas, pasar el linter, procesar y medir texturas | Python 3.11+ o [uv](https://docs.astral.sh/uv/) en macOS, Linux o Windows (el Python 3.9 que trae macOS es demasiado antiguo) |
| build | compilar `.efkefc` / `.efk` con el EffekseerCore oficial | **macOS en Apple silicon** o **Windows x64**, conexión de red para la primera instalación (~250 MB en `~/.cache/effekseer-vfx`) |
| render | revisión de filmstrips en Godot, Lab, vista previa, empaquetado | lo anterior + [Godot 4](https://godotengine.org) (Forward+) en el `PATH` o en `GODOT`; `ffmpeg` para clips de referencia y grabaciones |
| flipbooks de vídeo | comandos `video-*` | modo authoring + `ffmpeg`; clips de cualquier modelo de imagen a vídeo |
| Unity | reproducir hojas como habilidades de elemento | Unity 6 (6000.0+) con URP 17; verificado en 6000.5 |

Build y render están verificados en macOS ARM64 (Effekseer Core 1.80.7, EffekseerForGodot4 1.80.5.1, Godot 4.7, .NET 9)
y en Windows 11 x64 (las mismas versiones, Godot 4.7.2). En Windows ARM64 la instalación obtiene el runtime de .NET correspondiente, pero
no está verificado. Linux ejecuta el modo authoring; su ruta de build no está verificada.

En Windows, todos los comandos `sh <skill>/scripts/...` de abajo también funcionan desde Git Bash (el que usa Claude Code); desde cmd o
PowerShell, usa `<skill>\scripts\vfx.cmd` en lugar de `vfx` y
`powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1` en lugar de `setup.sh`.

## Instalación

La forma más sencilla: dale la URL de este repositorio a tu agente de programación y pídele que instale la habilidad. Los pasos que
sigue están en [Para agentes: instalar desde esta URL](#para-agentes-instalar-desde-esta-url). O instálala tú mismo:

**Claude Code** (escribe esto en Claude Code)

```text
/plugin marketplace add kanaworksai-hue/effekseer-vfx-skill
/plugin install effekseer-vfx@effekseer-vfx
```

**Codex** (pídelo en un chat de Codex; las habilidades se instalan en `~/.codex/skills`, o en `$CODEX_HOME/skills`, y se
usan a partir del siguiente turno o de una nueva sesión)

```text
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/effekseer-vfx
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/vfx-review
```

**Otros agentes** (Cursor, Gemini CLI, Copilot, OpenCode, ...)

```sh
npx skills add kanaworksai-hue/effekseer-vfx-skill
```

O copia `skills/effekseer-vfx` y `skills/vfx-review` en la carpeta de habilidades de tu agente (`~/.claude/skills/`,
`.agents/skills/`, ...). Cada carpeta de habilidad
incluye su propio `LICENSE` (y `effekseer-vfx`, su `THIRD_PARTY_NOTICES.md`), así que una carpeta copiada los conserva.

### Para agentes: instalar desde esta URL

1. **Obtén los archivos.** Si tu host tiene un instalador de plugins o de habilidades, úsalo preferentemente (los comandos de arriba); un comando de barra
   como `/plugin` debe escribirlo el usuario, así que muéstraselo. Si no, clona el repositorio y copia las dos carpetas de
   habilidades en tu carpeta de habilidades, sin cambiarles el nombre: `git clone --depth 1 <URL de este repositorio>` y luego copia
   `skills/effekseer-vfx` y `skills/vfx-review` a `~/.claude/skills/` (Claude Code, todos los proyectos),
   `<project>/.claude/skills/` (Claude Code, un solo proyecto), `~/.codex/skills/` (Codex; `$CODEX_HOME/skills` si está definido) o
   la carpeta de habilidades de tu host (por ejemplo `.agents/skills/`).
   No copies nada más; las habilidades son autocontenidas y de solo lectura en tiempo de ejecución.
2. **Cárgalas.** Si las habilidades todavía no aparecen en tu lista de habilidades, pide al usuario que inicie una nueva sesión.
3. **Comprueba la máquina.** Desde el proyecto de juego del usuario, ejecuta `sh <skill>/scripts/vfx doctor` (`<skill>` es la
   carpeta `effekseer-vfx` instalada; en Windows fuera de Git Bash, `<skill>\scripts\vfx.cmd doctor`) y sigue sus
   pasos `next`.
4. **Pregunta antes de descargar.** `sh <skill>/scripts/setup.sh` (Windows: `setup.ps1`; el comando exacto está en el
   `next` de `doctor`) instala la cadena de herramientas en `~/.cache/effekseer-vfx`
   (unos 250 MB en macOS ARM64 y Windows x64; `--authoring-only` en el resto), y el primer `vfx init` descarga el plugin oficial
   de Effekseer para Godot (unos 34 MB). La instalación requiere Python 3.11+ o uv: si `doctor` no encuentra ninguno de los dos, pide al usuario
   que instale uno. Godot 4 nunca se instala en nombre del usuario; pídele que lo instale (o que te permita
   hacerlo) y que defina `GODOT` si no está en el `PATH`.
5. **Ejecuta Godot fuera del sandbox.** `vfx review`, `preview` y `showcase` abren una ventana de Godot en el escritorio del
   usuario. Un agente en sandbox (por ejemplo, Codex en su sandbox de espacio de trabajo) no puede abrirla: ejecuta esos comandos con
   la aprobación del usuario fuera del sandbox; si tu host no puede salir de su sandbox, dale al usuario el comando exacto para
   ejecutarlo en una terminal de su escritorio. Una revisión que no renderiza ningún fotograma se detiene tras unos 90 s con "rendered no frame"
   (lo más probable es que la ventana no se haya podido abrir; revisa la salida de Godot que incluye). `render: true` en `doctor` solo significa que
   se encontró Godot.
6. **Confirma que funciona.** Vuelve a ejecutar `vfx doctor` (`modes` debería mostrar lo que admite esta máquina) y luego sigue
   [Primeros pasos](#primeros-pasos). Informa de lo que funciona y de lo que falta; no afirmes que build o render funcionan en una
   máquina donde `doctor` indica que no.

## Primeros pasos

Pide a tu agente, dentro de tu proyecto de juego: *"Configura aquí la habilidad effekseer-vfx y enséñame el ejemplo de fuego."* Ejecutará:

```sh
sh <skill>/scripts/vfx doctor            # what this machine can do, and what to install
sh <skill>/scripts/setup.sh              # macOS ARM64 / Windows x64; use --authoring-only elsewhere (asks you first)
sh <skill>/scripts/vfx init              # creates vfx/ with the Godot Lab, materials and math textures
sh <skill>/scripts/vfx examples add fire
sh <skill>/scripts/vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
sh <skill>/scripts/vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
sh <skill>/scripts/vfx showcase          # play the library in the Lab
```

Después pide un efecto: *"Crea un impacto de rayo para un hechizo con objetivo, corto y seco, con descarga de retorno."* La
habilidad hace que el agente escriba un brief, solicite texturas pintadas a tu herramienta de generación de imágenes (o te las pida
a ti), escriba la receta, compile, revise los filmstrips durante varias rondas y entregue el resultado a un revisor independiente
antes de informar de que `effect-verify` ha pasado. Hasta que se envíe esa revisión independiente y se vuelva a ejecutar `vfx overview`,
`effect-verify` indica `verified: false` aunque el efecto se renderice correctamente; en ese punto, un agente debería informar de que
"compila y se renderiza" en lugar de "verificado". La cadena de herramientas se encuentra en `~/.cache/effekseer-vfx`; define
`EFFEKSEER_VFX_HOME` para ubicarla en otro lugar (consulta [la referencia de comandos](skills/effekseer-vfx/references/cli.md)).

## Generación de imágenes

Las formas pintadas complejas (humo, arcos de tajo, fuego, grietas, hielo, símbolos) deben venir de un modelo de generación de imágenes; la
habilidad nunca las simula con código. Si tu agente tiene una herramienta de imágenes integrada o conectada, la usa con los prompts que
registra en `vfx/texture_prompts.json`. Si no, te indica exactamente qué imagen generar y dónde guardarla.
Las formas matemáticas (resplandores, anillos, ruido, degradados, estelas, mapas de distorsión) se generan de forma procedural.

## Usar los efectos en un juego

Los efectos se generan como exportaciones de runtime `.efk` y fuentes `.efkefc` con un `vfx_manifest.json`. El proyecto de Godot generado
incluye una pequeña API:

```gdscript
var handle = Vfx.play("VFX_Fire_Explosion", position)
var shot = Vfx.launch("VFX_Projectile_Fire", from, to)
shot.arrived.connect(func(at): Vfx.play("VFX_Fire_Explosion", at))
```

Los rayos se apuntan en cada fotograma; el punto final lo controla el juego (un raycast, un hueso del objetivo):

```gdscript
var ray = Vfx.beam("VFX_Kaiju_Atomic_Beam", mouth, target)
ray.aim(mouth, new_target)   # each frame: sweep, follow the head
ray.release()                # narrows and fades out, then frees itself
```

Consulta [`skills/effekseer-vfx/references/godot.md`](skills/effekseer-vfx/references/godot.md) y, para gigantes y kaijus,
[`references/scale.md`](skills/effekseer-vfx/references/scale.md).

## Estructura del repositorio

```
skills/effekseer-vfx/      SKILL.md, references/ (craft, engine conventions, review...), scripts/ (vfx CLI and vfx.cmd,
                           setup.sh and setup.ps1, vfxkit, vendored effekseer_ai), assets/ (Godot Lab, materials, rubric,
                           brief schema, examples, unity/ URP package)
skills/vfx-review/         SKILL.md for the independent reviewer
docs/zh/, docs/ja/         Chinese and Japanese translations of the references
.claude-plugin/            Claude Code plugin and marketplace manifests
tests/                     pure-Python tests (no Core or Godot needed)
```

## Limitaciones

- Las métricas de revisión son heurísticas de píxeles sobre el viewport real, no mediciones de GPU ni de overdraw.
- El sistema de revisión controla un Godot en ventana en macOS y Windows; todavía no se admite la captura headless en Linux. En
  Windows, la ventana de Godot conserva el foco mientras captura (macOS devuelve el foco a tu aplicación).
- En Windows, las pruebas de seguridad de enlaces simbólicos requieren el Modo de desarrollador (o una shell de administrador) y se omiten sin él.
- Las puntuaciones de los ejemplos corresponden a una revisión independiente de los renders del Lab de cápsulas de la propia habilidad (dos de los dieciséis se calificaron como
  `iterate`); vuelve a compilarlos y revisarlos antes de confiar en ellas.
- Las partículas `soft` están verificadas en Forward+ (solo se desvanecen frente a la profundidad opaca); el renderizador Compatibility no tiene
  textura de profundidad y no puede usarlas.

## Desarrollo

```sh
sh skills/effekseer-vfx/scripts/setup.sh --authoring-only
~/.cache/effekseer-vfx/venv/bin/python -m pip install pytest
~/.cache/effekseer-vfx/venv/bin/python -m pytest -q tests
```

En Windows (PowerShell; quita `--authoring-only` para ejecutar también las pruebas de compilación de EffekseerCore):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File skills\effekseer-vfx\scripts\setup.ps1 --authoring-only
~\.cache\effekseer-vfx\venv\Scripts\python.exe -m pip install pytest   # a venv made by uv: uv pip install --python <that python.exe> pytest
~\.cache\effekseer-vfx\venv\Scripts\python.exe -X utf8 -m pytest -q tests
```

Las contribuciones que confirmen una nueva convención de motor deben añadirla a
`skills/effekseer-vfx/references/engine-conventions.md` junto con la forma en que se midió.

## Licencia y créditos

- **Este proyecto:** [MIT](LICENSE). Úsalo, modifícalo y distribúyelo, también con fines comerciales; conserva el aviso de copyright y la licencia en las copias del código.
- **Lo que creas con él:** los efectos, texturas, flipbooks y skills de Unity que construyes en tu proyecto son tuyos. Este repositorio no reclama nada sobre ellos.
- **Modelos de vídeo e imagen:** los clips e imágenes que generas (por ejemplo, con Seedance 2.5) se rigen por los términos de ese modelo, no por esta licencia. Revísalos antes de un uso comercial. Aquí no se distribuye nada de eso.
- **Componentes de terceros:** Effekseer, EffekseerForGodot4, .NET y el effekseer-ai incluido conservan sus propias licencias. Consulta [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Marca y ejemplos:** el nombre KanaWorks_AI, el logo y el personaje Kana son © 東京AI映像合同会社 (Tokyo AI Visuals LLC) y **no** están cubiertos por la licencia MIT. Los efectos, personajes e imágenes del banner y de los vídeos promocionales son ejemplos: no se incluyen ni se licencian. Consulta [docs/brand](docs/brand/README.md).

Effekseer, Godot y Unity son marcas de sus respectivos propietarios. Este es un proyecto independiente, sin afiliación ni respaldo de ellos.

<br>

<div align="center">

<a href="https://x.com/KanaWorks_AI"><img src="docs/brand/kanaworks-logo.png" width="130" alt="KanaWorks_AI"></a>

<p><b>Hecho con ♥ por <a href="https://x.com/KanaWorks_AI">KanaWorks_AI</a></b> · <a href="https://x.com/KanaWorks_AI">@KanaWorks_AI</a> on X</p>

<p><sub>Si la skill te ahorra tiempo, una ⭐ mantiene las actualizaciones y ayuda a que otros la encuentren. Más proyectos: <a href="https://github.com/kanaworksai-hue">github.com/kanaworksai-hue</a></sub></p>

</div>
