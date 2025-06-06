# COCA词频功能实现说明

## 概述

基于用户提供的真实COCA数据库，成功集成了美国当代英语语料库(COCA)的词频查询功能。该功能可以为关键词提供权威的使用频率排名和等级分类。

## 功能特点

### 🎯 核心功能
- **真实数据源**: 基于完整的COCA数据库，包含60,023个词汇
- **精确查询**: 支持词频排名查询，数字越小表示使用频率越高
- **智能匹配**: 支持词根变形、前后缀处理、短语频率估算
- **等级分类**: 将词频分为7个等级（极高频、高频、中高频、中频、中低频、低频、很低频）
- **详细信息**: 提供词汇在不同语料库（口语、小说、杂志、报纸、学术）中的频次统计

### 📊 数据库结构
```sql
-- t_coca表结构
CREATE TABLE t_coca (
    rank     INTEGER   PRIMARY KEY AUTOINCREMENT,
    pos        TEXT,     -- 词性
    word TEXT,           -- 词汇
    total    INTEGER,    -- 总频次
    spoken INTEGER,      -- 口语频次
    fiction INTEGER,     -- 小说频次
    magazine INTEGER,    -- 杂志频次
    newspaper INTEGER,   -- 报纸频次
    academic INTEGER,    -- 学术频次
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- t_keywords表新增字段
ALTER TABLE t_keywords ADD COLUMN coca INTEGER;
```

## 实现细节

### 🔧 技术架构

1. **COCA查询模块** (`src/coca_lookup.py`)
   - `COCADatabaseLookup` 类：核心查询引擎
   - 支持精确匹配、模糊匹配、词根匹配
   - 处理数据库中的空格问题（使用TRIM函数）
   - 提供批量查询和详细信息查询

2. **关键词提取器集成** (`src/keyword_extractor.py`)
   - 在AI提取关键词时自动查询COCA排名
   - 为每个关键词附加频率信息

3. **数据库管理界面** (`src/database_interface.py`)
   - 关键词列表显示COCA排名和频率等级
   - 手动添加关键词支持COCA字段（可选，自动查询）
   - 搜索和筛选功能包含COCA信息

4. **数据库迁移** (`src/database.py`)
   - 自动检测并添加coca字段到t_keywords表
   - 安全的数据库迁移机制

### 📈 频率等级分类

| 排名范围 | 等级 | 描述 |
|---------|------|------|
| 1-100 | 极高频 | 最常用的基础词汇 |
| 101-500 | 高频 | 日常交流必备词汇 |
| 501-1000 | 中高频 | 常见的实用词汇 |
| 1001-2000 | 中频 | 一般性词汇 |
| 2001-5000 | 中低频 | 较少使用的词汇 |
| 5001-10000 | 低频 | 专业或特定领域词汇 |
| 10000+ | 很低频 | 罕见或非常专业的词汇 |

### 🔍 查询示例

```python
from coca_lookup import coca_lookup

# 查询单词频率排名
rank = coca_lookup.get_frequency_rank("computer")  # 返回: 589

# 获取频率等级
level = coca_lookup.get_frequency_level(589)  # 返回: "中高频"

# 获取详细信息
details = coca_lookup.get_word_details("computer")
# 返回: {'rank': 589, 'pos': 'N', 'total': 71358, ...}

# 批量查询
words = ["computer", "technology", "data"]
results = coca_lookup.batch_lookup(words)
# 返回: {'computer': 589, 'technology': 585, 'data': 559}
```

## 使用方式

### 🖥️ 通过Web界面

1. **启动数据库管理界面**:
   ```bash
   conda activate englishcut
   python src/database_interface.py
   ```
   访问: http://localhost:7861

2. **查看关键词COCA信息**:
   - 在关键词列表中查看"COCA排名"和"频率等级"列
   - 搜索关键词时自动显示COCA信息

3. **手动添加关键词**:
   - COCA排名字段可选（留空自动查询）
   - 系统会自动从COCA数据库查询并填充排名

4. **🔄 批量更新COCA信息**:
   - 在"📚 关键词库"标签页
   - 输入系列ID，点击"🔄 更新COCA"按钮
   - 系统会自动更新该系列下所有缺少COCA信息的关键词
   - 实时显示更新进度和统计结果

### 🔄 自动提取

- **音频/视频处理时**: AI提取的关键词自动包含COCA信息
- **关键词分析**: 每个提取的词汇都会查询其COCA排名和等级

### 📊 数据分析

- **词汇难度分析**: 根据COCA排名判断学习材料的难度
- **学习优先级**: 优先学习高频词汇
- **语言水平评估**: 通过词汇频率分布评估语言水平

## 测试验证

运行测试脚本验证功能：
```bash
python test/test_coca_database.py
```

测试覆盖：
- ✅ COCA数据库连接和统计
- ✅ 词频查询功能
- ✅ 单词详细信息查询
- ✅ 数据库集成测试
- ✅ 关键词提取器集成

## 技术优势

1. **数据权威性**: 使用美国当代英语语料库(COCA)权威数据
2. **查询效率**: 优化的SQL查询，支持大规模词汇库
3. **智能容错**: 处理词形变化、大小写、空格等问题
4. **无缝集成**: 与现有系统完美融合，用户体验一致
5. **扩展性**: 模块化设计，易于扩展和维护

## 注意事项

- COCA数据库需要预先加载到t_coca表
- 词汇查询时会自动处理空格和大小写问题
- 未找到的词汇会尝试词根匹配和短语估算
- 频率等级是根据COCA排名动态计算的

---

**更新时间**: 2025-06-06
**版本**: 1.0
**状态**: ✅ 已完成并测试通过 