> 英語原文の日本語訳です：[`skills/effekseer-vfx/references/primitives.md`](../../../skills/effekseer-vfx/references/primitives.md)。エージェントが読み込むのは英語版です。

# レシピコードとプリミティブ

目次：レシピファイル · `effect()` のフィールド · プリミティブ · ヘルパー · レイヤーフィールド · 単位

## レシピファイル

1 ファイルにつき 1 エフェクト：`vfx/src/VFX_<Name>.py` は `effect('<Name>', ...)` を返す `recipe()` を定義します。ID
`VFX_<Name>` はファイル名と一致していなければなりません。`_` で始まるファイルは共有ヘルパーです（`from _palette import *`）。
ソースはコマンドのたびに再読み込みされます。`from vfxkit.primitives import *` で、すべてのプリミティブ、以下の
ヘルパー、`WHITE`、`fade`、`ramp`、`walk`、`math` が取り込まれます。

どのプリミティブもプレーンなレイヤー dict を返します。`| dict(...)` で任意のフィールドを上書き・追加できます。テクスチャは
ステム名（`'T_Glow01'`）で指定し、`vfx/textures/processed/` から解決されます。レイヤーはリストの順に描かれます：**後のレイヤーが
手前に描かれます**（Godot プラグインはエフェクトレイヤー間の ZWrite を無視します）。

## `effect()` のフィールド

`effect(id, name, category, element, duration, layers, attach='impact', peak=.1, impact=0, light=(1,.85,.6), loop=False, design='', delivery=None, flight=None, arc=None)`

| フィールド | 意味 |
|---|---|
| `category` | `hit`、`slash`、`projectile`、`element`、`status`、`boss` など（lint の予算を決める） |
| `element` | `physical`、`fire`、`ice`、`lightning`、`dark`、`holy`、`poison` など（属性の違いとモーションのチェック） |
| `duration`, `peak` | 秒。`peak` は Lab のフラッシュ、キック、ターゲットのリアクションが使う接触/解放の瞬間 |
| `attach` | アンカー：`ground`、`body`、`impact`、`caster`、`caster_ground`、`projectile` |
| `impact`, `light` | Lab のステージフラッシュとカメラキックの強さ（0–1）と RGB（デモ演出専用） |
| `delivery` | ゲームでの演出方法：`SELF`、`MELEE`、`TARGETED`、`dict(kind='area')`、飛翔体そのものには `dict(kind='projectile')`、その着弾には `dict(kind='projectile', projectile='VFX_X')` |
| `flight`, `arc` | 飛翔体のみ：基準となる飛行の秒数と、山なりの高さ（メートル） |
| `design` | プレイヤーに見えるものを一文で。Lab に表示され、レビュアーに渡される |

## プリミティブ

**まずボリューム、テクスチャはその次。** 本体、衝撃波、結晶、柱は、カメラを向くカードではなく、傾いた 3D 平面上のメッシュやリングにすべきです。
カメラを向くスプライトは、本質的にスクリーン空間のもの — 接触の星形、グロー、火花、煙のひと吹き（積み重ねてボリュームにする） — のために取っておきます。

| プリミティブ | 用途 | 主なネイティブ機能 |
|---|---|---|
| `flash` / `glow` | 接触の星形、形の下の柔らかいブルーム | 単一値の F カーブスケール |
| `shadow` | 加算コアの後ろの暗い裏打ち | フラッシュの 1〜2 フレーム後にピークを迎える Blend の柔らかい円盤 |
| `radial_sparks` | 火花、針、立ち昇る筋 | 球/円の放出 + イージングした `travel` + DirectionalBillboard |
| `spark_burst` | 3 段階のヒット/爆発の火花 | 長く速い筋（6〜10 フレーム）、主体、`floor` を与えると跳ねる約 20 % の重い火花 |
| `motes` | 残り火、霜の粉、魔法のモート、内向きの集束 | 上記 + 乱流の力 |
| `shock_ring` / `tilted_ring` | 衝撃波、昇るハロー、縮むリング。3D 平面上のリング | 内径をイージングする Ring レンダラー。近接の傾き `(0,58,0)` は左から右への打撃を横切る |
| `slash_arc` | 刃の弧 | 開始/終了角をイージングでスイープする Crescent Ring + ディゾルブ |
| `wisps` | 途切れたエネルギーのストローク、渦の筋、地面を舐める炎 | Crescent Ring + `T_WispTrail01`、放出ごとにランダムな傾きとサイズ。侵食が 0 より上から始まるので完全なリングにはならない |
| `orbit_band` | 降着円盤、周回するルーンのリング | 傾いた平面上の Ring、ノイズがリングに沿って流れる。`arc=(-90,90)` で奥の半分、`(90,270)` で手前の半分 |
| `smoke` | 煙、霧、土埃、暗い残滓 | ペイント系の煙のフリップブック `T_SmokeSheet01` + 軽い侵食。静止した単発の煙には `texture='T_Smoke02'` — 氷の霧は、炎の転がる煙と区別するため静止した煙を使い続ける |
| `billow` | 火球、煙と同じ膨らみ | 一度だけ再生するペイント系 4×4 フリップブック `T_ExplosionSheet01` + `ramp` のカラーストップ |
| `flame` | 炎の舌、炎の壁、地面の炎 | 根元から成長する爆発フリップブック。白 → 色 → 暗色へ冷め、熱い縁を伴うノイズに侵食される（クリップアート風の炎シルエットではない） |
| `decal` | 紋章、亀裂、焦げ跡 | 地面の平面に置くスプライト、深度テストあり |
| `standing` | 棘、稲妻、ビーム | 根元を軸にする YAxisFixed スプライト |
| `column` | 光の柱、オーラ | プロシージャル円柱 + スクロールする筋 + 静的なアルファグラデーション + フレネル |
| `mesh` | 球、円錐、円柱 | プロシージャルモデル + falloff。追加のプロシージャルフィールドには `model={...}` |
| `crystal` | 氷の棘、破片、槍 | 先端へ細くなる六角柱 + セル状テクスチャ + フレネルの縁 |
| `shell` | 衝撃の泡、内破、解放 | 前面のみ、フレネル `pow<1` でリムだけを光らせる、イージングした膨張 |
| `shell_fragments` | シェルの実際の幾何的な崩れ | 離れながら回転する 6 枚の部分球面シート（AngleBeginEnd） |
| `heat_haze` / `distortion_ring` | 陽炎、屈折する衝撃波 | `BackDistortion` によるスクリーンの屈折 |
| `slice_line` | 解放時の長く細い線 | 35 % から全長まで伸びながら細くなる `T_Streak01`。`width` は見える太さ |
| `spray(end)` / `debris` | 射線に沿った方向のある飛沫、暗く転がる塊 | 回転しない放出 + ワールド方向の `travel` ボックス。重力付きの Blend `T_Shard01`、着地できる |
| `decay(layer, color)` | グロー → 灰色の煙の残像 | Blend のグレーとしてコピーし、`lag` フレーム遅らせ、ライフ × `stretch`、エミッシブなし、流れを遅く |

## ヘルパー

| ヘルパー | 意味 |
|---|---|
| `ramp((0,c0),(30,c1),(100,c2))` | 3〜5 個のストップによるライフ上の色 → `color_curve`（2 色の線形補間は色味付けに見える） |
| `fade(color, alpha=0)` | 同じ RGB で新しいアルファ |
| `POP`, `DISSOLVE` | パッと出てから漂うスケールカーブ。保持してから侵食するカットオフカーブ |
| `sustain(layer, interval)` | 飛翔体のエミッター：解放まで `interval` フレームごとにインスタンスを一つ |
| `TRAIL` | 位置/回転/スケールを生成時にだけ継承：レイヤーは経路上に留まる |
| `slash_set(colors, roll, sweep=(110,260), radius=1.5, offset=(0,0,.5), lean=-18, delay=1, life=14)` | 3 つの幅を持つ一本の刃：2 フレーム遅れる幅広で薄暗い残像、高彩度の本体、細く白熱した縁（`slash_arc`）、屈折の弧、ペイント系のセル調の三日月（`T_Slash02`、刃の平面に置いた `billboard='Fixed'`、計測した `SLASH02_BULGE` で回転）。`colors` = (残像, 本体, 縁) |
| `swing(layers, yaw, pitch=0)` | 刃のレイヤーを `renderer='None'` のピボットで包み、弧が 3D 空間を切り裂くようにする。ヨーを約 ±30–40° にすると、画面上の三日月ではなく楕円に見える |
| `contrast_pair(layer)` | 固定したスプライト一つと、ジオメトリが同一の Blend の下敷き（[layering](layering.md) を参照） |
| `lifetime(layer)`, `budget(layer)` | レイヤーまたはその子が生存しうる最後のフレーム。インスタンス数 |

## レイヤーフィールド

PVA、スケール、色のほかに、コンパイラは次をサポートします：`collide`（床での跳ね返り）、`soft`（エンジン規約を参照）、
`size` / `size_end` / `size_curve`（一様なスケール）、`color_end`、`color_curve`、`travel`（イージングした変位）、`spawn`
（球、円、線のエミッター）、`forces`（重力、乱流、渦）、`alpha_texture` + `cutoff` + `edge`
（熱い縁を伴うディゾルブ）、`distortion_texture`、`blend_texture`、`falloff`（フレネル）、`flipbook`、`pivot`、
`ring{...}`、`inherit`、`track_size`、`material`（`BackDistortion`）、`children`。`vfx layer-schema` は受け付けるすべての
キーを列挙します。未知のキーはスペルの候補とともに失敗します。それ以外のものは、レシピに生のプロパティパスとして書くのではなく、
save/open の読み戻しテストとともにコンパイラに追加しなければなりません（手順：[エンジン規約](engine-conventions.md#コンパイラの拡張)）。

## 単位

レイヤーの `life`、`delay`、`interval`：60 FPS のフレーム数。速度と加速度：units per frame。重力：units per frame²。
角度：度。色：RGBA 0–255。カーブ（`size_curve`、`cutoff`、`color_curve` など）：`[[percent_of_life, value], ...]`。
マニフェストの `duration` と `peak`：秒。ランダムな範囲は `[min, max]`。
