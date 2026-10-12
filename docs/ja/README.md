# effekseer-vfx-skill 日本語ドキュメント

これらのページは英語版ドキュメントの翻訳です。エージェントが実際に読み込むのは `skills/` 以下の英語ファイルで、内容が食い違う場合は英語版が正です。
リポジトリ全体の概要は [README.ja.md](../../README.ja.md) を参照してください。

## スキル本体

| ページ | 内容 |
|---|---|
| [SKILL.effekseer-vfx.md](SKILL.effekseer-vfx.md) | 制作スキル `effekseer-vfx`：初回セットアップ、エフェクト一つを作る手順、厳守ルール、ルーティング表、レシピの骨格 |
| [SKILL.vfx-review.md](SKILL.vfx-review.md) | 独立レビュアースキル `vfx-review`：受け取る入力、評価基準、JSON 出力の形式 |

## リファレンス

| ページ | 内容 |
|---|---|
| [craft.md](references/craft.md) | クラフトルール：時間構造、属性の違い、飛翔体、不規則で複数の役割を持つエフェクト、予算 |
| [design.md](references/design.md) | デザインブリーフ：用途、キーフレーム、パレットの役割、ブリーフの形式 |
| [layering.md](references/layering.md) | 明度、色、レイヤーの組み合わせ：暗い裏打ち・明暗ペア・煙の残像、白い塊と黒い塊の修正順序 |
| [timing.md](references/timing.md) | 強度、ボリューム、退場のリズム：サンプルの参考タイミング、カーブを実フレームに合わせる方法 |
| [skeletons.md](references/skeletons.md) | カテゴリ別の骨格：ヒット、斬撃、爆発、飛翔体、チャージ、シールド、ヒールとバフ |
| [motion.md](references/motion.md) | モーションと経路：ヘッド・トレイル・振りまきパーティクル、速度を形とリズムに込める |
| [shapes.md](references/shapes.md) | ボリュームと遮蔽：標準カメラでのボリュームの選び方、描画順 |
| [textures.md](references/textures.md) | テクスチャの役割、生成、受け入れ：プロンプトの内容、処理と計測、連番の変形 |
| [reference.md](references/reference.md) | リファレンスクリップとの比較：取り込み、フレームの読み取り、撮影フレームとの対比 |
| [review.md](references/review.md) | レビューループ、エビデンス、納品：フラグ、ストリップの読み方、独立レビュー、検証 |
| [cases.md](references/cases.md) | 診断済みのケース：火の爆発、飛翔体の煙のテール、シールドの崩れを再構成したビフォー/アフター（画像付き） |
| [cli.md](references/cli.md) | コマンドリファレンスと作業領域の構成 |
| [examples.md](references/examples.md) | 同梱サンプル：炎・氷・毒・闇の飛翔体と着弾のペア 4 組、ヒット・斬撃・チャージ・シールド・ヒールの単体 5 つ、怪獣セット（チャージ、ビーム、爆発） |
| [godot.md](references/godot.md) | Godot でエフェクトを使う：API、ビーム、スケールしたエフェクト、ソフトパーティクル、Lab、チェック |
| [engine-conventions.md](references/engine-conventions.md) | 検証済みのエンジン規約：角度と軸、力、メッシュとフレネル、フリップブック、継承、ゲーム入力と動的方程式、HDR とソフトパーティクル、アンカー、コンパイラの拡張 |
| [primitives.md](references/primitives.md) | レシピコードとプリミティブ：`effect()` のフィールド、プリミティブ、ヘルパー、レイヤーフィールド、`bind`、単位 |
| [scale.md](references/scale.md) | ワールドスケール：巨人・怪獣・軍艦向けの `scale` の宣言、変換されるもの、スケール時の Lab とチェック |
| [realism.md](references/realism.md) | 写真調の爆発・炎・煙：写真から取る色と明るさ、写真調のフリップブック、地面との接触、レイヤー計画 |
