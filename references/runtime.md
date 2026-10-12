# 本地执行

运行 `python scripts/pipeline.py --config 本机配置.json init --source 用户视频.mp4 --project 新项目目录`。后续命令均附 `--project 同一目录`；config是全局参数，放在子命令之前。

配置可通过 `--config`、环境变量 `ASY_CARD_CONFIG` 或默认用户目录 `.codex/asy-card-video/runtime.json` 提供。配置在技能包外，字段见 `examples/runtime.example.json`。复用本机现有依赖和离线模型；禁止为新片重复安装。找不到依赖时明确报出，不静默切云端。

先读取配置中的python_executable，命令里的python指该实际解释器；不能假定系统PATH里的python装有依赖。language默认zh，仅在实际音轨为其他语言时配置调整。字体、模型、运行库路径不得直接照搬到别人的机器。

命令顺序：init → transcribe → 智能体编写timeline.json → validate → preview → render → check。

init 保存 source.json 和媒体元数据，不复制或修改源片。输出目录必须新建或为空，防止混入另一条片子。transcribe 保存包含真实词级起止的 transcript-machine.json。重复转写需显式 `--replace`，旧结果留版本备份；失败不能覆盖已完成结果。

preview 生成开头、中间、结尾关键帧，检查人物和文字，再设置crop.reviewed。render可用 `--draft` 或正式模式；前者文件名必须包含draft或候选。正式模式要求字幕已校核、人物裁切已检查。该标记由实际工作的智能体记录，不是要求用户逐步点批准。

check 必须带 `--name` 指明本次输出，验证媒体、完整解码、原声音轨和来源未变。更换或修改源文件后不能继续复用旧项目。修改timeline后不能拿旧成片检查结果冒充新结果。

本地渲染：pipeline调用内部scripts/card_renderer.py，以内置卡片模板逐帧生成固定1080×1440、30fps的无声图解层，再由FFmpeg叠加同期原视频圆窗和原声。字体来自本机配置，内容来自timeline.json。人脸安全取景和图解设计仍需智能体判断。

只使用上述六个pipeline子命令。内部渲染模块不能作为命令行运行，不接受page、URL、size、fps、audio、start、subframes或still等通用参数。无需寻找、下载或安装另一个动画技能。修改timeline后再次preview/render会重建index.html，不保留手改页面。不要直接套本机绝对路径或特定录音名。

运行源有旋转元数据或非方形像素时：先在项目中生成保持时长的规范化工作副本，原文件保留，记录变换后重新init；脚本遇到这类输入会停止并说明，不以错误尺寸裁切。
