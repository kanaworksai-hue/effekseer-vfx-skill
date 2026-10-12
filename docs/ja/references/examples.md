> 英語原文の日本語訳です：[`skills/effekseer-vfx/references/examples.md`](../../../skills/effekseer-vfx/references/examples.md)。エージェントが読み込むのは英語版です。

# 同梱サンプル

遠距離ペア 4 組（飛翔体と、その到達点で再生される着弾）、よくあるカテゴリごとに一つずつの単体エフェクト 5 つ、そして怪獣セットがあります。
デザインブリーフ、ペイント系テクスチャ（処理済みのコピー）、それらを作ったプロンプトを備えた、完全なプロダクション用レシピです。
それぞれのレイヤーの役割は、[skeletons](skeletons.md) のカテゴリ別の骨格そのものです。

| ペア | 飛翔体 | 着弾 | 学べること |
|---|---|---|---|
| `fire` | `VFX_Projectile_Fire` — 沸き立つフリップブックの火球、引き伸ばされた彗星のテール、ワールド空間の炎と煙のトレイル | `VFX_Fire_Explosion` — 射線に沿って投げ出される偏った火球、昇っていくキノコ雲、煙へと減衰する地面を舐める炎、焦げ跡と亀裂 | フリップブックの膨らみ、カラーランプ、`decay()`、方向のある `spray`/`debris` |
| `ice` | `VFX_Projectile_Ice` — 紺色の裏打ちを持つ結晶の槍、プリズムの縁取りのあるリボン、経路上に凍り付いた霜のリング | `VFX_Ice_Spikes` — オーバーシュートしながら噴き出す結晶、昇るハローを伴う溜め、タイミングを合わせた砕け | `crystal` メッシュ、フレネルの縁、明度の裏打ち、溜めてから壊すリズム |
| `poison` | `VFX_Projectile_Poison` — 濡れたハイライトを持つ、弧を描いて飛ぶ光沢のある塊（変形メッシュ）、酸の糸、着地する滴 | `VFX_Poison_Cloud` — 酸の飛沫、泡を伴って広がる水たまり、濁った紫灰色へ冷めていく毒煙、転がる霧 | `arc`、Track トレイル、`ShapeNoise` の液体、補色の暗いコア、床との衝突 |
| `dark` | `VFX_Projectile_Dark` — 交差するマゼンタのウィスプの中で渦巻くアルファ黒の球、引き込まれる針と塵 | `VFX_Dark_Vortex` — 傾いた降着円盤の中で呑み込み続ける黒い地平、黒いインパクトフレーム、続いて引き裂かれた解放の弧と地面の渦巻き | 光を吸う Blend の本体、内向きの `travel`、円盤を手前と奥の 2 つに分けた遮蔽、インパクトフレーム |

| 単体 | エフェクト | 学べること |
|---|---|---|
| `hit` | `VFX_Hit_Heavy` | 2 フレームの予備動作、5 フレームの接触、ディゾルブするギザギザのバースト、3 段階の `spark_burst`、空気の泡と屈折の波 |
| `slash` | `VFX_Slash_Fire` | ヨーを付けた `swing()` の平面の中の `slash_set()`（残像、本体、熱い縁、屈折、セル調の三日月）。剥がれていく炎の舌 |
| `charge` | `VFX_Magic_Charge` | 傾いた `orbit_band` のリングと内側へ潰れていくシェルによる 1 秒間の内向きの溜め、そしてちょうど一度の解放 |
| `shield` | `VFX_Shield_Dome` | フレネルのシェルと細いリム、オーバーシュートするポップ、スキャンバンドを伴う保持、時間どおりに消える `shell_fragments` の崩れ |
| `heal` | `VFX_Heal` | インパクトフレームなし：床の紋章、スクロールする柱、リング、すべて昇ってイーズアウトするプラス記号と光の粒 |

| セット | エフェクト | 学べること |
|---|---|---|
| `kaiju` | `VFX_Kaiju_Atomic_Charge`、`VFX_Kaiju_Atomic_Beam`、`VFX_Kaiju_Explosion` | `scale='kaiju'`（40 倍大きく 2.5 倍遅くビルド、[scale](scale.md)）。ダミーの背中を昇っていく `charge_chain()`。ゲーム入力で駆動され、蒸気と焦げ跡を残す薙ぎ払い可能な `beam()`。煤、立ち昇る煙の柱、柔らかい地面の土埃を伴う写真調の爆発（[realism](realism.md)） |

怪獣セットは 70 m のダミーの間で演出され（Lab はエフェクトに合わせてステージをスケールします）、ビームはチャージの後に、
ターゲットの手前の地面からその胸へと薙ぎ上げられます。

```sh
vfx examples                     # list with historical scores and verdicts
vfx examples show slash          # layer plan, absolute frames, roles, budget (a pair shows both effects)
vfx examples add kaiju           # a set: the charge, the beam and the explosion
vfx examples add fire            # copy into vfx/src, vfx/briefs, vfx/textures/processed, vfx/texture_prompts.json
vfx lint --ids VFX_Projectile_Fire VFX_Fire_Explosion
vfx build --ids VFX_Projectile_Fire VFX_Fire_Explosion
vfx review --ids VFX_Projectile_Fire VFX_Fire_Explosion --note "baseline"
```

`vfx examples` は過去のスコアと判定付きの一覧、`vfx examples show` はレイヤー計画・絶対フレーム・役割・予算（ペアなら両方のエフェクト）、
`vfx examples add kaiju` はセット（チャージ、ビーム、爆発）の追加、`vfx examples add fire` は `vfx/src`、`vfx/briefs`、`vfx/textures/processed`、`vfx/texture_prompts.json` へのコピーです。

過去のスコア（評価基準の項目ごとに 0〜3）は、スキル既定のカプセル Lab でのレンダーに対する独立レビューによるものです：ストリップ、
キーフレームシート、マニフェストのエントリ、フラグだけを見た 2 人のレビュアーが採点しました。11 個が `ship` と判定され、
`VFX_Projectile_Ice`（白いコアも暗い縁もない平板な槍で、飛行中に形が変わらない）と `VFX_Projectile_Dark`（到達後に経路に何も残らない）は
`iterate` と判定されました。kaiju セットも同じ方法で、スケールした Lab での自身のレンダーに対して独立レビューを受け、数回の修正の後
3 つとも `ship` と判定されました（レビュアーの修正案：背板を体に沿わせる、1 枚ずつ点灯する結晶の背びれ、口へ集まる電光、くすぶる煙、
炎より長く残る煙柱で終わりを埋める）。`vfx examples` は各サンプルの最も弱い評価項目と、レビュアーによる修正案一つ（`historical_review.worst`）を一覧にします。
スコアは参考であって、あなたのビルドの検証では **ありません**：ビルド、レビュー、採点をやり直してください。`--force` を付けない限り、
サンプルを追加しても既存のファイルは上書きされません。

サンプルから新しいエフェクトを作るには、ソースを新しい ID でコピーし（ファイル名と `effect('...')` の名前、
ブリーフの `effect_id` を変更）、それから色だけでなく形、モーション、リズムを変えます（[craft](craft.md) を参照）。
飛翔体と着弾の対応を一貫させてください：着弾の `delivery.projectile` は飛翔体の ID を指していなければなりません。
