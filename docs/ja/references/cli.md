> 英語原文の日本語訳です：[`skills/effekseer-vfx/references/cli.md`](../../../skills/effekseer-vfx/references/cli.md)。エージェントが読み込むのは英語版です。

# コマンドリファレンス

`sh <skill>/scripts/vfx [--project DIR] <command> [options]`。出力：stdout に JSON オブジェクトを一つ。ビルド中の進捗と lint の
警告は stderr に出ます。終了コード：0 成功、1 チェック失敗またはエラー（`{"ok": false, "error": {...}}`）、
2 セットアップが必要：ツールチェーンがない（`SetupRequired`）か、ここに作業領域がない（`WorkspaceMissing`）。
画像の結果はファイルパスです — 開いて見てください。

`doctor`、`init`、`examples`、`rubric`、`layer-schema`、`process-texture` 以外のすべてのコマンドは、`vfx init` が作った作業領域
（`vfx/src/` と `vfx/vfx_manifest.json`）を必要とします。ゲームプロジェクトから実行するか、`--project` を渡してください。間違ったフォルダで
実行したコマンドは、余計な `vfx/` を作る代わりに `WorkspaceMissing` で失敗します。カレントディレクトリは Python の import パスから外され、
`vfx/src` のヘルパーは `_name` ファイルとしてしか解決されないので、プロジェクトのファイルが標準ライブラリを隠すことはありません。

環境変数：`VFX_PROJECT`（プロジェクト。既定はカレントディレクトリ）、`EFFEKSEER_VFX_HOME`（ツールチェーン。既定は
`~/.cache/effekseer-vfx`）、`GODOT`（Godot 4 の実行ファイル。既定は PATH 上の `godot`、次に `/Applications/Godot.app`）。

| コマンド | 必要なもの | 内容 |
|---|---|---|
| `doctor` | — | プラットフォーム、ツールチェーン、作業領域。`modes` と `next` ステップ |
| `init [--update-templates] [--no-plugin]` | Python | `vfx/`（Lab、マテリアル、数式テクスチャ、ペイント系テクスチャのスターター）を作成/更新。公式 Effekseer Godot プラグインをダウンロード（チェックサム固定） |
| `examples [list]` | — | 同梱のペアと単体エフェクト。過去のスコア、判定、最も弱い点付き |
| `examples show <name\|ID>` | Python | 絶対フレームと役割付きのレイヤー計画（ペアなら両方のエフェクト） |
| `examples add <name\|ID\|all> [--force]` | Python | サンプルのソース、ブリーフ、ペイント系テクスチャ、プロンプトをプロジェクトにコピー。名前：`fire`、`ice`、`poison`、`dark`、`hit`、`slash`、`charge`、`shield`、`heal` |
| `procedural` | Python | 数式プリミティブのテクスチャを再生成 |
| `list` | Python | `vfx/src` 内のエフェクトを、カテゴリ、タイミング、delivery、design、ビルド状態とともに一覧。読み込めないソースは `unloaded` に列挙 |
| `lint [--ids ...] [--timeline]` | Python | 静的ルール（エラー）とクラフト上のヒューリスティクス（警告）。下記参照 |
| `layer-schema` | Python | コンパイラが受け付けるすべてのレイヤーフィールド |
| `brief-validate <ID>` | Python | ブリーフとレシピの照合。展開した絶対レイヤータイムライン付き |
| `effect-context <ID>` | Python | ブリーフ、ビルドの問題、最新のエビデンス、直近 10 ラウンド |
| `texture-info [names...]` | Python | カバー率、bbox、縁への接触、向き、膨らみ、継ぎ目比率 |
| `texture-audit <name> [--role R] [--grid C R] [--loop] [--allow-empty i...]` | Python | 役割別のチェック + プレビュー画像 |
| `process-texture <src> <dst> [--size N] [--color] [--grid C R]` | Python | クロップ、アルファ、パディング、2 の累乗へのリサイズ |
| `build [--ids ...]` | Core | lint、コンパイル、save/open の読み戻し、マニフェスト、ビルドレシート。`--ids` なしでは、このスキルがビルドし、ソースが `vfx/src` からなくなったエフェクトも削除（下記参照） |
| `compile <recipe.json> [--source] [--runtime]` | Core | レシピ JSON を一つコンパイル |
| `export [--output DIR]` | Core | ビルド済みの全エフェクトを `resources/` 付きの `.efk` へ再エクスポート |
| `discover` | Core | Core のプロパティパス、型、列挙値を `vfx/work/property_schema.json` に書き出す |
| `core <command> ...` | Core | 同梱ブリッジの低レベルコマンドを明示した `.efkefc` ファイルに対して実行：`property-list`、`property-get`、`property-set`、`node-list`、`curve-list`、`curve-set`、`settings-list`、`settings-set`、…（`vfx core --help`）。[エンジン規約](engine-conventions.md#コンパイラの拡張) を参照 |
| `review [--ids] [--step N] [--note] [--key-frames ...] [--view standard\|close] [--profile default\|bare] [--bright]` | Core + Godot | ストリップ、キーフレームシート、フラグ、changes、エビデンス ID |
| `overview [--ids]` | review 済み | 最新の標準撮影によるライブラリの総覧ページ（`effect-verify` が確認するベースライン）。一度も撮影していないエフェクトは飛ばされ、`missing` に列挙される。`--ids` を付けると、ベースラインを置き換えない作業用ページ `overview_select_*.png` |
| `strip <ID> [--compare] [--bright]` | review 済み | ストリップのパスと保存された指標 |
| `frames <evidence_id> <frame...>` | review 済み | フルサイズのフレームのパスと鮮度の問題 |
| `history <ID> [--limit N]` | — | レビューのラウンド。最新が最後 |
| `rubric` | — | 独立レビューの評価基準 |
| `review-handoff <ID>` | review 済み | 鮮度が保たれた最新の撮影について、独立レビュアー向けの完全なブリーフ（`prompt_file`）を書き出し、`report_file` と提出コマンドを返す |
| `review-submit <evidence_id> <report.json> --reviewer ID [--frames f...]` | review 済み | 独立レポートを結び付ける。フレームの既定値はその `observed_frames` |
| `effect-verify <ID> [--no-overview]` | — | 現在のビルド、撮影、レビュー、総覧が一致しなければ終了コード 1。`--no-overview` は部分チェックで、`passed_without_overview` を報告するだけで `verified: true` にはならない |
| `preview [--ids] [--bright] [--output]` | Godot | ベースライン、ピーク、50 %、85 % での UI 付きスクリーンショット |
| `showcase [--movie]` | Godot（+ ffmpeg） | ライブラリを自動再生する Lab を開く。`--movie` で録画 |
| `package [--preview-dir]` | Godot | テクスチャ一覧付きで Godot プロジェクトを zip 化。デバイステストの合格は主張しない |
| `reference-import`、`reference-frames`、`reference-compare` | ffmpeg | [reference](reference.md) を参照 |

## `--ids` と壊れたソース

`--ids` を付けると、`lint` と `build` は指定したソースが読み込めることだけを要求します。読み込みに失敗するその他の `vfx/src/VFX_*.py`
（書きかけのエフェクト）は、作業を止める代わりに `unloaded` に報告され、エフェクト間のチェックから外されます。`--ids` なしでは、
すべてのソースが読み込めなければなりません。

## 全量ビルドが削除しうるもの

`vfx/src` にレシピが一つもないとき、全量 `vfx build` は実行を拒否します。それ以外の場合に削除するのは、**このスキルがビルドした**
エフェクトのうち `vfx/src/<ID>.py` がなくなったものだけです：`built_by: "effekseer-vfx"` が付き、`source` が自身の `vfx/src/<ID>.py`
と一致するマニフェスト項目、またはこのタグ導入前にビルドされたワークスペースで、`vfx/work/builds/` のビルドレシートがディスク上の
`.efkefc` と今も一致するエフェクトです。不正な ID は決して所有扱いにならず、削除の前にすべてのパスが `vfx/` の内側にあることを確認します。
他のツールや人が作ったマニフェスト項目や `vfx/effects/` 内のエフェクトは残り、`vfx doctor` は `unmanaged` として数えます。

全量ビルドは、どのレシピも使わなくなったリソースコピーも削除します。対象は `vfx/textures/processed/` のテクスチャと同一のファイル
（とその PNG 自身の `.import`）だけで、同じ接頭辞の他のファイルは削除せず、unmanaged なエフェクトが使う可能性のある名前
（その `.efkefc` にファイル名がある、またはファイルが欠けている）も削除しません。Core はテクスチャとモデルをファイル名で `resources/`
にコピーするため、異なる 2 つのファイルが同じ名前を持つとビルドは `Resource name conflict` で停止します：同じビルド内の衝突、
それを使っていて同時に再ビルドされない自前のエフェクトとの衝突（一緒に再ビルドする）、それを使う可能性のある unmanaged なエフェクト
との衝突（ファイル名を変える）。出力フォルダのどれかが `vfx/` の外を指す（別の場所へのシンボリックリンク）場合、ビルドは実行を拒否します。
各ビルドレシートはそのリソースコピーをすべて束縛するので、後のビルドがその一つを変えると以前の撮影は無効になります。

## lint がチェックするもの

エラー（一つでもある間はビルドを拒否）：

- 未知またはスペルミスのレイヤーフィールド（候補付き）、および無効なフィールド値
- duration の外にある `peak`。`flight` または `interval` のない `infinite` レイヤー
- duration を越えて生存するレイヤー（ループしないエフェクト）。発生と飛翔体の解放を含めて数える
- カテゴリの上限を超えるパーティクル予算：`hit` 60、`projectile` 100、`boss` 250、その他のカテゴリはすべて 150
- 数式プリミティブでもなく `vfx/texture_prompts.json` に記録もされていない、または `vfx/textures/processed/` にないテクスチャ
- ランダムなサイズやスケールの範囲と組み合わせた `size_curve`/`scale_curve`（コンパイラはそれらを掛け合わせられない）
- フリップブックへの UV ディストーション（隣のセルをサンプリングし、硬い四角い縁が描かれる）
- 0.01 を超える重力（1 フレームの 2 乗あたりの値）

警告（クラフト上のヒント。判断はストリップで）：

- 最短のライフより長い `fade_in + fade_out`（そのレイヤーは完全な不透明度に達しない）
- `impact >= 0.3` なのに接触がないエフェクト：`flash()` レイヤーも、生存 10 フレーム以下の白熱した加算レイヤー一つもない
- 接触の開始が、Lab が反応するマニフェストの `peak` から 6 フレーム以上離れている
- 6 フレームより長く生存する `flash()`（接触は 2〜5 フレームであるべき）
- 形を変えるレイヤーがない：ディゾルブのカットオフ、リングのスイープ、UV ディストーションやスクロール、フリップブック、後のフレームで打ち直すペイント系の形状のいずれもない
- 白熱した加算の色がない（luma ≥ 0.85 かつ全チャンネル ≥ 180）
- 同じカテゴリで属性の異なる 2 つのエフェクトが、形状、モーション、リズム、マテリアル、二次モーションのうち 3 つ未満でしか違わない（色替えの可能性が高い）

## 作業領域の構成

```
<project>/vfx/
  src/VFX_*.py            recipe sources (yours)              ┐
  briefs/VFX_*.json       design briefs                       │
  texture_prompts.json    prompts of painted textures         │ the effect library:
  textures/generated/     image-model originals (never edited)│ keep under version control
  textures/processed/     game textures (incl. procedural)    │
  recipes/*.json          compiled recipe snapshots           │
  effects/*.efkefc        Effekseer sources + resources/      │
  exports/*.efk           runtime exports + resources/        │
  vfx_manifest.json       ids, timing, delivery, design       │
  previews/strips/overview_*.png, metrics.json                ┘
  characters/             optional rigged stand-ins (player.glb, target.glb)
  godot/                  generated Godot Lab (ignored)
  work/                   receipts, locks, reference frames, audits, property schema (ignored)
```

`src/` から `previews/strips/overview_*.png, metrics.json` までがエフェクトライブラリで、バージョン管理に入れます：レシピのソース（あなたが書くもの）、
デザインブリーフ、ペイント系テクスチャのプロンプト、画像生成モデルの原画（編集しない）、ゲーム用テクスチャ（プロシージャルを含む）、
コンパイル済みレシピのスナップショット、Effekseer ソース + `resources/`、ランタイムエクスポート + `resources/`、
マニフェスト（ID、タイミング、delivery、design）、総覧と指標。`characters/` は任意のリグ付き代役キャラクター（`player.glb`、`target.glb`）、
`godot/` は生成された Godot Lab（バージョン管理から除外）、`work/` はレシート、ロック、リファレンスフレーム、監査結果、プロパティスキーマ（除外）です。
