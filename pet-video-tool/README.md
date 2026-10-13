# 宠物 IP 职场口播视频 · 自动生成工具

每天一条：**大模型写职场脚本 → 宠物配音 → 宠物图片动起来（说话、眨眼、按情绪做动作）→ 自动加标题和字幕 → 输出成片 MP4 + 剪映草稿**。

内容定位：宠物 IP 用第一人称讲职场梗、职场小故事，透露一点道理，重点是让打工人有共鸣、被理解、被安慰。

## 每天会产出什么

`output/日期_标题/` 下：

| 文件 | 用途 |
|---|---|
| `final.mp4` | 成片（1080×1920，带标题、字幕、配音），可直接发抖音/视频号/小红书 |
| `cover.jpg` | 封面（取"金句"那一帧） |
| `script.md` / `script.json` | 脚本、发布文案、话题标签；改 `script.json` 后可重新剪 |
| `clean_no_subtitles.mp4`、`voice.wav`、`subtitles.srt` | 无字幕画面、配音、字幕，方便二次剪辑 |
| 剪映草稿 | 视频轨 + 配音轨 + 标题 + 字幕轨，打开剪映就能继续精修和导出 |

## 安装（第一次）

1. 安装 [Python 3.10+](https://www.python.org/downloads/)（Windows 安装时勾选 *Add to PATH*）和 [ffmpeg](https://ffmpeg.org/download.html)（Windows 可用 `winget install ffmpeg`，macOS 用 `brew install ffmpeg`）。
2. 在本文件夹里运行：

```bash
pip install -r requirements.txt
```

## 三步用起来

**1. 放上你的宠物 IP 图**：保存为 `assets/pet.png`。效果最好的是**抠好图的透明背景 PNG**（宠物会整体弹跳、摇摆、挤压拉伸）；普通图片也可以，动作会收敛一些。然后在 `config.yaml` 里改名字、人设和口头禅。

**2. 让宠物张嘴、眨眼（推荐）**：

```bash
python make_video.py --mark
```

打开 `output/pet_grid.png`，对照网格上的数字，把嘴巴、眼睛的位置填进 `config.yaml`：

```yaml
mouth: [0.50, 0.62, 0.16, 0.06]                          # 中心x, 中心y, 宽, 高（0~1）
eyes: [[0.40, 0.48, 0.09, 0.06], [0.60, 0.48, 0.09, 0.06]]
```

**3. 配置大模型，让它每天写新脚本**（不配也能用，会轮换内置的 7 条职场脚本）：

```bash
# macOS / Linux
export LLM_API_KEY=你的密钥
# Windows（设置一次，重开命令行后生效）
setx LLM_API_KEY 你的密钥
```

默认用 DeepSeek。换豆包、Kimi、通义千问、OpenAI 等兼容 OpenAI 接口的模型，再设置 `LLM_BASE_URL` 和 `LLM_MODEL` 即可。可以在 `config.yaml` 的 `llm.themes` 里维护选题方向，工具会自动避开最近发过的标题。

然后运行：

```bash
python make_video.py                     # 生成今天的视频
python make_video.py --topic 开不完的会    # 指定主题
python make_video.py --days 7            # 一次做好一周的
python make_video.py --script-only       # 只要脚本
python make_video.py --from-script output/某天/script.json   # 改完脚本重新剪
```

## 剪映

- 工具会自动找本机的剪映草稿目录（Windows：`%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft`；macOS：`~/Movies/JianyingPro/...`），生成后**打开剪映首页就能看到当天的草稿**。找不到时，可在 `config.yaml` 的 `jianying.draft_folder` 里手动填写。
- 草稿里的素材使用本机的绝对路径，所以要在装剪映的那台电脑上运行本工具。
- 草稿格式基于开源项目 [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)，剪映 5.x 兼容最好；较新版本的剪映如果打不开草稿，直接用 `final.mp4` 即可，它不依赖剪映。
- 在剪映里可以继续换"文本朗读"音色、加贴纸和音效、套字幕样式。

## 让宠物动得更自然：AI 动作片段（可选）

本地动画的原理是让图片做呼吸、点头、弹跳、张嘴、眨眼和情绪动作，零成本，适合卡通风格的 IP。想要更真实的动作（转头、挥爪、捂脸），可以用 **即梦 / 可灵 / Runway** 的"图生视频"，拿你的 IP 图做几段 5~10 秒的动作视频（最好首尾衔接，方便循环），然后在 `config.yaml` 里填写：

```yaml
motion_clips:
  calm: assets/clips/calm.mp4     # 必填：平静说话
  happy: assets/clips/happy.mp4
  sad: assets/clips/sad.mp4
  shock: assets/clips/shock.mp4
  angry: assets/clips/angry.mp4
```

这些片段只需做一次。之后每天的视频会根据每句台词的情绪自动切换片段，并循环补足时长。

## 每天自动跑

- **Windows**：打开"任务计划程序"，选择"创建基本任务"，触发器设为"每天"，操作选"启动程序"并指向 `daily.bat`。
- **macOS / Linux**：运行 `crontab -e`，加一行 `0 8 * * * /路径/pet-video-tool/daily.sh`（每天 8 点）。

## 配音说明

默认使用免费的微软 edge-tts（`zh-CN-XiaoyiNeural`，活泼女声），需要联网。少年感音色可以换 `zh-CN-YunxiNeural`，在 `config.yaml` 的 `tts` 里调整语速和音调。edge-tts 连不上时，会自动退回离线的 espeak-ng（机械音，只适合测试，需要另外安装）。
