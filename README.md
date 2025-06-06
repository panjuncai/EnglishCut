# 🎵 音频/视频转文本和字幕生成器

## 📋 项目概览

这是一个基于 OpenAI Whisper 和 GPT 翻译的音频/视频转文本和双语字幕生成工具。项目支持多种音频和视频格式，能够生成高质量的 LRC 和 SRT 字幕文件。

## ✨ 主要功能

### 🎵 音频处理
- **格式支持**: WAV, FLAC, MP3, AAC, OGG, M4A
- **语音识别**: 基于 OpenAI Whisper 模型
- **字幕格式**: 支持 LRC 和 SRT 格式
- **双语字幕**: 支持英中双语字幕生成

### 🎬 视频处理
- **格式支持**: MP4, AVI, MOV, MKV, WMV, FLV, WebM, M4V
- **音频提取**: 自动从视频中提取音频进行处理
- **字幕格式**: 支持 SRT 格式（推荐用于视频）
- **双语字幕**: 支持英中双语字幕生成

### 🌐 翻译功能
- **翻译引擎**: 基于 OpenAI GPT 模型
- **智能分段**: 保持时间戳对应的分段翻译
- **质量保证**: 高质量的英中翻译

## 🏗️ 项目架构

### 核心模块

```
src/
├── media_processor.py      # 统一多媒体处理器
├── file_detector.py        # 文件类型检测模块
├── video_processor.py      # 视频处理模块
├── openai_whisper.py      # 语音识别模块
├── openai_translate.py    # 翻译模块
├── gradio_server.py       # Web界面服务器
└── logger.py              # 日志模块
```

### 测试脚本

```
test_video_processing.py     # 视频处理功能测试
test_srt_subtitles.py       # SRT字幕功能测试
test_bilingual_subtitles.py # 双语字幕功能测试
test_media_processor_fix.py # MediaProcessor修复验证
debug_env.py                # 环境变量调试
test_connection.py          # 网络连接测试
```

### 配置文件

```
requirements.txt     # Python依赖包
.env.example        # 环境变量示例
.env               # 环境变量配置（需创建）
```

## 🚀 快速开始

### 1. 环境准备

```bash
# 激活conda环境
conda activate englishcut

# 安装依赖
pip install -r requirements.txt

# 安装 ffmpeg (用于视频处理)
# Windows: 下载并配置到PATH
# Mac: brew install ffmpeg
# Linux: apt-get install ffmpeg
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，配置API密钥
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=your_api_base_url
```

### 3. 运行测试

```bash
# 测试基础功能
python debug_env.py

# 测试网络连接
python test_connection.py

# 测试MediaProcessor修复
python test_media_processor_fix.py

# 测试视频处理
python test_video_processing.py

# 测试字幕生成
python test_srt_subtitles.py
python test_bilingual_subtitles.py
```

### 4. 启动Web界面

```bash
python src/gradio_server.py
```

然后在浏览器中访问 `http://localhost:7860`

## 📝 字幕格式说明

### LRC 格式
```
[00:12.34]Hello world
[00:15.67]This is a test
```
- 适用于音频文件
- 音乐播放器支持
- 逐行显示歌词

### SRT 格式
```
1
00:00:12,340 --> 00:00:15,670
Hello world

2
00:00:15,670 --> 00:00:18,890
This is a test
```
- 适用于视频文件
- 视频播放器广泛支持
- 支持时间范围显示

### 双语字幕示例

**LRC双语格式:**
```
[00:12.34]Hello world
[00:13.45]你好世界
[00:15.67]This is a test
[00:16.78]这是一个测试
```

**SRT双语格式:**
```
1
00:00:12,340 --> 00:00:15,670
Hello world
你好世界

2
00:00:15,670 --> 00:00:18,890
This is a test
这是一个测试
```

## 🔧 技术特点

### 模块化设计
- **文件检测器**: 统一处理文件类型识别
- **媒体处理器**: 统一的音频/视频处理接口
- **视频处理器**: 专门处理视频文件的音频提取
- **错误处理**: 完善的异常处理和日志记录

### 智能格式选择
- 音频文件：支持 LRC 和 SRT 格式
- 视频文件：仅支持 SRT 格式（更适合视频播放）
- 自动根据文件类型调整界面选项

### 高效处理
- 临时文件管理：自动清理提取的音频文件
- 内存优化：分块处理大文件
- 并发支持：支持多用户同时使用

### 用户友好
- 实时进度显示
- 详细的文件信息
- 清晰的错误提示
- 支持文件拖拽上传

## 🛠️ 依赖组件

### 核心依赖
- **OpenAI Whisper**: 语音识别引擎
- **OpenAI API**: GPT翻译服务
- **FFmpeg**: 音频/视频处理
- **Gradio**: Web界面框架

### Python包
- `torch`: 机器学习框架
- `gradio`: Web界面
- `openai`: OpenAI API客户端
- `ffmpeg-python`: FFmpeg Python包装
- `httpx`: HTTP客户端（代理支持）

## 📊 性能优化

### 音频处理优化
- 支持多种采样率
- 自动音频格式转换
- 分段处理长音频

### 视频处理优化
- 高效的音频提取
- 临时文件管理
- 支持大视频文件

### 翻译优化
- 智能分段翻译
- 保持时间戳对应
- 错误重试机制

## 🐛 故障排除

### 常见问题

1. **ffmpeg 未找到**
   ```bash
   # 确保ffmpeg已安装并在PATH中
   ffmpeg -version
   ```

2. **OpenAI API连接失败**
   ```bash
   # 检查网络和API配置
   python test_connection.py
   ```

3. **环境变量未加载**
   ```bash
   # 检查.env文件配置
   python debug_env.py
   ```

4. **依赖包版本冲突**
   ```bash
   # 重新安装依赖
   pip install -r requirements.txt --force-reinstall
   ```

### 日志查看
项目使用详细的日志记录，可以通过日志信息定位问题：
- `🎵` 表示音频处理
- `🎬` 表示视频处理
- `🌐` 表示翻译功能
- `❌` 表示错误信息
- `✅` 表示成功操作

## 🔄 更新日志

### v2.0.1 - MediaProcessor 重要修复
- 🔧 **修复**: 修正了 MediaProcessor 中的函数导入错误
- ✅ **改进**: 现在正确使用 `openai_whisper.py` 中的 `asr` 函数
- 🚀 **优化**: 充分利用 `openai/whisper-large-v3` 高质量模型
- 🧪 **新增**: 添加 `test_media_processor_fix.py` 验证修复
- 📝 **更新**: 简化了处理流程，移除了重复的翻译逻辑

### v2.0.0 - 视频处理支持
- ✅ 新增视频文件处理功能
- ✅ 统一的多媒体处理器
- ✅ 模块化架构重构
- ✅ 智能文件类型检测
- ✅ 完善的测试套件
- ✅ 改进的用户界面

### v1.0.0 - 基础功能
- ✅ 音频转文本功能
- ✅ LRC/SRT字幕生成
- ✅ 双语字幕支持
- ✅ Web界面

## 📄 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进项目！

## 📞 支持

如果您在使用过程中遇到问题，请：
1. 查看故障排除部分
2. 运行测试脚本诊断问题
3. 提交 Issue 描述具体问题 