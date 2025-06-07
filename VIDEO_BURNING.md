# 📱 移动端视频烧制功能说明

## 🎯 功能概述

移动端视频烧制功能将COCA排名>5000的重点单词烧制到竖屏视频中，专为手机观看美国新闻设计。通过将16:9横屏视频裁剪为3:4竖屏，并在底部显示分层的重点单词、音标和中文解释，为移动端学习者提供最佳的无字幕观看体验。

## ✨ 核心特性

### 🔍 智能词汇筛选
- **筛选条件**: COCA排名 > 5000 且不为空
- **重要性排序**: 排名越高（数字越大）= 频率越低 = 越重要
- **冲突处理**: 一条字幕多个词汇时，自动选择最重要的
- **长度优化**: 相同重要性时选择更短的词汇

### 📱 移动端优化设计
- **视频格式**: 智能裁剪 16:9 → 3:4 竖屏 (完美适配手机)
- **字幕样式**: 底部居中，橙色背景，黑色字体，高对比度
- **分层字体**: 单词24pt > 中文18pt > 音标14pt (适合手机屏幕)
- **时间同步**: 烧制时长 = 字幕时间段

### 🔄 批处理能力
- 一次处理整个系列的所有字幕
- 自动跳过无重点词汇的字幕
- 实时进度显示和状态更新

## 📋 使用流程

### 1. 准备工作
确保系统已安装以下依赖：
```bash
# 检查FFmpeg
which ffmpeg

# 如果未安装，可以通过以下方式安装
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
# 下载并安装 FFmpeg
```

### 2. 数据准备
在使用烧制功能前，请确保：
- ✅ 已导入视频系列
- ✅ 已提取字幕文本
- ✅ 已使用AI提取关键词
- ✅ 已更新COCA排名信息

### 3. 操作步骤

#### 步骤1: 预览烧制信息
1. 在"🎬 视频烧制"标签页中输入系列ID
2. 点击"👀 预览烧制信息"
3. 查看统计信息：
   - 重点单词数量
   - 烧制时长
   - 词频分布
   - 示例单词

#### 步骤2: 执行烧制
1. 设置输出目录（默认: `output`）
2. 点击"🎬 开始烧制"
3. 等待FFmpeg处理完成
4. 查看烧制结果

## 📊 技术实现

### 核心算法
```python
# 1. 筛选重点词汇
eligible_keywords = [kw for kw in keywords if kw.get('coca', 0) > 5000]

# 2. 选择最重要的词汇
sorted_keywords = sorted(
    keywords,
    key=lambda x: (-x.get('coca', 0), len(x.get('key_word', '')))
)
selected = sorted_keywords[0]

# 3. 生成字幕文件
subtitle_text = f"{keyword} {phonetic}\n{explanation}"
```

### FFmpeg处理链
```bash
ffmpeg -i input.mp4 \
  -vf "scale=-1:ih,\
       crop=ih*3/4:ih:(iw-ow)/2:0,\
       ass='keywords.ass'" \
  -aspect 3:4 -c:a copy -preset medium -crf 23 \
  output_keywords_mobile.mp4
```

## 📈 示例效果

### 输入数据
```
字幕1 (0:00-0:02): "This technology is revolutionary"
关键词: technology (COCA: 15000), revolutionary (COCA: 18000)
选择: revolutionary (更重要)
```

### 输出效果 (ASS格式)
```ass
Dialogue: 0,0:00:00.00,0:00:02.00,Keyword,,0,0,0,,{\rKeyword}revolutionary\N{\rChinese}革命性的\N{\rPhonetic}ˌrevəˈluːʃəˌneri
```

**实际显示效果**:
- **revolutionary** (24pt, 粗体, 黑色)
- 革命性的 (18pt, 常规, 黑色)  
- ˌrevəˈluːʃəˌneri (14pt, 常规, 黑色)
- 🟡 深黄色背景条 (贴底部显示)

## ⚙️ 配置选项

### 视频质量设置
- **编码预设**: medium (平衡质量和速度)
- **质量控制**: CRF 23 (高质量)
- **音频处理**: 直接复制原音频

### ASS字幕样式定制
```python
# 单词样式 (最大最醒目)
keyword_style = {
    'Fontname': 'Arial',
    'Fontsize': 24,                 # 调小字体
    'Bold': 1,
    'PrimaryColour': '&H00000000',  # 黑色
    'BackColour': '&H0000B2FF',     # 深黄色背景
    'BorderStyle': 3,               # 背景框
    'Alignment': 2,                 # 底部居中
    'MarginV': 20                   # 贴底部边距
}

# 中文样式 (中等)
chinese_style = {
    'Fontname': 'Arial',
    'Fontsize': 18,                 # 调小字体
    'PrimaryColour': '&H00000000',  # 黑色
    'BackColour': '&H0000B2FF',     # 深黄色背景
}

# 音标样式 (最小)
phonetic_style = {
    'Fontname': 'Arial',
    'Fontsize': 14,                 # 调小字体
    'PrimaryColour': '&H00000000',  # 黑色
    'BackColour': '&H0000B2FF',     # 深黄色背景
}
```

## 🔧 故障排除

### 常见问题

#### 1. FFmpeg命令失败
**症状**: 烧制过程中报错
**解决方案**:
```bash
# 检查FFmpeg版本
ffmpeg -version

# 检查输入文件
ffmpeg -i input.mp4

# 测试简单转换
ffmpeg -i input.mp4 -t 10 test_output.mp4
```

#### 2. 没有重点词汇
**症状**: 预览显示0个重点单词
**解决方案**:
- 检查是否已提取关键词
- 检查COCA排名是否已更新
- 确认筛选条件 (COCA > 5000)

#### 3. 输出文件过大
**症状**: 烧制后文件很大
**解决方案**:
- 调整CRF值 (提高数字降低质量)
- 使用更快的编码预设
- 考虑降低分辨率

### 日志调试
```python
# 查看详细日志
from logger import LOG
LOG.setLevel(logging.DEBUG)

# 手动测试烧制
from video_subtitle_burner import video_burner
preview = video_burner.get_burn_preview(series_id)
print(preview)
```

## 📁 文件结构

### 输入文件
- `input_video.mp4` - 原始视频 (16:9)
- `data/englishcut.db` - 数据库 (字幕+关键词)

### 输出文件
- `output/video_keywords_mobile.mp4` - 烧制后视频 (3:4竖屏)
- `temp/keywords.ass` - 临时ASS字幕文件 (自动清理)

### 目录结构
```
EnglishCut/
├── src/
│   ├── video_subtitle_burner.py  # 烧制核心
│   ├── database_interface.py     # 界面集成
│   └── database.py              # 数据操作
├── output/                      # 输出目录
├── test/
│   └── test_video_burn.py       # 测试脚本
└── VIDEO_BURNING.md            # 本文档
```

## 🎉 最佳实践

### 1. 数据质量优化
- 使用高质量的AI关键词提取
- 确保COCA数据的准确性
- 人工审核重要词汇的解释

### 2. 批量处理建议
- 一次处理一个系列
- 监控磁盘空间
- 定期清理临时文件

### 3. 学习效果优化
- 重点词汇密度适中 (不超过每分钟5个)
- 确保单词解释简洁明了
- 考虑添加词汇难度标记

## 🚀 未来增强

### 计划功能
- [ ] 支持多种字幕样式主题
- [ ] 添加词汇复现率统计
- [ ] 支持自定义COCA阈值
- [ ] 集成语音播报功能
- [ ] 支持批量系列处理
- [ ] 添加学习进度跟踪

### 性能优化
- [ ] GPU加速编码支持
- [ ] 并行处理多个视频
- [ ] 智能缓存机制
- [ ] 增量更新支持

---

**💡 提示**: 这个功能特别适合英语学习者在手机上观看美国新闻，竖屏格式让通勤时间的学习更加便利，分层的字体设计确保重点词汇清晰可见，橙色背景提供良好的视觉对比度。 