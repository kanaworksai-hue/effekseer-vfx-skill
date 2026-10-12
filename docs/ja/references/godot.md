> 英語原文の日本語訳です：[`skills/effekseer-vfx/references/godot.md`](../../../skills/effekseer-vfx/references/godot.md)。エージェントが読み込むのは英語版です。

# Godot でエフェクトを使う

`vfx init` は `vfx/godot/` を生成します。これは公式 Effekseer プラグイン、`Vfx` オートロード、インスタンスごとの
`CombatVfxHandle`、VfxLab シーンを含む Godot 4 プロジェクトです。スキルの `assets/godot-lab/` にあるランタイムロジックを編集するのは、
スキルをメンテナンスする場合だけにしてください。ゲームプロジェクトでは、`scripts/Vfx.gd`、`scripts/VfxHandle.gd`、`effects/` フォルダ
（`resources/` 付き）、`vfx_manifest.json` を同じ `res://` パスでゲームにコピーし（`Vfx.gd` は `res://vfx_manifest.json` を読みます）、
そこで Effekseer プラグインを有効にし、autoload を登録します：プロジェクト設定 → グローバル → 自動読み込み、または `project.godot` の
`[autoload]` に `Vfx="*res://scripts/Vfx.gd"`。登録しないと `Vfx.play()` は存在しません。

## API

```gdscript
var handle = Vfx.play("VFX_Fire_Explosion", position, rotation, effect_scale)   # rotation in radians
Vfx.set_speed(0.5)      # all active effects, 0.05–4
Vfx.set_paused(true)
handle.stop()           # immediately
handle.release()        # stop emitting; live particles finish, then it frees itself

# Projectiles: flight time from the manifest unless options.speed (m/s) or options.flight (s); options.arc lifts it.
var shot = Vfx.launch("VFX_Projectile_Fire", from, to)
shot.arrived.connect(func(at): Vfx.play("VFX_Fire_Explosion", at))
```

補足：`rotation` はラジアンです。`Vfx.set_speed` はアクティブなすべてのエフェクトに作用し、範囲は 0.05–4 です。`handle.stop()` は即座に停止し、
`handle.release()` は放出を止め、生きているパーティクルが終わった後に自身を解放します。飛翔体の飛行時間は、`options.speed`（m/s）か
`options.flight`（s）を指定しない限りマニフェストから取られ、`options.arc` で山なりに持ち上げます。

有限のエフェクトは `duration` の後に自動で片付けられ、ループするエフェクトは `stop()` まで再生を繰り返します。マニフェスト
（`vfx_manifest.json`）は `id`、`duration`、`peak`、`impact`、`light`、`delivery`、`flight`、`arc`、`hold`、
`inputs`、`scale`、`attach`、`design` を持ちます。Lab はステージのフラッシュとカメラキックに `impact`/`light`/`peak` を使いますが、ゲームではこれらを自前で実装します。

## ビーム

`beam()` でビルドしたレシピ（マニフェストの `delivery.kind == "beam"`）は保持型のエフェクトで、その長さと出力は、`bind` の方程式が読む
入力（`@In0` はワールド単位の長さ、`@In1` は出力 0–1）を通じてゲームが動かします：

```gdscript
var ray = Vfx.beam("VFX_Kaiju_Atomic_Beam", mouth.global_position, target_point)   # ignites: power 0 -> 1
func _process(_delta):
	if is_instance_valid(ray) and not ray.released:
		ray.aim(mouth.global_position, raycast_hit_point)   # every frame: sweep, follow the head, stop at walls
# when the breath ends:
ray.release()           # the beam narrows (power -> 0) and its last instances fade; the handle frees itself
```

補足：`Vfx.beam()` で点火し、出力が 0 から 1 へ上がります。`aim()` は毎フレーム呼び、薙ぎ払い、頭部への追従、壁での停止を行います。
ブレスが終わったら `release()` を呼びます：ビームが細くなり（出力 → 0）、最後のインスタンスがフェードし、ハンドルは自身を解放します。

`aim(from, to)` はハンドルを `from` に置き、その +Y を `to` へ向け、`@In0` にエフェクト自身の単位での距離を設定します（スケールした
ハンドルはそのスケールで割ります）。`options.ignite` / `options.fade`（秒）で出力のランプを設定し、`handle.set_input(index, value)` で
レシピが bind する他の入力を動かします。火花、蒸気、焦げ跡はワールド空間に放出されるので、薙ぎ払うビームはその経路に沿ってそれらを残します。
終点は物理のレイキャストから取り、ビームが当たった面で止まるようにします。別の表面着弾が欲しいゲームは、その点で別のエフェクトを再生することもできます。

どのハンドルも、マニフェストの `inputs` の既定値から始め、作られた直後とその後の毎フレームに `inputs` をエミッターへ送り込むので、
最初のフレームから実際の値が使われます。

## スケールしたエフェクト

`scale` 付きでビルドしたエフェクト（マニフェストの `scale.world`、[scale](scale.md) を参照）は、すでにワールド単位になっています：
スケール 1 で再生してください。ゲームの Effekseer の上限が怪獣サイズのライブラリに足りること（`project.godot` の `[effekseer]`
`instance_max_count`、`square_max_count`。Lab は 2000 / 8000 を使用）と、カメラのファープレーンがエフェクトを覆うことを確認してください。

## ソフトパーティクル

`soft` を持つレイヤーは、不透明なジオメトリと接する位置でフェードします。Forward+ レンダラーの深度テクスチャが必要です
（検証済み。Mobile にも深度テクスチャはありますが未検証）。Compatibility ではほとんど見えなくなります。透明な面（水）は、
深度を書き込まない限り深度テクスチャに入りません。

## Lab

`vfx showcase`（または `godot --path vfx/godot`）で Lab が開きます：PLAYER と TARGET の 2 体のダミーが向かい合い、すべての
エフェクトがその `delivery` に従って演出されます — `self` は術者に、`melee` は打撃の瞬間にターゲットに、
`projectile` は術者からターゲットへ飛んで到達時に着弾を、`targeted` はターゲットの上に降らせ、`area` はボスの叩きつけを中心に、`beam` は術者の砲口からターゲットの手前の地面へ撃ち、その胸へと薙ぎ上げます
（`delivery.charge` で指定したチャージがあれば、その後で）。ステージは選択したエフェクトの `scale.world` に合わせてスケールします：
怪獣のエフェクトは 70 m のダミーの間で再生され、カメラも同じ倍率で引かれます。キー：←/→ 切り替え、Space 再生し直し、C 対戦/単体ステージ、L ループ、P 一時停止、1–4 速度、
B 背景、S 自動ショーケース。`-- --no-glow` は比較用に HDR ブルームを無効にします。

ダミーはカプセルです。任意のリグ付き代役で置き換えられます：`player.glb` と `target.glb`（高さ約 1 ユニット、
Mixamo 形式のボーン名、`idle`、`cast_a_spell`、`box_03`、`hit_to_head`、`hit_to_body_01`、`jump` という名前のクリップ）と、
任意の `<name>.materials.json`（部位 → 役割のマップ）を `vfx/characters/` に置き、`vfx init` を実行します。ダミーを変えると
ステージが変わります：ベースラインをレンダーし直し、ブルームのしきい値を計測し直してください
（[エンジン規約](engine-conventions.md) を参照）。

## チェック

`godot --path vfx/godot --fixed-fps 60 --script res://scripts/TestApi.gd` は、現在のマニフェストに対して play、launch、beam（aim、出力、
release）、pause、speed、loop、自動回収を試験します。`godot --headless --path vfx/godot --script res://scripts/ExportRuntime.gd` は
Godot のランタイムリソースをエクスポートします。これらは実際に実行した後でのみ、合格と報告してください。
