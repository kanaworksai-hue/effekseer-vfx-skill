# effekseer-vfx-skill

<div align="center">

<img src="docs/assets/banner-zh.jpg" alt="VFX Skill：让编程 agent 为 Effekseer、Godot、Unity 制作实时游戏特效" width="820">

<p>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-6b4dff?style=flat-square"></a>
  <a href="https://agentskills.io"><img alt="Agent Skill" src="https://img.shields.io/badge/Agent_Skill-Claude_Code_·_Codex_·_Cursor-19b8d6?style=flat-square"></a>
  <img alt="Effekseer 1.80" src="https://img.shields.io/badge/Effekseer-1.80-ff7d2e?style=flat-square">
  <img alt="Godot 4" src="https://img.shields.io/badge/Godot-4-478cbf?style=flat-square&logo=godotengine&logoColor=white">
  <img alt="Unity 6 URP" src="https://img.shields.io/badge/Unity_6-URP-111?style=flat-square&logo=unity">
  <a href="https://github.com/kanaworksai-hue/effekseer-vfx-skill/stargazers"><img alt="GitHub stars" src="https://img.shields.io/github/stars/kanaworksai-hue/effekseer-vfx-skill?style=flat-square&logo=github&label=stars&color=f5c518"></a>
</p>

<p><a href="https://github.com/kanaworksai-hue"><img src="docs/brand/kanaworks-mark.png" height="22" alt="" align="absmiddle"></a>&nbsp;<a href="https://github.com/kanaworksai-hue"><b>KanaWorks_AI 出品</b></a></p>

[English](README.md) | 简体中文 | [日本語](README.ja.md) | [한국어](README.ko.md) | [Português (Brasil)](README.pt-BR.md) | [Español](README.es.md)

</div>

> 中文文档是英文原文的翻译，仅供阅读参考。agent 实际加载的是 `skills/` 下的英文文件（`SKILL.md` 与 `references/*.md`）；两者不一致时以英文为准。中文译文索引见 [docs/zh/README.md](docs/zh/README.md)。

一组 agent 技能，让编程 agent（Claude Code、Codex、Cursor、Gemini CLI、GitHub Copilot、OpenCode 以及其他
[Agent Skills](https://agentskills.io) 宿主）像 VFX 美术迭代那样，用代码制作实时游戏特效：

**设计简报 → 纹理 → Python 配方 → EffekseerCore 构建 → 真实 Godot 连拍 → 看图 → 修一处 → 重复 → 独立评审**

- **`effekseer-vfx`** —— 制作技能：制作规则、经过实测的 Effekseer/Godot 引擎约定、约 30 个可组合的层基元、
  静态检查器、带 save/open 回读的官方 EffekseerCore 编译器、把每个效果演成两个假人之间一次交锋的 Godot Lab、
  带像素 flag 的连拍采集、迭代历史，以及把评审绑定到它所看构建的防篡改证据。
- **`vfx-review`** —— 评审技能：由另一个 agent 在看不到配方的情况下，按固定评分表给连拍图打分，因为作者从不给自己的作品打分。
- **示例** —— 十六个完成的效果，附设计简报和纹理：四组远程配对（火、冰、毒、暗：飞行体 + 命中），打击、斩击、蓄力、护盾、治疗各一个，以及一个怪兽套组（沿背鳍骨板攀升的蓄力、可以扫动的原子光束、照片级的爆炸）；另有三个前后对照的诊断教案。
- **大型与写实效果** —— `scale='kaiju'` 把角色尺度的配方构建得大 40 倍、慢 2.5 倍（尺寸、速度、重力、预算和复查镜头全都随之变化）；`beam()` 制作一条持续光束，终点由游戏每帧移动（`Vfx.beam()` → `aim()` → `release()`）；`charge_chain()` 沿一串点点亮电弧；照片级的火焰、烟灰和烟雾序列帧；软粒子已在 Forward+ 中验证。
- **连段、灰盒与风格化形状** —— 序列简报把多个特效绑定到角色动画的节拍上，按灰盒 → 细节 → 打磨推进（贴图工作之前必须先通过独立的灰盒评审）；截图可以直接来自游戏本身；参考资料附带“偷什么”清单，由评审逐项检查；`vfx paintover` 把截到的关键帧变成概念图用的图像编辑提示词。硬边风格化原语（`spiral_ribbons`、`spike_crown`、`speed_streaks`、`stylized_pair`、`sparkle`）、灰度遮罩模板，以及屏幕反馈（`screen=`：震屏、冲击帧、顿帧，由 Lab 播放，并通过 `Vfx.screen_cue` 交给游戏）。

## 三种做法（0.3 新增）

每个特效自己选，不强制任何一种。

| 做法 | 怎么做 | 在哪里播放 |
|---|---|---|
| **程序化** | Python 配方叠加图元、手绘贴图、EffekseerCore 编译、Godot 审查（即上面的全部内容） | Effekseer → Godot |
| **视频序列帧** | 图生视频模型（用 Seedance 2.5 验证；任何支持首尾帧的模型都行）在黑底上画出运动；`vfx video-flipbook` 负责抠像、统一裁切、遮罩并拼成图集，`vfx video-grade` 让同一元素的所有图集都是同一套赛璐珞色阶 | Unity（URP），或 Effekseer → Godot |
| **联合** | 图集作为配方的主体层（`video_body(...)`），接触闪光、火花、冲击环、裂纹、贴花和热扭曲由图元补上 | Effekseer → Godot、Unity |

**以前做不到、现在能做到的：**

- **连续变形的特效。** 水柱冲起、把目标托上半空、再化作雨水落下；火球炸开后翻滚着变成灰烟；火焰翻卷的球体无缝循环。图元能缩放、淡出、滚动、侵蚀一张图，却没法在同一个轮廓里把火变成烟；视频模型把每一帧中间态都画出来了。
- **会动的手绘二次元质感，并且整套元素统一。** 每个元素一条明度色阶，把所有图集压成同样的平涂层次（暗边、主体、亮部、高热核心）。
- **Unity。** 以前只能到 Godot。`vfx unity-install <UnityProject>` 会加入一个 URP 运行时包（数据驱动的 `ElementProfile` 技能：飞行弹道、瞬间命中、地面喷发三种出手方式，分层粒子，顿帧、震屏、把目标托起）和程序生成的贴图；`vfx unity-export` 把图集连同网格信息拷进去；三个菜单（或 agent 可直接运行的一条批处理命令）就能把图集变成可玩的技能和演示场景。
- **一句话就能复现。** 每段视频的提示词和每张图集的参数都记录在 `vfx/video_prompts.json`，agent 可以精确重做或改出变体。比如对 agent 说：*「用视频序列帧做一个水柱技能，并装进我的 Unity 项目。」*

指南：[`references/video-flipbook.md`](skills/effekseer-vfx/references/video-flipbook.md)。本 skill 只开源技术；你自己生成的视频、图集和角色都留在你自己的项目里。

## 环境要求

| 模式 | 能做什么 | 需要 |
|---|---|---|
| authoring | 写简报和配方、lint、处理和测量纹理 | macOS、Linux 或 Windows 上的 Python 3.11+ 或 [uv](https://docs.astral.sh/uv/)（macOS 自带的 Python 3.9 太旧） |
| build | 通过官方 EffekseerCore 编译 `.efkefc` / `.efk` | **Apple 芯片的 macOS** 或 **Windows x64**，首次安装需要联网（约 250 MB，装到 `~/.cache/effekseer-vfx`） |
| render | Godot 连拍复查、Lab、预览、打包 | 以上全部 + 位于 `PATH` 或 `GODOT` 中的 [Godot 4](https://godotengine.org)（Forward+）；参考视频和录像需要 `ffmpeg` |
| 视频序列帧 | `video-*` 命令 | authoring 模式 + `ffmpeg`；视频可来自任意图生视频模型 |
| Unity | 把图集作为元素技能播放 | Unity 6（6000.0+）+ URP 17；已在 6000.5 验证 |

build 和 render 已在 macOS ARM64（Effekseer Core 1.80.7、EffekseerForGodot4 1.80.5.1、Godot 4.7、.NET 9）和
Windows 11 x64（版本相同，Godot 4.7.2）上验证。Windows ARM64 的安装脚本会装上对应的 .NET 运行时，但未经验证。
Linux 可以运行 authoring 模式，构建路径未经验证。

在 Windows 上，下文每条 `sh <skill>/scripts/...` 命令也都能在 Git Bash（Claude Code 使用的就是它）里运行；在 cmd 或
PowerShell 里，`vfx` 请用 `<skill>\scripts\vfx.cmd`，`setup.sh` 请用
`powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1`。

## 安装

最简单的方式：把本仓库的 URL 交给你的编程 agent，让它安装这个技能。它要遵循的步骤见
[给 agent：通过这个 URL 安装](#给-agent通过这个-url-安装)。也可以自己安装：

**Claude Code**（在 Claude Code 里输入）

```text
/plugin marketplace add kanaworksai-hue/effekseer-vfx-skill
/plugin install effekseer-vfx@effekseer-vfx
```

**Codex**（在 Codex 对话里发送；技能装到 `~/.codex/skills`，设置了 `$CODEX_HOME` 时是 `$CODEX_HOME/skills`，
下一轮对话或新会话起生效）

```text
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/effekseer-vfx
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/vfx-review
```

**其他 agent**（Cursor、Gemini CLI、Copilot、OpenCode 等）

```sh
npx skills add kanaworksai-hue/effekseer-vfx-skill
```

也可以把 `skills/effekseer-vfx` 和 `skills/vfx-review` 复制到 agent 的技能目录（`~/.claude/skills/`、
`.agents/skills/` 等）。每个技能目录都自带 `LICENSE`（`effekseer-vfx` 还带 `THIRD_PARTY_NOTICES.md`），单独复制也不会丢失。

### 给 agent：通过这个 URL 安装

1. **获取文件。** 宿主有插件或技能安装器时优先用它（上面的命令）；`/plugin` 这类斜杠命令必须由用户自己输入，请把命令展示给用户。
   否则克隆仓库，把两个技能目录按原名复制到技能目录：`git clone --depth 1 <本仓库 URL>`，再把 `skills/effekseer-vfx` 和
   `skills/vfx-review` 复制到 `~/.claude/skills/`（Claude Code，所有项目）、`<project>/.claude/skills/`（Claude Code，单个项目）、
   `~/.codex/skills/`（Codex；设置了 `$CODEX_HOME` 时是 `$CODEX_HOME/skills`）或宿主的技能目录（例如 `.agents/skills/`）。不要复制其他内容；技能是自包含的，运行时只读。
2. **加载。** 如果技能还没出现在技能列表里，请用户新开一个会话。
3. **检查本机。** 在用户的游戏项目里运行 `sh <skill>/scripts/vfx doctor`（`<skill>` 是安装好的 `effekseer-vfx` 目录；在 Windows 上，不在 Git Bash 里时用
   `<skill>\scripts\vfx.cmd doctor`），按它的 `next` 步骤操作。
4. **下载前先询问。** `sh <skill>/scripts/setup.sh`（Windows：`setup.ps1`，具体命令见 `doctor` 的 `next`）把工具链装到
   `~/.cache/effekseer-vfx`（macOS ARM64 和 Windows x64 上约 250 MB；其他系统用 `--authoring-only`），第一次 `vfx init` 还会下载官方 Effekseer Godot 插件（约 34 MB）。它需要 Python 3.11+ 或 uv：`doctor` 报告两者都没有时，请用户安装其中一个。Godot 4 永远不会替用户安装；
   请用户自行安装（或允许你安装），不在 `PATH` 上时设置 `GODOT`。
5. **在沙箱外运行 Godot。** `vfx review`、`preview` 和 `showcase` 会在用户桌面上打开 Godot 窗口。处于沙箱中的 agent（例如在工作区沙箱里的 Codex）
   打不开窗口：请在用户批准后到沙箱外运行这些命令；如果宿主无法离开沙箱，就把完整命令交给用户，让用户在自己桌面的终端里运行。
   没有渲染出任何帧的 review 会在约 90 秒后以 "rendered no frame" 停止（最可能是窗口打不开，请结合它附带的 Godot 输出判断）；
   `doctor` 的 `render: true` 只表示找到了 Godot。
6. **确认可用。** 再运行一次 `vfx doctor`（`modes` 显示本机支持什么），然后按 [第一步](#第一步) 操作。如实报告哪些可用、缺什么；
   `doctor` 说不支持 build 或 render 的机器上，不要声称它们可用。

## 第一步

在你的游戏项目里对 agent 说：*"在这里配置 effekseer-vfx 技能，并给我看火焰示例。"* 它会运行：

```sh
sh <skill>/scripts/vfx doctor            # what this machine can do, and what to install
sh <skill>/scripts/setup.sh              # macOS ARM64 / Windows x64; use --authoring-only elsewhere (asks you first)
sh <skill>/scripts/vfx init              # creates vfx/ with the Godot Lab, materials and math textures
sh <skill>/scripts/vfx examples add fire
sh <skill>/scripts/vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
sh <skill>/scripts/vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
sh <skill>/scripts/vfx showcase          # play the library in the Lab
```

（各命令作用依次为：检查本机能力与需要安装的内容；安装依赖（macOS ARM64 / Windows x64，其他系统用 `--authoring-only`，会先征得你同意）；
创建包含 Godot Lab、材质和数学纹理的 `vfx/`；添加火焰示例；构建；复查；在 Lab 中播放效果库。）

然后提出一个效果需求：*"为指定目标的法术做一个落雷，短而锐利，带回击。"* 技能会让 agent 写简报、通过你的图像生成工具
请求手绘纹理（或向你索要），编写配方、构建、多轮复查连拍图，并在报告 `effect-verify` 通过之前把结果交给独立评审。在提交独立评审并重新运行 `vfx overview` 之前，即使效果渲染正常，`effect-verify` 也会显示 `verified: false`；此时 agent 应报告“能构建、能渲染”，而不是“已验证”。工具链默认装在 `~/.cache/effekseer-vfx`，设置 `EFFEKSEER_VFX_HOME` 可以换位置（见[命令参考](skills/effekseer-vfx/references/cli.md)）。

## 图像生成

复杂的手绘形状（烟、斩击弧、火焰、裂纹、冰、符号）必须来自图像生成模型；本技能从不用代码伪造它们。如果 agent 有内置或
已连接的图像工具，就用它生成，并把提示词记录在 `vfx/texture_prompts.json` 中；否则它会明确告诉你要生成哪张图、保存到哪里。
数学形状（光晕、环、噪声、渐变、拖尾、扰动图）由程序生成。

## 在游戏中使用效果

效果最终产出为 `.efk` 运行时导出文件和 `.efkefc` 源文件，并附带 `vfx_manifest.json`。生成的 Godot 项目包含一个小 API：

```gdscript
var handle = Vfx.play("VFX_Fire_Explosion", position)
var shot = Vfx.launch("VFX_Projectile_Fire", from, to)
shot.arrived.connect(func(at): Vfx.play("VFX_Fire_Explosion", at))
```

光束需要每帧瞄准；终点由游戏掌握（射线检测结果、目标骨骼）：

```gdscript
var ray = Vfx.beam("VFX_Kaiju_Atomic_Beam", mouth, target)
ray.aim(mouth, new_target)   # each frame: sweep, follow the head
ray.release()                # narrows and fades out, then frees itself
```

（`aim()` 每帧调用：扫动、跟随头部；`release()` 让光束变细并淡出，然后自行释放。）

参见 [`skills/effekseer-vfx/references/godot.md`](skills/effekseer-vfx/references/godot.md)（中文译文：
[docs/zh/references/godot.md](docs/zh/references/godot.md)）；巨人和怪兽另见
[`references/scale.md`](skills/effekseer-vfx/references/scale.md)（中文译文：[docs/zh/references/scale.md](docs/zh/references/scale.md)）。

## 仓库结构

```
skills/effekseer-vfx/      SKILL.md, references/ (craft, engine conventions, review...), scripts/ (vfx CLI and vfx.cmd,
                           setup.sh and setup.ps1, vfxkit, vendored effekseer_ai), assets/ (Godot Lab, materials, rubric,
                           brief schema, examples, unity/ URP package)
skills/vfx-review/         SKILL.md for the independent reviewer
docs/zh/, docs/ja/         Chinese and Japanese translations of the references
.claude-plugin/            Claude Code plugin and marketplace manifests
tests/                     pure-Python tests (no Core or Godot needed)
```

各目录：`skills/effekseer-vfx/` 含 `SKILL.md`、`references/`（制作规则、引擎约定、复查等）、`scripts/`（`vfx` CLI 和 `vfx.cmd`、
`setup.sh` 和 `setup.ps1`、`vfxkit`、内置的 `effekseer_ai`）和 `assets/`（Godot Lab、材质、评分表、简报 schema、示例）；
`skills/vfx-review/` 是独立评审用的 `SKILL.md`；`docs/zh/`、`docs/ja/` 是参考文档的中文和日文译文；
`.claude-plugin/` 是 Claude Code 插件与 marketplace 清单；`tests/` 是纯 Python 测试（不需要 Core 或 Godot）。

## 限制

- 复查指标是基于真实 viewport 的像素启发式，不是 GPU 或 overdraw 测量。
- 复查工具驱动的是 macOS 和 Windows 上带窗口的 Godot；暂不支持无头 Linux 采集。在 Windows 上，Godot 窗口在采集期间会一直
  占着焦点（macOS 会把焦点还给你的应用）。
- 在 Windows 上，符号链接安全测试需要开启开发者模式（或使用管理员 shell），否则会被跳过。
- 示例分数来自对 skill 自带胶囊 Lab 渲染的独立评审（十六个中有两个被判为 `iterate`）；依赖它们之前请重新构建并复查。
- `soft` 粒子已在 Forward+ 中验证（只会对不透明深度淡出）；Compatibility 渲染器没有深度纹理，无法使用它们。

## 开发

```sh
sh skills/effekseer-vfx/scripts/setup.sh --authoring-only
~/.cache/effekseer-vfx/venv/bin/python -m pip install pytest
~/.cache/effekseer-vfx/venv/bin/python -m pytest -q tests
```

在 Windows 上（PowerShell；去掉 `--authoring-only` 还会运行 EffekseerCore 构建测试）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File skills\effekseer-vfx\scripts\setup.ps1 --authoring-only
~\.cache\effekseer-vfx\venv\Scripts\python.exe -m pip install pytest   # a venv made by uv: uv pip install --python <that python.exe> pytest
~\.cache\effekseer-vfx\venv\Scripts\python.exe -X utf8 -m pytest -q tests
```

确认了新引擎约定的贡献，应把它连同测量方法一起写进
`skills/effekseer-vfx/references/engine-conventions.md`（英文原文）。

## 许可与署名

- **本项目：** [MIT](LICENSE)。只要在代码副本中保留版权声明和许可文本，就可以自由使用、修改和分发，包括商用。
- **你做出来的东西：** 你在自己项目里做的特效、贴图、序列帧和 Unity 技能归你所有，本仓库不主张任何权利。
- **视频 / 图像模型：** 你生成的视频和图片（例如用 Seedance 2.5）受该模型的使用条款约束，不受本许可约束。商用前请先确认。本仓库不分发任何生成内容。
- **第三方组件：** Effekseer、EffekseerForGodot4、.NET 以及内置的 effekseer-ai 各自遵循自己的许可，见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
- **品牌与作例：** KanaWorks_AI 名称、logo 和 Kana 形象版权归东京AI映像合同会社所有，**不在** MIT 授权范围内。横幅和宣传视频里的特效、角色和画面都是作例，不包含在仓库中，也不在授权范围内。见 [docs/brand](docs/brand/README.md)。

Effekseer、Godot 和 Unity 是其各自所有者的商标。本项目为独立项目，与它们没有关联，也未获其认可。

<br>

<div align="center">

<a href="https://x.com/KanaWorks_AI"><img src="docs/brand/kanaworks-logo.png" width="130" alt="KanaWorks_AI"></a>

<p><b>Made with ♥ by <a href="https://x.com/KanaWorks_AI">KanaWorks_AI</a></b> · <a href="https://x.com/KanaWorks_AI">@KanaWorks_AI</a> on X</p>

<p><sub>觉得有用的话点个 ⭐，这是持续更新的动力，也能让更多人发现它。更多项目： <a href="https://github.com/kanaworksai-hue">github.com/kanaworksai-hue</a></sub></p>

</div>
