---
name: voice-reply
version: 1.0.0
description: 語音雙模回覆技能。使用 Edge TTS (免費) 生成語音回覆，使用 Whisper 轉錄語音輸入。
metadata: 
  emoji: 🎙️
  requires:
    bins:
      - ffmpeg
    pip:
      - openai-whisper
      - edge-tts
  install:
    - id: pip
      kind: pip
      packages:
        - openai-whisper
        - edge-tts
      label: "pip install openai-whisper edge-tts"
    - id: brew
      kind: brew
      formula: ffmpeg
      label: "brew install ffmpeg"
---

# Voice Reply Skill

語音雙模回覆技能 - 支援語音輸入轉文字與文字轉語音輸出。

## 🎙️ 功能說明

| 功能 | 技術 | 說明 |
|------|------|------|
| 語音輸入 | Whisper | 將語音訊息轉換為文字 |
| 語音輸出 | Edge TTS | 將文字轉換為語音回覆 |

**特點**：
- 完全免費，無需 API Key
- 支援多種中文女生聲音
- 離線運行（Whisper 模型需首次下載）

---

## 🔊 可用聲音（中文女生）

| Voice ID | 風格 | 描述 |
|----------|------|------|
| `zh-TW-HsiaoChenNeural` | General | 台灣，友善正向 ✅ **默認** |
| `zh-TW-HsiaoYuNeural` | General | 台灣，另一種風格 |
| `zh-CN-XiaoxiaoNeural` | News, Novel | 大陸，溫暖 |
| `zh-CN-XiaoyiNeural` | Cartoon, Novel | 大陸，活潑 |
| `zh-HK-HiuGaaiNeural` | General | 香港，友善正向 |

---

## 📦 環境需求

| 依賴 | 安裝方式 |
|------|----------|
| Python | 3.9+ |
| ffmpeg | `brew install ffmpeg` |
| openai-whisper | `pip3 install --user openai-whisper` |
| edge-tts | `pip3 install --user edge-tts` |

---

## 🛠️ 使用方式

### 轉錄語音輸入（Whisper）

```python
import whisper

# 載入模型（首次會下載模型檔案）
model = whisper.load_model('tiny')  # tiny/base/small/medium

# 轉錄語音
result = model.transcribe('/path/to/audio.ogg')
print(result['text'])
```

**模型選擇**：
| 模型 | 速度 | 準確度 | 大小 |
|------|------|--------|------|
| tiny | 最快 | 一般 | ~72MB |
| base | 快 | 較好 | ~142MB |
| small | 中等 | 好 | ~466MB |
| medium | 慢 | 很好 | ~1.5GB |

### 生成語音回覆（Edge TTS）

```bash
# 基本用法
edge-tts \
  --text "你好，我是寶寶！" \
  --voice zh-TW-HsiaoChenNeural \
  --write-media output.mp3

# 列出所有可用聲音
edge-tts --list-voices
```

### Python 整合範例

```python
import subprocess

def text_to_speech(text, voice='zh-TW-HsiaoChenNeural', output='/tmp/voice.mp3'):
    """將文字轉換為語音"""
    import shutil
    edge_tts_path = shutil.which('edge-tts')
    if not edge_tts_path:
        # 嘗試常見路徑
        edge_tts_path = '/Users/claw/Library/Python/3.9/bin/edge-tts'
    
    cmd = [
        edge_tts_path,
        '--text', text,
        '--voice', voice,
        '--write-media', output
    ]
    subprocess.run(cmd, check=True)
    return output

# 使用
audio_file = text_to_speech('你好！很高興為你服務。')
```

---

## ⚙️ 配置

默認使用：
- Whisper model: `tiny` (快速，適合即時對話)
- TTS voice: `zh-TW-HsiaoChenNeural` (台灣女生聲音)

可在 TOOLS.md 中修改偏好設定。

---

## 📁 相關檔案

| 檔案 | 說明 |
|------|------|
| `~/.cache/whisper/` | Whisper 模型下載位置 |
| `~/.qclaw/workspace/skills/voice-reply/SKILL.md` | 本 Skill 定義 |
| `~/.qclaw/workspace/TOOLS.md` | 語音偏好設定 |
