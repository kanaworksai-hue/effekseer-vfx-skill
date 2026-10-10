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
（`vfx_manifest.json`）は `id`、`duration`、`peak`、`impact`、`light`、`delivery`、`flight`、`arc`、`attach`、
`design` を持ちます。Lab はステージのフラッシュとカメラキックに `impact`/`light`/`peak` を使いますが、ゲームではこれらを自前で実装します。

## Lab

`vfx showcase`（または `godot --path vfx/godot`）で Lab が開きます：PLAYER と TARGET の 2 体のダミーが向かい合い、すべての
エフェクトがその `delivery` に従って演出されます — `self` は術者に、`melee` は打撃の瞬間にターゲットに、
`projectile` は術者からターゲットへ飛んで到達時に着弾を、`targeted` はターゲットの上に降らせ、`area` はボスの叩きつけを中心に。
キー：←/→ 切り替え、Space 再生し直し、C 対戦/単体ステージ、L ループ、P 一時停止、1–4 速度、
B 背景、S 自動ショーケース。`-- --no-glow` は比較用に HDR ブルームを無効にします。

ダミーはカプセルです。任意のリグ付き代役で置き換えられます：`player.glb` と `target.glb`（高さ約 1 ユニット、
Mixamo 形式のボーン名、`idle`、`cast_a_spell`、`box_03`、`hit_to_head`、`hit_to_body_01`、`jump` という名前のクリップ）と、
任意の `<name>.materials.json`（部位 → 役割のマップ）を `vfx/characters/` に置き、`vfx init` を実行します。ダミーを変えると
ステージが変わります：ベースラインをレンダーし直し、ブルームのしきい値を計測し直してください
（[エンジン規約](engine-conventions.md) を参照）。

## チェック

`godot --path vfx/godot --fixed-fps 60 --script res://scripts/TestApi.gd` は、現在のマニフェストに対して play、launch、pause、speed、loop、
自動回収を試験します。`godot --headless --path vfx/godot --script res://scripts/ExportRuntime.gd` は
Godot のランタイムリソースをエクスポートします。これらは実際に実行した後でのみ、合格と報告してください。
