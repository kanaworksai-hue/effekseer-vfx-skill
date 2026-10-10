# effekseer-vfx-skill

[English](README.md) | [简体中文](README.zh-CN.md) | 日本語

> 日本語のドキュメントは英語版の翻訳です。エージェントが実際に読み込むのは `skills/` 以下の英語ファイルで、内容が食い違う場合は英語版が正です。翻訳の一覧は [docs/ja/README.md](docs/ja/README.md) にあります。

コーディングエージェント（Claude Code、Codex、Cursor、Gemini CLI、GitHub Copilot、OpenCode など
[Agent Skills](https://agentskills.io) に対応したホスト）が、VFX アーティストと同じ反復の進め方で、リアルタイムのゲーム VFX をコードで制作できるようにするエージェントスキルです。

**デザインブリーフ → テクスチャ → Python レシピ → EffekseerCore ビルド → Godot 実レンダーのフィルムストリップ → 見る → 一つだけ直す → 繰り返す → 独立レビュー**

- **`effekseer-vfx`** — 制作スキル。クラフトルール、実測で確認済みの Effekseer/Godot エンジン規約、組み合わせて使える約 30 個のレイヤープリミティブ、静的 linter、save/open の読み戻し検証付きの公式 EffekseerCore コンパイラ、すべてのエフェクトを 2 体のダミー間のやり取りとして演出する Godot Lab、ピクセルフラグ付きのフィルムストリップ撮影、反復履歴、そしてレビューを実際に見たビルドへ結び付ける改ざん検知可能なエビデンスを備えています。
- **`vfx-review`** — レビュアースキル。作者は自分の作品を採点しないため、別のエージェントがレシピを見ずに、固定の評価基準でストリップを採点します。
- **サンプル** — 完成済みのエフェクト 13 種。ブリーフとテクスチャ付き：遠距離ペア 4 組（炎、氷、毒、闇：飛翔体 + 着弾）と、ヒット・斬撃・チャージ・シールド・ヒール各 1 種。前後比較の診断事例 3 件も付属。

## 動作要件

| モード | できること | 必要なもの |
|---|---|---|
| authoring | ブリーフとレシピの作成、lint、テクスチャの処理と計測 | macOS、Linux または Windows 上の Python 3.11+ または [uv](https://docs.astral.sh/uv/)（macOS 標準の Python 3.9 は古すぎます） |
| build | 公式 EffekseerCore による `.efkefc` / `.efk` のコンパイル | **Apple silicon の macOS** または **Windows x64**、初回セットアップ時のネットワーク接続（`~/.cache/effekseer-vfx` に約 250 MB） |
| render | Godot のフィルムストリップレビュー、Lab、プレビュー、パッケージング | 上記 + `PATH` 上または `GODOT` で指定した [Godot 4](https://godotengine.org)（Forward+）。リファレンスクリップと録画には `ffmpeg` |

build と render は macOS ARM64（Effekseer Core 1.80.7、EffekseerForGodot4 1.80.5.1、Godot 4.7、.NET 9）と Windows 11 x64（同じバージョン、Godot 4.7.2）で検証済みです。Windows ARM64 ではセットアップが対応する .NET ランタイムを入れますが、検証はされていません。Linux では authoring モードで動作し、build の経路は検証されていません。

Windows では、以下の `sh <skill>/scripts/...` コマンドはすべて Git Bash（Claude Code が使うもの）でも動作します。cmd や PowerShell からは、`vfx` には `<skill>\scripts\vfx.cmd` を、`setup.sh` には
`powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1` を使います。

## インストール

いちばん簡単な方法：このリポジトリの URL をコーディングエージェントに渡し、スキルのインストールを頼みます。エージェントが
従う手順は [エージェント向け：この URL からのインストール](#エージェント向けこの-url-からのインストール) にあります。自分でインストールする場合：

**Claude Code**（Claude Code で入力）

```text
/plugin marketplace add kanaworksai-hue/effekseer-vfx-skill
/plugin install effekseer-vfx@effekseer-vfx
```

**Codex**（Codex のチャットで依頼します。スキルは `~/.codex/skills`（`$CODEX_HOME` 設定時は `$CODEX_HOME/skills`）に入り、
次のターンか新しいセッションから使えます）

```text
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/effekseer-vfx
$skill-installer install https://github.com/kanaworksai-hue/effekseer-vfx-skill/tree/main/skills/vfx-review
```

**その他のエージェント**（Cursor、Gemini CLI、Copilot、OpenCode など）

```sh
npx skills add kanaworksai-hue/effekseer-vfx-skill
```

または `skills/effekseer-vfx` と `skills/vfx-review` を、使用するエージェントのスキルフォルダ（`~/.claude/skills/`、
`.agents/skills/` など）にコピーしてください。各スキルフォルダには `LICENSE`（`effekseer-vfx` には `THIRD_PARTY_NOTICES.md` も）が同梱されているため、フォルダ単体でコピーしても失われません。

### エージェント向け：この URL からのインストール

1. **ファイルを取得する。** ホストにプラグインやスキルのインストーラーがあればそれを優先します（上のコマンド）。`/plugin` のような
   スラッシュコマンドはユーザー自身が入力する必要があるので、コマンドをユーザーに示します。そうでなければリポジトリをクローンし、
   2 つのスキルフォルダを名前を変えずにスキルフォルダへコピーします：`git clone --depth 1 <このリポジトリの URL>` の後、
   `skills/effekseer-vfx` と `skills/vfx-review` を `~/.claude/skills/`（Claude Code、全プロジェクト）、`<project>/.claude/skills/`
   （Claude Code、単一プロジェクト）、`~/.codex/skills/`（Codex。`$CODEX_HOME` 設定時は `$CODEX_HOME/skills`）、またはホストのスキルフォルダ（例：`.agents/skills/`）にコピーします。それ以外はコピーしません。
   スキルは自己完結しており、実行時は読み取り専用です。
2. **読み込む。** スキル一覧にまだ表示されない場合は、ユーザーに新しいセッションを始めてもらいます。
3. **マシンを確認する。** ユーザーのゲームプロジェクトで `sh <skill>/scripts/vfx doctor` を実行し（`<skill>` はインストールした
   `effekseer-vfx` フォルダ。Windows で Git Bash 以外なら `<skill>\scripts\vfx.cmd doctor`）、その `next` に従います。
4. **ダウンロード前に確認する。** `sh <skill>/scripts/setup.sh`（Windows では `setup.ps1`。正確なコマンドは `doctor` の `next` にあります）はツールチェーンを
   `~/.cache/effekseer-vfx` に入れます（macOS ARM64 と Windows x64 で約 250 MB。その他の環境では `--authoring-only`）。最初の `vfx init` は公式 Effekseer Godot プラグイン（約 34 MB）もダウンロードします。Python 3.11+ か uv が必要で、`doctor` がどちらもないと報告したらユーザーに
   どちらかのインストールを頼みます。Godot 4 はユーザーの代わりにインストールしません。ユーザーにインストールしてもらう（または
   許可を得る）こと、`PATH` にない場合は `GODOT` を設定することを伝えます。
5. **Godot はサンドボックスの外で実行する。** `vfx review`、`preview`、`showcase` はユーザーのデスクトップに Godot のウィンドウを開きます。
   サンドボックス内のエージェント（ワークスペースサンドボックス内の Codex など）はウィンドウを開けないので、ユーザーの承認を得てサンドボックスの外で
   実行します。ホストがサンドボックスの外に出られない場合は、完全なコマンドをユーザーに渡し、デスクトップのターミナルで実行してもらいます。
   1 フレームも描画できない review は約 90 秒後に "rendered no frame" で停止します（ウィンドウを開けなかった可能性が最も高く、
   含まれる Godot の出力で確認します）。`doctor` の `render: true` は Godot が見つかったことだけを示します。
6. **動作を確認する。** もう一度 `vfx doctor` を実行し（`modes` がこのマシンでできることを示します）、[はじめの一歩](#はじめの一歩)
   に進みます。動くものと足りないものを正直に報告し、`doctor` が build や render を非対応とするマシンで動くと言わないこと。

## はじめの一歩

ゲームプロジェクトの中でエージェントに *「ここに effekseer-vfx スキルをセットアップして、炎のサンプルを見せて」* と頼みます。エージェントは次を実行します。

```sh
sh <skill>/scripts/vfx doctor            # what this machine can do, and what to install
sh <skill>/scripts/setup.sh              # macOS ARM64 / Windows x64; use --authoring-only elsewhere (asks you first)
sh <skill>/scripts/vfx init              # creates vfx/ with the Godot Lab, materials and math textures
sh <skill>/scripts/vfx examples add fire
sh <skill>/scripts/vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
sh <skill>/scripts/vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
sh <skill>/scripts/vfx showcase          # play the library in the Lab
```

各コマンドの役割：`doctor` はこのマシンでできることと、インストールが必要なものを報告します。`setup.sh` は macOS ARM64 / Windows x64 用で、それ以外では `--authoring-only` を使います（実行前に確認を求めます）。`init` は Godot Lab、マテリアル、数式テクスチャを含む `vfx/` を作成します。`showcase` は Lab でライブラリを再生します。

次にエフェクトを頼みます。*「ターゲット指定の魔法に使う落雷を作って。短く鋭く、リターンストロークあり」*。スキルに従ってエージェントは、ブリーフを書き、お使いの画像生成ツールに手描き風テクスチャを依頼し（またはあなたに用意を頼み）、レシピを書いてビルドし、数ラウンドにわたってストリップをレビューし、結果を独立レビュアーに渡してから、`effect-verify` の合格を報告します。独立レビューを提出して `vfx overview` を再実行するまでは、エフェクトが正しく描画されていても `effect-verify` は `verified: false` になります。その段階でエージェントは「検証済み」ではなく「ビルドと描画ができた」と報告すべきです。ツールチェーンの既定の場所は `~/.cache/effekseer-vfx` で、`EFFEKSEER_VFX_HOME` で変更できます（[コマンドリファレンス](skills/effekseer-vfx/references/cli.md) を参照）。

## 画像生成

複雑なペイント系の形状（煙、斬撃の弧、炎、亀裂、氷、シンボル）は画像生成モデルで作らなければならず、スキルがコードでそれを偽装することはありません。エージェントに組み込みまたは接続済みの画像ツールがあれば、`vfx/texture_prompts.json` に記録したプロンプトでそれを使います。なければ、どの画像を生成してどこに保存すればよいかを正確に伝えます。
数式で作れる形状（グロー、リング、ノイズ、グラデーション、トレイル、ディストーションマップ）はプロシージャルに生成されます。

## ゲームでエフェクトを使う

エフェクトは `.efk` ランタイムエクスポートと `.efkefc` ソース、および `vfx_manifest.json` として出力されます。生成される Godot プロジェクトには小さな API が含まれます。

```gdscript
var handle = Vfx.play("VFX_Fire_Explosion", position)
var shot = Vfx.launch("VFX_Projectile_Fire", from, to)
shot.arrived.connect(func(at): Vfx.play("VFX_Fire_Explosion", at))
```

[`docs/ja/references/godot.md`](docs/ja/references/godot.md) を参照してください（英語原文：[`skills/effekseer-vfx/references/godot.md`](skills/effekseer-vfx/references/godot.md)）。

## リポジトリ構成

```
skills/effekseer-vfx/      SKILL.md, references/ (craft, engine conventions, review...), scripts/ (vfx CLI and vfx.cmd,
                           setup.sh and setup.ps1, vfxkit, vendored effekseer_ai), assets/ (Godot Lab, materials, rubric,
                           brief schema, examples)
skills/vfx-review/         SKILL.md for the independent reviewer
docs/zh/, docs/ja/         Chinese and Japanese translations of the references
.claude-plugin/            Claude Code plugin and marketplace manifests
tests/                     pure-Python tests (no Core or Godot needed)
```

| パス | 内容 |
|---|---|
| `skills/effekseer-vfx/` | SKILL.md、references/（クラフト、エンジン規約、レビューなど）、scripts/（vfx CLI と vfx.cmd、setup.sh と setup.ps1、vfxkit、同梱の effekseer_ai）、assets/（Godot Lab、マテリアル、評価基準、ブリーフスキーマ、サンプル） |
| `skills/vfx-review/` | 独立レビュアー用の SKILL.md |
| `docs/zh/`、`docs/ja/` | リファレンスの中国語訳と日本語訳 |
| `.claude-plugin/` | Claude Code のプラグインとマーケットプレイスのマニフェスト |
| `tests/` | 純粋な Python テスト（Core も Godot も不要） |

## 制限事項

- レビューの指標は実 viewport 上のピクセルヒューリスティクスであり、GPU やオーバードローの計測ではありません。
- レビューのハーネスは macOS と Windows 上でウィンドウ表示の Godot を操作します。ヘッドレス Linux での撮影はまだサポートしていません。
  Windows では、撮影中 Godot ウィンドウがフォーカスを保持し続けます（macOS ではフォーカスがお使いのアプリに戻ります）。
- Windows では、シンボリックリンクの安全性テストに開発者モード（または管理者権限のシェル）が必要で、無効だとスキップされます。
- サンプルのスコアは、スキル同梱のカプセル Lab でのレンダーに対する独立レビューの結果です（13 種のうち 2 種は `iterate` 判定）。頼りにする前に、ビルドとレビューをやり直してください。
- `soft` パーティクルは Forward+ の Lab で未検証のため、使用していません。

## 開発

```sh
sh skills/effekseer-vfx/scripts/setup.sh --authoring-only
~/.cache/effekseer-vfx/venv/bin/python -m pip install pytest
~/.cache/effekseer-vfx/venv/bin/python -m pytest -q tests
```

Windows の場合（PowerShell。`--authoring-only` を外すと EffekseerCore のビルドテストも実行されます）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File skills\effekseer-vfx\scripts\setup.ps1 --authoring-only
~\.cache\effekseer-vfx\venv\Scripts\python.exe -m pip install pytest   # a venv made by uv: uv pip install --python <that python.exe> pytest
~\.cache\effekseer-vfx\venv\Scripts\python.exe -X utf8 -m pytest -q tests
```

新しいエンジン規約を確認したコントリビューションでは、それを計測方法と一緒に
`skills/effekseer-vfx/references/engine-conventions.md` に追記してください。

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。サードパーティのコンポーネントとダウンロード：[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
Effekseer および Godot はそれぞれの所有者の商標です。本プロジェクトはそれらと提携していません。

作者：KanaWorks_AI（X：[@KanaWorks_AI](https://x.com/KanaWorks_AI)）。
