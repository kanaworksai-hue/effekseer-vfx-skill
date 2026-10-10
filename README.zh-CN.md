# effekseer-vfx-skill

[English](README.md) | 简体中文 | [日本語](README.ja.md)

> 中文文档是英文原文的翻译，仅供阅读参考。agent 实际加载的是 `skills/` 下的英文文件（`SKILL.md` 与 `references/*.md`）；两者不一致时以英文为准。中文译文索引见 [docs/zh/README.md](docs/zh/README.md)。

一组 agent 技能，让编程 agent（Claude Code、Codex、Cursor、Gemini CLI、GitHub Copilot、OpenCode 以及其他
[Agent Skills](https://agentskills.io) 宿主）像 VFX 美术迭代那样，用代码制作实时游戏特效：

**设计简报 → 纹理 → Python 配方 → EffekseerCore 构建 → 真实 Godot 连拍 → 看图 → 修一处 → 重复 → 独立评审**

- **`effekseer-vfx`** —— 制作技能：制作规则、经过实测的 Effekseer/Godot 引擎约定、约 30 个可组合的层基元、
  静态检查器、带 save/open 回读的官方 EffekseerCore 编译器、把每个效果演成两个假人之间一次交锋的 Godot Lab、
  带像素 flag 的连拍采集、迭代历史，以及把评审绑定到它所看构建的防篡改证据。
- **`vfx-review`** —— 评审技能：由另一个 agent 在看不到配方的情况下，按固定评分表给连拍图打分，因为作者从不给自己的作品打分。
- **示例** —— 十三个完成的效果，附设计简报和纹理：四组远程配对（火、冰、毒、暗：飞行体 + 命中），以及打击、斩击、蓄力、护盾、治疗各一个；另有三个前后对照的诊断教案。

## 环境要求

| 模式 | 能做什么 | 需要 |
|---|---|---|
| authoring | 写简报和配方、lint、处理和测量纹理 | macOS 或 Linux 上的 Python 3.11+ 或 [uv](https://docs.astral.sh/uv/)（macOS 自带的 Python 3.9 太旧；Windows 请用 WSL） |
| build | 通过官方 EffekseerCore 编译 `.efkefc` / `.efk` | **Apple 芯片的 macOS**，首次安装需要联网（约 250 MB，装到 `~/.cache/effekseer-vfx`） |
| render | Godot 连拍复查、Lab、预览、打包 | 以上全部 + 位于 `PATH` 或 `GODOT` 中的 [Godot 4](https://godotengine.org)（Forward+）；参考视频和录像需要 `ffmpeg` |

build 和 render 只在 macOS ARM64 上验证过（Effekseer Core 1.80.7、EffekseerForGodot4 1.80.5.1、Godot 4.7、
.NET 9）。Linux 可以运行 authoring 模式，构建路径未经验证。

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
3. **检查本机。** 在用户的游戏项目里运行 `sh <skill>/scripts/vfx doctor`（`<skill>` 是安装好的 `effekseer-vfx` 目录），按它的 `next` 步骤操作。
4. **下载前先询问。** `sh <skill>/scripts/setup.sh` 把工具链装到 `~/.cache/effekseer-vfx`（macOS ARM64 上约 250 MB；其他系统用
   `--authoring-only`），第一次 `vfx init` 还会下载官方 Effekseer Godot 插件（约 34 MB）。它需要 Python 3.11+ 或 uv：`doctor` 报告两者都没有时，请用户安装其中一个。Godot 4 永远不会替用户安装；
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
sh <skill>/scripts/setup.sh              # macOS ARM64; use --authoring-only elsewhere (asks you first)
sh <skill>/scripts/vfx init              # creates vfx/ with the Godot Lab, materials and math textures
sh <skill>/scripts/vfx examples add fire
sh <skill>/scripts/vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
sh <skill>/scripts/vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
sh <skill>/scripts/vfx showcase          # play the library in the Lab
```

（各命令作用依次为：检查本机能力与需要安装的内容；安装依赖（macOS ARM64，其他系统用 `--authoring-only`，会先征得你同意）；
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

参见 [`skills/effekseer-vfx/references/godot.md`](skills/effekseer-vfx/references/godot.md)（中文译文：
[docs/zh/references/godot.md](docs/zh/references/godot.md)）。

## 仓库结构

```
skills/effekseer-vfx/      SKILL.md, references/ (craft, engine conventions, review...), scripts/ (vfx CLI, setup.sh,
                           vfxkit, vendored effekseer_ai), assets/ (Godot Lab, materials, rubric, brief schema, examples)
skills/vfx-review/         SKILL.md for the independent reviewer
docs/zh/, docs/ja/         Chinese and Japanese translations of the references
.claude-plugin/            Claude Code plugin and marketplace manifests
tests/                     pure-Python tests (no Core or Godot needed)
```

各目录：`skills/effekseer-vfx/` 含 `SKILL.md`、`references/`（制作规则、引擎约定、复查等）、`scripts/`（`vfx` CLI、
`setup.sh`、`vfxkit`、内置的 `effekseer_ai`）和 `assets/`（Godot Lab、材质、评分表、简报 schema、示例）；
`skills/vfx-review/` 是独立评审用的 `SKILL.md`；`docs/zh/`、`docs/ja/` 是参考文档的中文和日文译文；
`.claude-plugin/` 是 Claude Code 插件与 marketplace 清单；`tests/` 是纯 Python 测试（不需要 Core 或 Godot）。

## 限制

- 复查指标是基于真实 viewport 的像素启发式，不是 GPU 或 overdraw 测量。
- 复查工具驱动的是 macOS 上带窗口的 Godot；暂不支持无头 Linux 采集。
- 示例分数来自对 skill 自带胶囊 Lab 渲染的独立评审（十三个中有两个被判为 `iterate`）；依赖它们之前请重新构建并复查。
- `soft` 粒子在 Forward+ Lab 中未经验证，未被使用。

## 开发

```sh
sh skills/effekseer-vfx/scripts/setup.sh --authoring-only
~/.cache/effekseer-vfx/venv/bin/python -m pip install pytest
~/.cache/effekseer-vfx/venv/bin/python -m pytest -q tests
```

确认了新引擎约定的贡献，应把它连同测量方法一起写进
`skills/effekseer-vfx/references/engine-conventions.md`（英文原文）。

## 许可证

MIT，见 [LICENSE](LICENSE)。第三方组件与下载内容：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
Effekseer 和 Godot 是其各自所有者的商标；本项目与它们没有关联。

作者：KanaWorks_AI（X：[@KanaWorks_AI](https://x.com/KanaWorks_AI)）。
