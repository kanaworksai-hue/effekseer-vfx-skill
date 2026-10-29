# effekseer-vfx-skill

<div align="center">

<img src="docs/assets/banner-pt.jpg" alt="VFX Skill: seu agente de código cria VFX de jogo em tempo real para Effekseer, Godot e Unity" width="820">

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-6b4dff?style=flat-square"></a>
  <a href="https://agentskills.io"><img alt="Agent Skill" src="https://img.shields.io/badge/Agent_Skill-Claude_Code_·_Codex_·_Cursor-19b8d6?style=flat-square"></a>
  <img alt="Effekseer 1.80" src="https://img.shields.io/badge/Effekseer-1.80-ff7d2e?style=flat-square">
  <img alt="Godot 4" src="https://img.shields.io/badge/Godot-4-478cbf?style=flat-square&logo=godotengine&logoColor=white">
  <img alt="Unity 6 URP" src="https://img.shields.io/badge/Unity_6-URP-111?style=flat-square&logo=unity">
  <a href="https://github.com/kanaworksai-hue/effekseer-vfx-skill/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/kanaworksai-hue/effekseer-vfx-skill?style=flat-square&logo=github&label=stars&color=f5c518"></a>
</p>

<p><a href="https://github.com/kanaworksai-hue"><img src="docs/brand/kanaworks-mark.png" height="22" alt="" align="absmiddle"></a>&nbsp;<a href="https://github.com/kanaworksai-hue"><b>Um projeto KanaWorks_AI</b></a></p>

[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | Português (Brasil) | [Español](README.es.md)

</div>

> Este documento é uma tradução do README em inglês. Os agentes carregam os arquivos em inglês dentro de `skills/`; se houver divergência entre as versões, vale a versão em inglês.

Skills de agente que permitem que um agente de programação (Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, OpenCode e outros hosts compatíveis com
[Agent Skills](https://agentskills.io)) crie VFX de jogos em tempo real do mesmo jeito que um artista de VFX itera, só que em código:

**brief de design → texturas → receita em Python → build no EffekseerCore → filmstrip real no Godot → olhar → corrigir uma coisa → repetir → revisão independente**

- **`effekseer-vfx`** — a skill de criação: regras de ofício, convenções de engine do Effekseer/Godot já verificadas, cerca de 30 primitivas de camada combináveis, um linter estático, o compilador oficial EffekseerCore com verificação por releitura (save/open), um Godot Lab que encena cada efeito como uma troca entre dois dummies, captura de filmstrip com flags de pixel, histórico de iterações e evidências à prova de adulteração que vinculam uma revisão ao build exato que ela viu.
- **`vfx-review`** — a skill de revisão: um agente separado dá nota ao strip segundo uma rubrica fixa, sem ver a receita, porque o autor nunca avalia o próprio trabalho.
- **Exemplos** — dezesseis efeitos prontos, com briefs e texturas: quatro pares de longo alcance (fogo, gelo, veneno, trevas: projétil + impacto), um de cada para golpe, corte, carga, escudo e cura, e um conjunto kaiju (uma carga que sobe pelas placas dorsais, um raio atômico capaz de varrer a área, uma explosão fotográfica), além de três casos de antes/depois com diagnóstico.
- **Efeitos grandes e realistas** — `scale='kaiju'` gera uma receita em escala de personagem 40x maior e 2,5x mais lenta (tamanhos, velocidades, gravidade, orçamentos e a câmera de revisão acompanham); `beam()` cria um raio sustentado cujo ponto final o jogo move a cada frame (`Vfx.beam()` → `aim()` → `release()`); `charge_chain()` acende arcos ao longo de uma cadeia de pontos; flipbooks fotográficos de fogo, fuligem e fumaça; soft particles verificadas no Forward+.
- **Combos, blockout e formas estilizadas** — um brief de sequência amarra vários efeitos aos tempos de uma animação de personagem e conduz o trabalho pelas etapas blockout → detalhe → polimento (uma revisão independente do blockout precisa ser aprovada antes de qualquer trabalho de textura); as capturas podem vir do próprio jogo; as referências trazem listas do que "roubar", que o revisor confere; `vfx paintover` transforma um frame capturado em um prompt de edição de imagem para gerar uma referência de concept. Primitivas estilizadas de borda dura (`spiral_ribbons`, `spike_crown`, `speed_streaks`, `stylized_pair`, `sparkle`), templates de máscara em tons de cinza e feedback de tela (`screen=`: shake, impact frame, hit-stop) que o Lab reproduz e `Vfx.screen_cue` repassa ao jogo.

## Três formas de criar um efeito (novidade da 0.3)

Você escolhe por efeito; nada obriga a seguir um único caminho.

| Forma | Como | Roda em |
|---|---|---|
| **Procedural** | primitivas em camadas numa receita Python, texturas pintadas, build no EffekseerCore, revisão no Godot (tudo o que foi descrito acima) | Effekseer → Godot |
| **Flipbook de vídeo** | um modelo de imagem para vídeo (verificado com o Seedance 2.5; qualquer modelo que aceite primeiro e último frame serve) pinta o movimento sobre fundo preto; `vfx video-flipbook` faz o key, recorta, aplica máscara e monta a sheet, e `vfx video-grade` dá a todas as sheets de um elemento o mesmo visual cel-shaded | Unity (URP), ou Effekseer → Godot |
| **Combinada** | a sheet é a camada principal (body) de uma receita (`video_body(...)`); as primitivas adicionam o flash de contato, faíscas, anéis, rachaduras, decals e a distorção de calor (heat haze) | Effekseer → Godot, Unity |

**O que antes não era possível e agora é:**

- **Mudanças contínuas de forma.** Uma coluna d'água que dispara para cima, leva o alvo para o ar e desaba como chuva; uma bola de fogo que explode e se revolve em fumaça cinza; um orbe cujas chamas se agitam em um loop sem emendas. Primitivas escalam, fazem fade, rolam (scroll) e erodem uma imagem; elas não conseguem transformar fogo em fumaça dentro de uma mesma silhueta. Um modelo de vídeo desenha todos os in-betweens.
- **Um visual de anime pintado à mão, em movimento**, consistente em todo o conjunto de um elemento: uma rampa de valores por elemento ajusta todas as sheets aos mesmos degraus chapados (borda escura, corpo, luz, núcleo incandescente).
- **Unity.** Antes, a skill parava no Godot. `vfx unity-install <UnityProject>` adiciona um pacote de runtime para URP (skills `ElementProfile` orientadas a dados, com entrega por projétil, raio instantâneo e erupção do chão, partículas em camadas, hit-stop, tremor de tela, levantamento do alvo) e suas texturas procedurais; `vfx unity-export` copia uma sheet junto com o seu grid; três itens de menu (ou um único comando em batch mode que um agente pode executar) transformam sheets em uma skill jogável e em uma cena de demonstração.
- **Reproduzível a partir de uma frase.** O prompt de cada clipe e os parâmetros de cada sheet ficam registrados em `vfx/video_prompts.json`, então um agente pode reconstruir ou variar uma sheet com exatidão. Peça: *"Crie uma skill de coluna d'água a partir de um flipbook de vídeo e configure-a no meu projeto Unity."*

Guia: [`references/video-flipbook.md`](skills/effekseer-vfx/references/video-flipbook.md). A skill distribui apenas a técnica: os clipes, as sheets e os personagens que você gerar ficam no seu próprio projeto.

## Requisitos

| Modo | O que dá para fazer | Requer |
|---|---|---|
| authoring | escrever briefs e receitas, rodar o lint, processar e medir texturas | Python 3.11+ ou [uv](https://docs.astral.sh/uv/) em macOS, Linux ou Windows (o Python 3.9 que vem com o macOS é antigo demais) |
| build | compilar `.efkefc` / `.efk` pelo EffekseerCore oficial | **macOS em Apple silicon** ou **Windows x64**, conexão de rede na primeira configuração (~250 MB em `~/.cache/effekseer-vfx`) |
| render | revisão de filmstrip no Godot, Lab, preview, empacotamento | o item anterior + [Godot 4](https://godotengine.org) (Forward+) no `PATH` ou em `GODOT`; `ffmpeg` para clipes de referência e gravações |
| flipbooks de vídeo | comandos `video-*` | modo authoring + `ffmpeg`; clipes de qualquer modelo de imagem para vídeo |
| Unity | reproduzir sheets como skills de elemento | Unity 6 (6000.0+) com URP 17; verificado na 6000.5 |

Build e render estão verificados no macOS ARM64 (Effekseer Core 1.80.7, EffekseerForGodot4 1.80.5.1, Godot 4.7, .NET 9) e no Windows 11 x64 (as mesmas versões, Godot 4.7.2). No Windows ARM64, o setup instala o runtime .NET correspondente, mas a plataforma não foi verificada. No Linux roda o modo authoring; o caminho de build não foi verificado.

No Windows, todos os comandos `sh <skill>/scripts/...` abaixo também funcionam no Git Bash (o que o Claude Code usa); no cmd ou no PowerShell, use `<skill>\scripts\vfx.cmd` no lugar de `vfx` e
`powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1` no lugar de `setup.sh`.

## Instalação

O jeito mais simples: passe a URL deste repositório para o seu agente de programação e peça que ele instale a skill. Os passos que ele segue estão em [Para agentes: instalação a partir desta URL](#para-agentes-instalação-a-partir-desta-url). Ou instale você mesmo:

**Claude Code** (digite isto no Claude Code)

```text
/plugin marketplace add kanaworksai-hue/effekseer-vfx-skill
/plugin install effekseer-vfx@effekseer-vfx
```

**Codex** (peça em um chat do Codex; as skills vão para `~/.codex/skills`, ou `$CODEX_HOME/skills`, e passam a ser usadas a partir do próximo turno ou de uma nova sessão)

```text
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/effekseer-vfx
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/vfx-review
```

**Outros agentes** (Cursor, Gemini CLI, Copilot, OpenCode, ...)

```sh
npx skills add kanaworksai-hue/effekseer-vfx-skill
```

Ou copie `skills/effekseer-vfx` e `skills/vfx-review` para a pasta de skills do seu agente (`~/.claude/skills/`, `.agents/skills/`, ...). Cada pasta de skill traz o próprio `LICENSE` (e a `effekseer-vfx`, também o seu `THIRD_PARTY_NOTICES.md`), então uma pasta copiada continua com esses arquivos.

### Para agentes: instalação a partir desta URL

1. **Obtenha os arquivos.** Se o seu host tiver um instalador de plugins ou de skills, dê preferência a ele (os comandos acima); um slash command como `/plugin` precisa ser digitado pelo usuário, então mostre o comando a ele. Caso contrário, clone o repositório e copie as duas pastas de skill para a sua pasta de skills, mantendo os nomes: `git clone --depth 1 <URL deste repositório>`, depois copie `skills/effekseer-vfx` e `skills/vfx-review` para `~/.claude/skills/` (Claude Code, todos os projetos), `<project>/.claude/skills/` (Claude Code, um único projeto), `~/.codex/skills/` (Codex; `$CODEX_HOME/skills` se estiver definido) ou para a pasta de skills do seu host (por exemplo, `.agents/skills/`).
   Não copie mais nada; as skills são autocontidas e somente leitura em tempo de execução.
2. **Carregue as skills.** Se elas ainda não aparecerem na sua lista de skills, peça ao usuário que inicie uma nova sessão.
3. **Verifique a máquina.** A partir do projeto de jogo do usuário, rode `sh <skill>/scripts/vfx doctor` (`<skill>` é a pasta `effekseer-vfx` instalada; no Windows fora do Git Bash, `<skill>\scripts\vfx.cmd doctor`) e siga os passos indicados em `next`.
4. **Pergunte antes de baixar.** `sh <skill>/scripts/setup.sh` (Windows: `setup.ps1`; o comando exato está no `next` do `doctor`) instala o toolchain em `~/.cache/effekseer-vfx` (cerca de 250 MB no macOS ARM64 e no Windows x64; `--authoring-only` nas demais plataformas), e o primeiro `vfx init` baixa o plugin oficial do Effekseer para Godot (cerca de 34 MB). O setup precisa de Python 3.11+ ou uv: se o `doctor` não encontrar nenhum dos dois, peça ao usuário que instale um deles. O Godot 4 nunca é instalado automaticamente para o usuário; peça que ele o instale (ou que permita que você instale) e defina `GODOT` se ele não estiver no `PATH`.
5. **Rode o Godot fora do sandbox.** `vfx review`, `preview` e `showcase` abrem uma janela do Godot na área de trabalho do usuário. Um agente em sandbox (o Codex no sandbox do workspace, por exemplo) não consegue abrir essa janela: rode esses comandos fora do sandbox, com a aprovação do usuário; se o seu host não puder sair do sandbox, passe ao usuário o comando exato para ele rodar em um terminal na área de trabalho. Uma revisão que não renderiza nenhum frame é interrompida após cerca de 90 s com "rendered no frame" (o mais provável é que a janela não tenha conseguido abrir; confira a saída do Godot incluída na mensagem). `render: true` no `doctor` significa apenas que o Godot foi encontrado.
6. **Confirme que funciona.** Rode `vfx doctor` de novo (`modes` deve mostrar o que esta máquina suporta) e depois siga os [Primeiros passos](#primeiros-passos). Informe o que funciona e o que está faltando; não afirme que build ou render funcionam em uma máquina onde o `doctor` diz que não funcionam.

## Primeiros passos

Peça ao seu agente, dentro do seu projeto de jogo: *"Configure a skill effekseer-vfx aqui e me mostre o exemplo de fogo."* Ele vai rodar:

```sh
sh <skill>/scripts/vfx doctor            # what this machine can do, and what to install
sh <skill>/scripts/setup.sh              # macOS ARM64 / Windows x64; use --authoring-only elsewhere (asks you first)
sh <skill>/scripts/vfx init              # creates vfx/ with the Godot Lab, materials and math textures
sh <skill>/scripts/vfx examples add fire
sh <skill>/scripts/vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
sh <skill>/scripts/vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
sh <skill>/scripts/vfx showcase          # play the library in the Lab
```

Depois, peça um efeito: *"Crie um relâmpago para um feitiço com alvo, curto e seco, com descarga de retorno."* A skill faz o agente escrever um brief, pedir texturas pintadas à sua ferramenta de geração de imagens (ou pedir que você as forneça), escrever a receita, fazer o build, revisar os strips ao longo de várias rodadas e entregar o resultado a um revisor independente antes de reportar `effect-verify` como aprovado. Até que essa revisão independente seja enviada e `vfx overview` seja executado de novo, `effect-verify` indica `verified: false`, mesmo quando o efeito renderiza corretamente; nesse ponto, o agente deve reportar "compila e renderiza", e não "verificado". O toolchain fica em `~/.cache/effekseer-vfx`; defina `EFFEKSEER_VFX_HOME` para colocá-lo em outro lugar (veja [a referência de comandos](skills/effekseer-vfx/references/cli.md)).

## Geração de imagens

Formas pintadas complexas (fumaça, arcos de corte, fogo, rachaduras, gelo, símbolos) precisam vir de um modelo de geração de imagens; a skill nunca as simula com código. Se o seu agente tiver uma ferramenta de imagem integrada ou conectada, ele a usa com os prompts que registra em `vfx/texture_prompts.json`. Caso contrário, ele diz exatamente qual imagem você deve gerar e onde salvá-la.
Formas matemáticas (glows, anéis, ruído, gradientes, trails, mapas de distorção) são geradas proceduralmente.

## Usando os efeitos em um jogo

Os efeitos terminam como exports de runtime `.efk` e fontes `.efkefc`, acompanhados de um `vfx_manifest.json`. O projeto Godot gerado contém uma pequena API:

```gdscript
var handle = Vfx.play("VFX_Fire_Explosion", position)
var shot = Vfx.launch("VFX_Projectile_Fire", from, to)
shot.arrived.connect(func(at): Vfx.play("VFX_Fire_Explosion", at))
```

Os raios (beams) são mirados a cada frame; o ponto final é controlado pelo jogo (um ray cast, um bone do alvo):

```gdscript
var ray = Vfx.beam("VFX_Kaiju_Atomic_Beam", mouth, target)
ray.aim(mouth, new_target)   # each frame: sweep, follow the head
ray.release()                # narrows and fades out, then frees itself
```

Veja [`skills/effekseer-vfx/references/godot.md`](skills/effekseer-vfx/references/godot.md) e, para gigantes e kaiju,
[`references/scale.md`](skills/effekseer-vfx/references/scale.md).

## Estrutura do repositório

```
skills/effekseer-vfx/      SKILL.md, references/ (craft, engine conventions, review...), scripts/ (vfx CLI and vfx.cmd,
                           setup.sh and setup.ps1, vfxkit, vendored effekseer_ai), assets/ (Godot Lab, materials, rubric,
                           brief schema, examples, unity/ URP package)
skills/vfx-review/         SKILL.md for the independent reviewer
docs/zh/, docs/ja/         Chinese and Japanese translations of the references
.claude-plugin/            Claude Code plugin and marketplace manifests
tests/                     pure-Python tests (no Core or Godot needed)
```

## Limitações

- As métricas de revisão são heurísticas de pixel sobre o viewport real, não medições de GPU ou de overdraw.
- O harness de revisão controla um Godot em janela no macOS e no Windows; a captura headless no Linux ainda não é suportada. No Windows, a janela do Godot mantém o foco durante a captura (o macOS devolve o foco ao seu app).
- No Windows, os testes de segurança de symlinks precisam do Modo de Desenvolvedor (ou de um shell de administrador) e são pulados sem ele.
- As notas dos exemplos vêm de uma revisão independente dos renders da própria skill no Lab com cápsulas (dois dos dezesseis foram avaliados como `iterate`); refaça o build e a revisão antes de confiar nelas.
- As partículas `soft` estão verificadas no Forward+ (o fade acontece apenas contra a profundidade opaca); o renderer Compatibility não tem textura de profundidade e não consegue usá-las.

## Desenvolvimento

```sh
sh skills/effekseer-vfx/scripts/setup.sh --authoring-only
~/.cache/effekseer-vfx/venv/bin/python -m pip install pytest
~/.cache/effekseer-vfx/venv/bin/python -m pytest -q tests
```

No Windows (PowerShell; remova `--authoring-only` para rodar também os testes de build do EffekseerCore):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File skills\effekseer-vfx\scripts\setup.ps1 --authoring-only
~\.cache\effekseer-vfx\venv\Scripts\python.exe -m pip install pytest   # a venv made by uv: uv pip install --python <that python.exe> pytest
~\.cache\effekseer-vfx\venv\Scripts\python.exe -X utf8 -m pytest -q tests
```

Contribuições que confirmem uma nova convenção de engine devem adicioná-la a
`skills/effekseer-vfx/references/engine-conventions.md`, junto com a forma como ela foi medida.

## Licença e créditos

- **Este projeto:** [MIT](LICENSE). Use, modifique e distribua, inclusive comercialmente; mantenha o aviso de copyright e a licença junto às cópias do código.
- **O que você cria com ele:** os efeitos, texturas, flipbooks e skills de Unity que você constrói no seu projeto são seus. Este repositório não reivindica nada sobre eles.
- **Modelos de vídeo e imagem:** clipes e imagens que você gera (por exemplo, com Seedance 2.5) seguem os termos desse modelo, não esta licença. Confira antes de uso comercial. Nada disso é distribuído aqui.
- **Componentes de terceiros:** Effekseer, EffekseerForGodot4, .NET e o effekseer-ai incluído mantêm suas próprias licenças. Veja [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Marca e exemplos:** o nome KanaWorks_AI, o logo e a personagem Kana são © 東京AI映像合同会社 (Tokyo AI Visuals LLC) e **não** estão cobertos pela licença MIT. Os efeitos, personagens e imagens do banner e dos vídeos de divulgação são exemplos: não estão incluídos nem licenciados. Veja [docs/brand](docs/brand/README.md).

Effekseer, Godot e Unity são marcas de seus respectivos proprietários. Este é um projeto independente, sem afiliação ou endosso deles.

<br>

<div align="center">

<a href="https://x.com/KanaWorks_AI"><img src="docs/brand/kanaworks-logo.png" width="130" alt="KanaWorks_AI"></a>

<p><b>Feito com ♥ por <a href="https://x.com/KanaWorks_AI">KanaWorks_AI</a></b> · <a href="https://x.com/KanaWorks_AI">@KanaWorks_AI</a> on X</p>

<p><sub>Se a skill te poupa tempo, uma ⭐ mantém as atualizações vindo e ajuda outras pessoas a encontrá-la. Mais projetos: <a href="https://github.com/kanaworksai-hue">github.com/kanaworksai-hue</a></sub></p>

</div>
