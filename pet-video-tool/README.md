# 宠物 IP 职场短视频 · 自动生成工具

每天一条：**大模型写职场脚本 → 宠物配音 → 画面（分镜视频或会动的 IP 图）→ 自动加标题和字幕 → 输出成片 MP4 + 剪映草稿**。

内容定位：宠物 IP 用第一人称讲职场梗、职场小故事，透露一点道理，重点是让打工人有共鸣、被理解、被安慰。

## 两种视频形式（`config.yaml` 里的 `mode`）

| 形式 | 画面 | 适合 |
|---|---|---|
| `story` 剧情 vlog（默认） | 每句旁白一个分镜：宠物像人一样在工位、电梯、地铁、街头生活，场景随故事切换 | 对标「小斗下班啦」这类写实 AI 萌宠账号 |
| `talking` 口播 | 同一张 IP 图全程对镜头说话，会张嘴、眨眼、按情绪做动作 | 零成本、日更压力小、卡通风格 IP |

剧情模式下，每个镜头的素材按这个顺序找：

1. 你放进当天 `shots/` 文件夹的 `shot_01.mp4`、`shot_02.png`……（可以复制 `shots.md` 里的提示词，去即梦或可灵手动生成）；
2. 设置了 `media.provider: ark` 和环境变量 `ARK_API_KEY` 时，调用火山方舟 Seedance，用你的 IP 图做参考图，自动生成 5 秒竖屏视频；
3. 都没有时，用 IP 图做本地动画兜底，保证一定能出片。

想换掉某个镜头，只需把文件替换掉，再运行 `python make_video.py --from-script output/某天/script.json`，工具会用新素材重新合成。

## 每天会产出什么

`output/日期_标题/` 下：

| 文件 | 用途 |
|---|---|
| `final.mp4` | 成片（1080×1920，带标题、字幕、配音），可直接发抖音/视频号/小红书 |
| `cover.jpg` | 封面（取"金句"那一帧） |
| `script.md` / `script.json` | 脚本、分镜、发布文案、话题标签；改 `script.json` 后可重新剪 |
| `shots.md`、`shots/` | 剧情模式的分镜表、每个镜头的提示词和素材 |
| `clean_no_subtitles.mp4`、`voice.wav`、`subtitles.srt` | 无字幕画面、配音、字幕，方便二次剪辑 |
| 剪映草稿 | 视频轨 + 配音轨 + 标题 + 字幕轨，打开剪映就能继续精修和导出 |

## 安装（第一次）

1. 安装 [Python 3.10+](https://www.python.org/downloads/)（Windows 安装时勾选 *Add to PATH*）和 [ffmpeg](https://ffmpeg.org/download.html)（Windows 可用 `winget install ffmpeg`，macOS 用 `brew install ffmpeg`）。
2. 在本文件夹里运行：

```bash
pip install -r requirements.txt
```

## 用起来

**1. 放上你的宠物 IP 图**：保存为 `assets/pet.png`。效果最好的是**抠好图的透明背景 PNG**（宠物会整体弹跳、摇摆、挤压拉伸）；普通图片也可以，动作会收敛一些。然后在 `config.yaml` 里改名字、人设和口头禅。

**2. 让宠物张嘴、眨眼（口播模式和兜底动画用）**：

```bash
python make_video.py --mark
```

打开 `output/pet_grid.png`，对照网格上的数字，把嘴巴、眼睛的位置填进 `config.yaml`：

```yaml
mouth: [0.50, 0.62, 0.16, 0.06]                          # 中心x, 中心y, 宽, 高（0~1）
eyes: [[0.40, 0.48, 0.09, 0.06], [0.60, 0.48, 0.09, 0.06]]
```

**3. 配置大模型，让它每天写新脚本**（不配也能用，会轮换内置脚本：剧情模式 3 条、口播模式 7 条）：

```bash
# macOS / Linux
export LLM_API_KEY=你的密钥
# Windows（设置一次，重开命令行后生效）
setx LLM_API_KEY 你的密钥
```

默认用 DeepSeek。换豆包、Kimi、通义千问、OpenAI 等兼容 OpenAI 接口的模型，再设置 `LLM_BASE_URL` 和 `LLM_MODEL` 即可。可以在 `config.yaml` 的 `llm.themes` 里维护选题方向，工具会自动避开最近发过的标题。

**4. 剧情模式自动生成分镜视频（可选）**：在 [火山方舟控制台](https://console.volcengine.com/ark) 开通 Seedance 视频生成并创建 API Key，然后：

```bash
export ARK_API_KEY=你的方舟密钥        # Windows：setx ARK_API_KEY 你的方舟密钥
```

接着把 `config.yaml` 里的 `media.provider` 改成 `ark`，并在 `pet.appearance` 里写清楚 IP 的固定外形（毛色、配饰，比如"背一个牛仔小挎包"）。这段描述会写进每个镜头的提示词，保证镜头之间是同一只宠物。还可以在 `pet.reference_images` 里放几张不同角度的 IP 图，形象会更稳定。视频生成按条计费，一条视频大约 7~10 个镜头，费用以方舟控制台的价格为准。

然后运行：

```bash
python make_video.py                     # 生成今天的视频
python make_video.py --topic 开不完的会    # 指定主题
python make_video.py --days 7            # 一次做好一周的
python make_video.py --script-only       # 只要脚本和分镜提示词
python make_video.py --mode talking      # 临时切换成口播
python make_video.py --from-script output/某天/script.json   # 改完脚本重新剪
```

## 省钱做法：素材库（推荐）

仓库里已经放好了一套现成的：`assets/pet.png` 是示例 IP「团团」（英短蓝猫幼猫，蓝色工牌、米色帆布小挎包），`assets/library/` 里有 17 个职场日常镜头，下载后直接运行就能出剧情视频。换成你自己的 IP 时，用你的 IP 图做参考图，按同样的文件名重新生成这些镜头即可。

每天都按镜头调用 AI 生成视频会很贵。职场日常的镜头其实高度重复（工位打字、趴桌叹气、捂脸崩溃、电梯、地铁、下班路上、喝奶茶），所以可以**一次性做好一套通用镜头，之后每天复用**：

```bash
python make_video.py --library-plan
```

运行后会生成 `output/library_plan.md`，里面有 24 个常用镜头的建议文件名和提示词。用即梦/可灵每天的免费额度，花几天时间慢慢生成这些镜头，然后按建议文件名（文件名就是标签，比如 `工位_打字_认真.mp4`）放进 `assets/library/`。如果愿意一次性付费，也可以运行 `python make_video.py --build-library` 自动生成缺的镜头。

之后每天出片时：

- 每句台词会按场景、动作、情绪自动匹配素材库里最贴合的镜头，并尽量不在同一条视频里重复使用；
- 配置了大模型时，脚本会尽量写成能用上素材库的场景；
- 匹配不到的镜头才走自动生成。用 `media.max_generated_per_video` 可以限制每条视频最多自动生成几个镜头（优先生成开头钩子和金句）；剩下的用本地动画兜底；
- 素材库里也可以放图片，图片镜头会缓慢推拉，成本只有视频的零头。

## 剪映

- 工具会自动找本机的剪映草稿目录（Windows：`%LOCALAPPDATA%\JianyingPro\User Data\Projects\com.lveditor.draft`；macOS：`~/Movies/JianyingPro/...`），生成后**打开剪映首页就能看到当天的草稿**。找不到时，可在 `config.yaml` 的 `jianying.draft_folder` 里手动填写。
- 草稿里的素材使用本机的绝对路径，所以要在装剪映的那台电脑上运行本工具。
- 草稿格式基于开源项目 [pyJianYingDraft](https://github.com/GuanYixuan/pyJianYingDraft)，剪映 5.x 兼容最好；较新版本的剪映如果打不开草稿，直接用 `final.mp4` 即可，它不依赖剪映。
- 在剪映里可以继续换"文本朗读"音色、加贴纸和音效、套字幕样式。

## 口播模式：用 AI 动作片段让宠物动得更自然（可选）

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

**推荐：GitHub 定时任务（已配好，`.github/workflows/daily-video.yml`）**。每天北京时间 8 点，GitHub 会自动出当天的视频，发到仓库的 **Releases** 页面。每天一条，里面有视频、封面、可直接复制的文案和话题，用手机浏览器或 GitHub App 就能下载。

- 选题来源：`content/<日期>.json` 有排好的剧本就用排好的；没有的话，设置了 `LLM_API_KEY` 就由大模型现写，写好的剧本会自动存回 `content/`，用于之后去重。
- 设置大模型：仓库 Settings → Secrets and variables → Actions，在 Secrets 里添加 `LLM_API_KEY`（比如 DeepSeek 的密钥）。如果用别家模型，再到 Variables 里添加 `LLM_BASE_URL` 和 `LLM_MODEL`。
- 手动补跑：Actions → 团团每日视频 → Run workflow，可以指定日期。

另一种方式是交给 Cursor 云端 Agent。它还能自己补拍新镜头，但需要在 Cursor 网页上手动创建自动化，提示词见 [`automation_prompt.md`](automation_prompt.md)。发布时间和文案见 `content/发布日历.md`。

如果想在自己电脑上跑（需要设置 `LLM_API_KEY`，否则会轮换使用内置剧本）：

- **Windows**：打开"任务计划程序"，选择"创建基本任务"，触发器设为"每天"，操作选"启动程序"并指向 `daily.bat`。
- **macOS / Linux**：运行 `crontab -e`，加一行 `0 8 * * * /路径/pet-video-tool/daily.sh`（每天 8 点）。

## 配音说明

默认使用免费的微软 edge-tts（`zh-CN-XiaoyiNeural`，活泼女声），需要联网。少年感音色可以换 `zh-CN-YunxiNeural`，在 `config.yaml` 的 `tts` 里调整语速和音调。edge-tts 连不上时，会依次退回谷歌语音 gTTS（免费，可调语速和音调），再退回离线的 espeak-ng（机械音，只适合测试，需要另外安装）。
