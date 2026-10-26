# 模型文件

当前目录的 `逐光中南_v19.blend` 是贴图已打包的最终源文件，未因本轮摄影而改动。

[Release](https://github.com/sunfleeting-debug/glow-csu-campus-timer/releases/tag/v19-final) 同时提供：

- `glow-csu-v19.glb`：通用模型，下载后可直接用支持 glTF 2.0 的查看器打开；参与本地校验时重命名为 `逐光中南_v19.glb` 放到本目录。
- `glow-csu-v19-complete.zip`：完整项目快照，含四个模型原件、25 张正式图片、说明与源码。
- `glow-csu-v19-photos.zip`：轻量光影图集。
- `SHA256SUMS.txt`：Release 附件与四个模型的校验值。

OBJ/MTL 从完整包获得，保持两者在同一目录。使用 `python scripts/verify_sources.py --all` 可验证所有已下载并按原名放进本目录的模型；未下载交换文件时可不带 `--all` 只验证现有文件。
