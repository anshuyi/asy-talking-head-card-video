# ASY真人卡片讲解 Skills

这是本次使用的真人口播卡片视频技能：真人圆窗＋浅色卡片动态图解，默认3:4、1080×1440，保留原视频声音。

当前专用版1.1.0固定使用内置卡片模板、1080×1440画布和30fps导出。保留六种内容图解（流程、因果、对比、要点、引用、观点）及字幕、真人同期圆窗。它是一个完整的本地制作流程，不是通用网页动画或视频剪辑工具箱。

## 安装

解压后，把 asy-talking-head-card-video 整个文件夹放入目标工具支持的技能目录。
在 Codex 中，通常放入用户目录下的 .codex/skills/，使结构为 .codex/skills/asy-talking-head-card-video/SKILL.md。重新打开会话后使用。
其他工具需支持 SKILL.md、本地文件操作和命令执行；此包不保证所有客户端和模型均可运行。

## 第一次使用

准备一条你自己的真人口播视频，可以没有字幕、没有文稿。向智能体发送：

“使用 ASY真人卡片讲解，把这条口播视频做成3:4真人圆窗＋浅色卡片动态图解，保留原声，自动转写核对字幕，根据内容安排图解，最后给我完整MP4。”

## 运行环境

这是一套技能、代码与模板，不是包含全部环境的独立软件。需要可用的 Python、FFmpeg/FFprobe、Python Playwright及浏览器、faster-whisper及转写模型、中文字体。根据本机条件配置，优先复用已安装环境。
请让智能体先阅读技能内 references/runtime.md，依照 examples/runtime.example.json 建立本机配置。不要把配置示例中的占位文字当作真实路径。模型配置应指向本机可用模型；CUDA是否可用及计算精度按硬件设置。
包不携带个人配置、密钥、私人视频、缓存、模型或运行库，不需要MiniMax配音密钥。

## 包含内容

技能说明、使用示例、图解模板、制作脚本、结构测试及渲染器MIT许可。
这是基于 xilo-opus-video 渲染器整理的真人卡片衍生工作流，不是作者原始整包。详见技能内 references/provenance.md。

视频封面制作属于另一独立技能，本包只包含真人卡片视频制作技能。

## GitHub 安装与下载

- 仓库：https://github.com/anshuyi/asy-talking-head-card-video
- 安装压缩包：https://github.com/anshuyi/asy-talking-head-card-video/releases/latest

可以下载 Release 中的 `ASY-talking-head-card-video-skills.zip`，解压后按上文安装。也可以将本仓库克隆为技能目录下的 `asy-talking-head-card-video` 文件夹；仓库根目录的 SKILL.md 是入口。

## 验证范围

运行 `python -m unittest discover -s tests -v` 检查时间线约束、专用命令边界、固定模板重建和编码失败保护。结构及模拟异常测试不能代替真实成片验收。已有本地真人口播制作验证；这些记录不等于在任意电脑、客户端或模型上都做过实测。新环境仍需配置并验证一次完整流程。

## 专用范围

- 本包只接受含声音的真人视频及对应结构化时间线；唯一制作命令入口是 `scripts/pipeline.py`。
- 只通过内置卡片模板输出完整3:4视频。项目HTML是可再生成的预览产物，手动替换它不会成为下一次导出的输入。
- 不提供任意网页/HTML、独立配音、其他画幅或帧率、片段截取、子帧特效、通用图片导出接口。流程内的画面预览正常保留。
- 1.1.0移除了原独立通用渲染脚本，改成流程内部模块；无需下载原作者的完整技能包。
- 这是功能范围精简，源码仍然可读可改。不能保证他人无法找到上游或自行开发其他用途；旧公开版本和Git历史仍然存在。

## 来源与许可

本项目为 ASY 真人卡片讲解衍生工作流。`scripts/card_renderer.py` 的浏览器启动与逐帧编码部分改编自 [Kianzzz/xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video)，随附原始 MIT 许可见 `vendor/LICENSE-xilo`。该许可文件对应所用的上游代码，不将其冒称为原作者对整个衍生项目的授权声明。
