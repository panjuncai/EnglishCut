# 🤖 AI关键词提取功能使用指南

## 🎯 功能介绍

EnglishCut 现已集成 OpenAI API，可以智能分析字幕内容，自动提取适合大学生英语水平的重点词汇。

## ✨ 核心特性

### 🎓 智能分析
- **目标水平**: 专门针对大学生四六级英语水平
- **智能筛选**: 自动过滤过于简单的词汇（如 the, a, is 等）
- **包含短语**: 提取有价值的短语和搭配

### 📚 完整信息
- **国际音标**: 提供标准的国际音标
- **中文解释**: 简洁准确的中文释义
- **精确对应**: 关键词与具体字幕精确关联

### ⚡ 高效处理
- **批量分析**: 支持整个系列的字幕批量处理
- **上下文理解**: 考虑语境，提取更准确的词汇
- **自动保存**: 提取结果直接保存到数据库

## 🚀 使用方法

### 1. 准备工作
确保您已经：
- ✅ 处理了音视频文件，生成了字幕
- ✅ 数据已保存到数据库
- ✅ 配置了有效的 OpenAI API Key

### 2. 访问管理界面
1. 启动服务：`python start_services.py`
2. 访问数据库管理界面：http://localhost:7861
3. 切换到 **"📚 关键词库"** 标签页

### 3. 执行AI提取
1. 在 **"按系列ID查看"** 输入框中输入要分析的系列ID
2. 点击 **"🤖 AI提取关键词"** 按钮
3. 等待AI分析完成（会显示实时进度）
4. 提取完成后，关键词自动保存到数据库

### 4. 查看结果
- 使用 **"📚 加载关键词"** 查看提取的词汇
- 使用 **"🔍 搜索"** 功能快速查找特定词汇
- 在关键词列表中查看音标和解释

## 📖 使用示例

### 输入文本示例
```
"Today we will discuss artificial intelligence and machine learning. 
These technologies are becoming increasingly important in our daily lives."
```

### AI提取结果
```
1. artificial intelligence /ˌɑːtɪˈfɪʃəl ɪnˈtelɪdʒəns/ - 人工智能
2. machine learning /məˈʃiːn ˈlɜːrnɪŋ/ - 机器学习
3. increasingly /ɪnˈkriːsɪŋli/ - 日益，越来越
4. important /ɪmˈpɔːrtənt/ - 重要的
```

## 🔧 技术原理

### AI分析流程
1. **文本预处理**: 清理和整理字幕文本
2. **智能分析**: 使用 GPT-3.5-turbo 分析文本
3. **专业提示**: 基于大学生英语水平的专业提示词
4. **结果解析**: 自动解析AI返回的词汇、音标、解释
5. **数据库存储**: 关联到具体字幕并保存

### 批量处理策略
- **分批处理**: 将字幕分成小批次（3-5条），提高效率
- **上下文保持**: 保持语境连贯性，提取更准确的词汇
- **智能匹配**: 自动将关键词匹配到最相关的字幕

## 💡 使用技巧

### 📈 提高提取质量
1. **选择合适内容**: 学术、新闻、教育类音视频效果更好
2. **确保字幕质量**: 清晰准确的字幕能获得更好的提取结果
3. **合理批次大小**: 系统默认批次大小已优化，无需调整

### 🎯 学习建议
1. **系统复习**: 定期查看提取的关键词，建立词汇库
2. **上下文学习**: 结合字幕内容学习词汇，理解使用场景
3. **音标练习**: 利用提供的音标练习发音
4. **主动添加**: 手动添加AI未提取但您认为重要的词汇

## 🔍 功能组合

### 与其他功能的配合
- **字幕生成** → **AI关键词提取** → **词汇学习**
- **搜索功能**: 跨文件搜索学过的词汇
- **统计分析**: 查看学习进度和词汇积累
- **数据导出**: 导出词汇表用于其他学习工具

## ⚠️ 注意事项

### API使用
- 需要有效的 OpenAI API Key
- 每次提取会消耗一定的 API 额度
- 网络连接需要稳定

### 数据管理
- 提取结果会永久保存到数据库
- 重复提取同一系列会产生重复词汇
- 建议定期清理不需要的词汇

### 性能优化
- 大量字幕的提取可能需要较长时间
- 系统会显示实时进度
- 请耐心等待处理完成

## 🚧 未来扩展

### 计划功能
- [ ] 词汇难度分级
- [ ] 个性化学习计划
- [ ] 词汇复习提醒
- [ ] 学习进度跟踪
- [ ] 词汇游戏和测试

---

**🎓 AI关键词提取让英语学习更加智能和高效！** 