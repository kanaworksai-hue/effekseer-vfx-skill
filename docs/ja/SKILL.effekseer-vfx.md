> このページは [`skills/effekseer-vfx/SKILL.md`](../../skills/effekseer-vfx/SKILL.md) の日本語訳です（YAML フロントマターは省略）。エージェントが読み込むのは英語の SKILL.md で、内容が食い違う場合は英語版が正です。

# Effekseer VFX

VFX アーティストと同じ反復の進め方で、ただしコードでゲームエフェクトを作ります：**ブリーフ → テクスチャ → レシピ → EffekseerCore ビルド → Godot 実レンダーのフィルムストリップ → 見る → 一つだけ直す → 繰り返す → 独立レビュー**。

以下の `<skill>` は、このファイル（英語の SKILL.md）を含むディレクトリです。すべてのコマンドは
`sh <skill>/scripts/vfx [--project <game project>] <command> ...` の形式で、JSON オブジェクトを一つ出力します
（進捗は stderr に出ます）。プロジェクトの既定はカレントディレクトリで、エフェクトの作業領域は `<project>/vfx/` です。
全コマンドは `sh <skill>/scripts/vfx --help` で確認できます。説明は [references/cli.md](references/cli.md) にあります。
Windows では、`sh <skill>/scripts/vfx` は Git Bash で動作します。cmd や PowerShell からは代わりに `<skill>\scripts\vfx.cmd` を実行します
（コマンドも出力も同じです）。

## プロジェクトでの初回実行

1. `vfx doctor` — `modes`（`authoring`、`build`、`render`）、作業領域、具体的な `next` ステップを報告します。`vfx init` が作成したのではない `vfx/` フォルダが存在すると報告された場合は、初期化する前に、それがゲームプロジェクトであることをユーザーに確認します（または `--project` を渡します）。
2. セットアップが必要な場合は、**まずユーザーに確認します**（フルモードは `~/.cache/effekseer-vfx` に約 250 MB をダウンロードします）。
   macOS ARM64 では `sh <skill>/scripts/setup.sh`、Linux では `sh <skill>/scripts/setup.sh --authoring-only`、Windows では
   `powershell -NoProfile -ExecutionPolicy Bypass -File <skill>\scripts\setup.ps1` です（Git Bash からは `sh <skill>/scripts/setup.sh` でも実行でき、これが上記を呼び出します）。
   `doctor` の `next` が、このマシン向けの正確なコマンドを表示します。
   setup には Python 3.11+ か uv が必要です（macOS 標準の Python 3.9 は古すぎます）。`doctor` がどちらもないと報告したら、ユーザーにどちらかのインストールを頼みます。Godot 4（Forward+）はユーザーがインストールする必要があります。`PATH` 上にない場合は `GODOT` を設定します。
3. `vfx init` は `vfx/`（Godot Lab、マテリアル、数式テクスチャ、公式 Effekseer プラグイン）を作成します。`--update-templates` を付けない限り、既存のファイルは上書きしません。
4. 任意：`vfx examples add <name>` で、完成済みで独立レビュー済みのサンプルを学習用にコピーします：ペアは `fire`、`ice`、`poison`、`dark`（飛翔体 + 着弾）、単体は `hit`、`slash`、`charge`、`shield`、`heal`、または `all`。[references/examples.md](references/examples.md) を参照してください。

`vfx review`、`preview`、`showcase` はユーザーのデスクトップに Godot のウィンドウを開きます。サンドボックス内で動いている場合（Codex のワークスペース
サンドボックスなど）は、ユーザーの承認を得てサンドボックスの外で実行します。外に出られない場合は、完全なコマンドをユーザーに渡してデスクトップの
ターミナルで実行してもらいます。"rendered no frame" で止まった review は、ウィンドウを開けなかった可能性が最も高いです（含まれる Godot の出力で確認します）。
`doctor` の `render: true` は Godot が見つかったことだけを示します。

`build`/`render` モードがなくても、ブリーフ、レシピ、テクスチャを書いて `lint` を実行することはできますが、見た目を判断することはできません。
そのことをはっきり伝え、作業は **未コンパイル・レンダー未検証** として報告します。エフェクトが改善したと主張してはいけません。

## エフェクトを一つ作る・変更する

1. **書く前に読む。** [craft](references/craft.md)、[design](references/design.md)、[layering](references/layering.md)、[timing](references/timing.md)、[skeletons](references/skeletons.md) は必ず読み、さらに下のルーティング表にあるトピック別ファイルと、該当するサンプルのレイヤー計画を示す `vfx examples show <name>` を読みます（名前：`hit`、`slash`、`charge`、`shield`、`heal`。飛翔体や爆発などの着弾はペア `fire`、`ice`、`poison`、`dark`。エフェクト ID も使えます）。既存のエフェクトでは `vfx effect-context <ID>` を実行して履歴を読み、失敗した変更を繰り返さないようにします。
2. **ブリーフ。** `vfx/briefs/<ID>.json` を書きます（キーフレーム 3 つ、パレットの役割、ビート、レイヤー計画、受け入れ条件、避けること）。形式は [design.md](references/design.md) にあります。
3. **テクスチャ。** 数式で作る形状（グロー、リング、ノイズ、トレイル、ディストーションマップ）と、ペイント系の煙・爆発・ウィスプ・亀裂・氷のスターターセットは、`init` の時点で揃っています。複雑なペイント系の形状（炎、斬撃、煙、亀裂、氷、ルーン）は画像生成モデルで作ります — [textures.md](references/textures.md) に従ってください。どのテクスチャも、その角度を使う前に `vfx texture-info` で計測します。
4. **レシピ。** [primitives.md](references/primitives.md) のプリミティブを使って `recipe()` を定義する `vfx/src/<ID>.py` を書きます。軸、単位、ブレンドの挙動は推測せず、[engine-conventions.md](references/engine-conventions.md) の検証済みエンジンルールに従います。
5. `vfx brief-validate <ID>` と `vfx lint --ids <ID>`。lint のエラーは必ず修正します。警告はクラフト上のヒントで、判断はレンダーで行います。
6. `vfx build --ids <ID>` の後、`vfx review --ids <ID> --note "<what this round changed>"`。
7. **画像を見る。** レビューが返すすべてのパス（`sheets`、`compare`、`details.*.sheet`）を画像表示ツールで開きます。フラグはありがちな問題を指し示すだけなので、フラグだけで判断してはいけません。手順とフラグの意味：[review.md](references/review.md)。
8. **1 ラウンドにつき 1 種類の問題** を直し、エフェクトごとに 3〜5 ラウンド行います。
9. **独立レビュー。** 作者は自分のエフェクトを採点しません。`vfx review-handoff <ID>` を実行します。これはレビュアー向けの完全なブリーフ（画像、撮影したフレーム番号、マニフェストの文脈、評価基準、レポートの保存先、このスキルの隣にインストールされた `vfx-review` スキルのパス）を書き出し、`prompt_file`、`report_file`、そのまま使える提出コマンドを返します。そのブリーフを手を加えずに、レシピを見ていない別のエージェントに渡します。ホストが可能ならそれでサブエージェントを起動し、エフェクトについてそれ以外のことは何も伝えません。できなければ、ユーザーに新しいセッションを開いて貼り付けてもらいます。`report_file` ができたら、返された `vfx review-submit <evidence_id> <report_file> --reviewer <that agent's identifier>` を実行します（識別子はサブエージェントの ID か名前、またはセッション ID。`author` や `self` は不可。フレームの既定値はレポートの `observed_frames` です）。レポートを自分で書いてはいけません。
10. `vfx overview`（`--ids` なし：ライブラリのベースライン）の後、`vfx effect-verify <ID>`。完了と報告してよいのは `verified: true` の場合だけで、そうでなければ不足しているものを列挙します。ラウンドの上限に達しても ship 判定が出なければ、未解決の項目を報告します。

## 厳守ルール

- すべてのエフェクトに時間構造（予備動作 → 接触 → 本体 → 二次モーション → 消散）と明度の階層（白熱コア、高彩度の本体、暗い外縁または残滓）を持たせます。ヒール、シールド、チャージには、文書化された独自の例外があります。
- 本体は形を変えます（ディゾルブ、スイープ、UV ディストーション、フリップブック、形状の打ち直し）。拡大とフェードだけで済ませてはいけません。パーティクルはイーズアウト（速く、そして遅く）で動かします。
- 属性同士は、形状、モーション、リズム、マテリアル、二次モーションのうち少なくとも 3 つで違いを持たせます — 色替えだけにしてはいけません。
- 複雑なペイント系の形状を Python で描いてはいけません。画像生成ツールが使えない場合は、プロンプトを `vfx/texture_prompts.json` に書き、ユーザーに画像を依頼します。
- 生成した原画は `vfx/textures/generated/` に保持し、処理済みのコピーは `vfx/textures/processed/` に書き出します。プロンプトはすべて記録します。
- 単位：レシピのタイミングは 60 FPS のフレーム数、F カーブはライフに対するパーセント、マニフェストの duration/peak は秒、Godot API の rotation はラジアンです。
- すべてのエフェクトは `delivery` を宣言します。飛翔体には、それを参照し返す対の着弾エフェクトが必要です。
- コンパイラが知っているレイヤーフィールド（`vfx layer-schema`）だけを使います。レシピに生のプロパティパスを書くのではなく、コンパイラを拡張します。
- `--ids` なしの全量 `vfx build` は、このスキルがビルドし、ソースが `vfx/src/` からなくなったエフェクトの出力を削除します。自分がビルドしていないエフェクトは決して削除せず、空のライブラリでは実行を拒否します。部分的な作業には `--ids` を使います（他の場所の壊れたソースは、作業を止めずに `unloaded` に報告されます）。
- 実際に実行して確認しない限り、エクスポート、再生、デバイス性能、録画の成功を主張してはいけません。

## ルーティング表

| タスク | 追加で読むもの |
|---|---|
| 新しいペイント系テクスチャ、フリップブック、テクスチャの問題 | [textures.md](references/textures.md) |
| 斬撃、飛翔体、チャージ、オーラなど移動するもの全般 | [motion.md](references/motion.md) |
| シールド、柱、ボス、状態異常、ボリューム、遮蔽 | [shapes.md](references/shapes.md) |
| リファレンス動画に合わせる | [reference.md](references/reference.md) |
| 特定の見た目の失敗（白い塊、空のテール、崩れが出ない） | [cases.md](references/cases.md) |
| コンパイラへのエンジン機能の追加 | [engine-conventions.md](references/engine-conventions.md#コンパイラの拡張)、`vfx discover`、`vfx core property-list/get/set` |
| ゲームでエフェクトを使う | [godot.md](references/godot.md) |

## レシピの骨格

```python
# vfx/src/VFX_Hit_Spark.py
from vfxkit.primitives import *

def recipe():
    hot = (255, 240, 200, 255)
    return effect('Hit_Spark', 'Spark Hit', 'hit', 'physical', .4, [
        flash('Contact flash', WHITE, 2.2, life=4, delay=1),
        glow('Bloom', (255, 170, 70, 170), 1.6, life=9, delay=1),
        radial_sparks('Sparks', 10, hot, color_end=(255, 120, 30, 255), distance=(.8, 1.7), life=(12, 16), delay=1, gravity=.0018),
        smoke('Dust', (185, 160, 135, 200), count=2, size=(.5, .7), life=(13, 14), delay=4),
    ], peak=.03, impact=.3, delivery=MELEE, design='One-line description of what the player sees.')
```

`effect('Hit_Spark', ...)` は ID `VFX_Hit_Spark` を生成し、これはファイル名と一致していなければなりません。`vfx/src/` 内の
`_` で始まるファイルは、レシピから import できる共有ヘルパーです。
