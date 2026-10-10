# 对照参考视频

需要 `ffmpeg` 和 `ffprobe`。只使用用户提供的或允许使用的视频；记录它们的来源。

1. `vfx reference-import <clip.mp4> --start 0 --end 2 --slow 2 [--roi x y w h] [--source-url <url>]` 最多解码 30 秒媒体时长，
   写入被忽略的 `vfx/work/references/`。`--slow 2` 表示视频以半速播放，因此效果时间 = 相对 `--start` 的视频时间 ÷ 2。
   打开返回的 `overview` 图片。把参考 ID 和时间写进简报的 `reference` 字段。
2. 按顺序阅读带标签的帧，把预兆、接触、主体、次级运动和退场写进简报的 beats。需要细节时，对一小段使用
   `vfx reference-frames <reference_id> <start> <end> --count 8`，而不是重新载入整个视频。如果不知道视频的速度而节奏又依赖它，就去问。
3. 复查之后，`vfx reference-compare <reference_id> <evidence_id> --times 0.1 0.3` 把参考时刻与精确采集到的 Godot 帧配对
   （缺失的帧用 `vfx review --key-frames` 补采）。对比节奏、轮廓、画面占比、饱和主体、暗层和残留。每个视图保留自己的宽高比和时间标签；
   绝不用未说明的裁切或缩放把它们"做成一样大"。

这种分析是近似的：压缩、背景和泛光会改变像素；镜头移动或剪辑会污染变化区域。镜头移动时，使用手动关键帧和明确的 ROI。
不要从视频推断世界尺寸、emissive 数值、粒子数量或看不见的纹理；在简报中标明近似值。参考观察指导形状和节奏；
它们绝不能推翻本引擎实测的单位、UV、HDR 和继承规则。
