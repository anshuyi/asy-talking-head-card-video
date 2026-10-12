# ASY真人卡片讲解 Skills

这是本次使用的真人口播卡片视频技能：真人圆窗＋浅色卡片动态图解，默认3:4、1080×1440，保留原视频声音。

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

发布前运行包内 13 项结构测试，检查技能文件和归档完整性。已有本地真人口播制作验证；这些记录不等于在任意电脑、客户端或模型上都做过实测。新环境仍需配置并验证一次完整流程。

## 来源与许可

本项目为 ASY 真人卡片讲解衍生工作流。`vendor/xilo-render.py` 的上游为 [Kianzzz/xilo-opus-video](https://github.com/Kianzzz/xilo-opus-video)，随附原始 MIT 许可见 `vendor/LICENSE-xilo`。该许可文件对应上游渲染器，不将其冒称为原作者对整个衍生项目的授权声明。
