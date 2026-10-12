# 数据契约

项目中timeline.json：

- duration：source.json的实际音视频总时长，不能硬编码62秒。
- header：本条主题系列名，最多18个字符。
- crop：x/y/size为源像素，reviewed是实际视觉检查状态，reason说明安全取景依据。
- transcript_review：status为machine/draft/reviewed，method为实际校对方式，unresolved为尚未解决问题列表。
- captions：start/end秒、text、source_span（真实音轨起止）；可选display:false及hidden_reason。
- scenes：start/end连续覆盖全片、mode、tag、title数组（1—2行）、purpose、source_span、items数组、note、side两行。每个item含at秒、label、可选detail。

字幕与场景独立，字幕不得交叉或越界。所有时间必须是有限数字。图解只展示属于当前scene的items；at在该scene内。scene数量依口播，不复制示例。异常数据先修正，禁止用默认值掩盖。

script的validate检查结构、时序、取景边界和文本规模；浏览器实际字宽检查放在preview/render阶段。自动检查不验证语义是否来自音轨，执行智能体仍须逐段核对。
