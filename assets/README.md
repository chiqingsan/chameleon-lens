# 资产说明

- `app.png`：应用图标源图，使用用户提供的参考图片。
- `chameleon.ico`：由 `tools/generate_app_icon.py` 从源图裁切、透明化并生成，用于窗口图标、菜单 Logo 和 Nuitka 打包。

## 设计说明

- 不直接把原始图片塞进 ICO；生成脚本会裁掉白边、处理白色背景透明度，并输出 16px 到 256px 的多尺寸 ICO。
- 菜单左上角和应用窗口使用同一个 `chameleon.ico`，保证品牌标识一致。
