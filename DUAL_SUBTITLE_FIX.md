# 双语字幕烧制功能修复

## 问题描述

用户反馈在使用"烧制关键词+字幕视频"功能时，只能看到中文字幕，英文字幕没有显示出来。

## 问题分析

通过代码审查发现，问题出现在 `_build_video_filter` 函数的字幕渲染逻辑中：

```python
# 原有问题代码（第271-275行）
if any('\u4e00' <= char <= '\u9fff' for char in line):
    font_size = int(width * 0.05) # 中文字体稍小
    
    filter_chain.append(
    f"drawtext=text='{escaped_line}':fontcolor=#111111:fontsize={font_size}:x=(w-text_w)/2:y={y_pos}:fontfile='{douyin_font}'"
    )
```

**核心问题**: 只有当检测到中文字符时，才会添加 `drawtext` 滤镜指令。这导致纯英文行被跳过，不会渲染到视频中。

## 修复方案

### 1. 修复字幕渲染逻辑

将条件判断从"只处理中文"改为"处理所有行，但区分中英文样式"：

```python
# 修复后的代码
for i, line in enumerate(lines):
    if not line.strip():  # 跳过空行
        continue
        
    escaped_line = escape_text(line)
    y_pos = start_y + i * line_height
    
    # 区分中英文，使用不同字体大小和颜色
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in line)
    if is_chinese:
        font_size = int(width * 0.048) # 中文字体
        font_color = "#444444"  # 中文使用深灰色
        shadow_color = "white@0.9"
    else:
        font_size = int(width * 0.058) # 英文字体稍大
        font_color = "#111111"  # 英文使用更深的黑色
        shadow_color = "white@0.8"
    
    # 为所有行（不管是中文还是英文）添加字幕
    filter_chain.append(
        f"drawtext=text='{escaped_line}':fontcolor={font_color}:fontsize={font_size}:x=(w-text_w)/2:y={y_pos}:fontfile='{douyin_font}':shadowcolor={shadow_color}:shadowx=1:shadowy=1"
    )
```

### 2. 优化双语字幕显示效果

- **字体大小区分**: 英文字体稍大(0.058)，中文字体稍小(0.048)
- **颜色区分**: 英文使用深黑色(#111111)，中文使用深灰色(#444444)
- **阴影效果**: 为不同语言设置不同的阴影透明度
- **行高优化**: 双语时使用稍大的行高(0.075)，单语时使用标准行高(0.08)

### 3. 添加调试日志

在视频烧制过程中添加调试信息，便于排查问题：

```python
# 调试日志：检查双语字幕构建
if i < 3:  # 只记录前3个片段的日志
    LOG.info(f"片段 {i} 双语字幕构建:")
    LOG.info(f"  - 英文: '{item['english_text']}'")
    LOG.info(f"  - 中文: '{item['chinese_text']}'")
    LOG.info(f"  - 合并后: '{bottom_text}'")
    line_count = len(bottom_text.split('\n')) if bottom_text else 0
    LOG.info(f"  - 行数: {line_count}")
```

### 4. 更新预览功能

修改 `get_burn_preview` 函数，提供更详细的双语字幕预览信息：

```python
# 构建双语示例文本
english_text = item.get('english_text', '')
chinese_text = item.get('chinese_text', '')
subtitle_example = ""
if english_text:
    subtitle_example = english_text
if chinese_text:
    if subtitle_example:
        subtitle_example += " | "
    subtitle_example += chinese_text

sample_keywords.append({
    'keyword': item['keyword'],
    'phonetic': item.get('phonetic', ''),
    'explanation': item.get('explanation', ''),
    'coca_rank': coca,
    'subtitle_example': subtitle_example,
    'time_range': f"{item['begin_time']:.1f}s - {item['end_time']:.1f}s"
})
```

## 测试验证

### 测试结果

运行测试脚本 `demo_dual_subtitle.py` 的结果：

```
📊 过滤器统计:
- 总drawtext指令数: 6
- 字幕drawtext数: 2
- 关键词drawtext数: 2

✅ 双语字幕修复效果:
- 英文字幕: ✓
- 中文字幕: ✓
- 关键词显示: ✓

🎉 双语字幕功能已成功修复！英文和中文都会正确显示。
```

### 验证内容

1. **字幕构建**: 英文和中文正确合并为双行文本
2. **Filter生成**: 为每行文本都生成对应的drawtext指令
3. **样式区分**: 英文和中文使用不同的字体大小和颜色
4. **渲染效果**: 所有字幕行都会被正确渲染到视频中

## 影响范围

此修复影响以下功能：

1. **烧制关键词+字幕视频** (主要修复目标)
2. **烧制关键词视频** (无影响，不涉及字幕)
3. **烧制无字幕视频** (无影响，不涉及字幕)

## 数据库结构确认

根据提供的数据库结构，字幕数据正确存储在 `t_subtitle` 表中：

```sql
CREATE TABLE t_subtitle (
    id           INTEGER   PRIMARY KEY AUTOINCREMENT,
    series_id    INTEGER   NOT NULL,
    begin_time   REAL      NOT NULL,
    end_time     REAL      NOT NULL,
    english_text TEXT,      -- 英文字幕
    chinese_text TEXT,      -- 中文字幕
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (series_id) REFERENCES t_series (id) ON DELETE CASCADE
);
```

修复后的代码能够正确读取和处理这两个字段。

## 使用说明

修复完成后，用户在使用"烧制关键词+字幕视频"功能时：

1. 英文字幕会显示在上一行，使用稍大的黑色字体
2. 中文字幕会显示在下一行，使用稍小的深灰色字体
3. 两行字幕都会有白色阴影，增强可读性
4. 关键词会显示在视频中央的半透明背景框内

修复确保了双语学习体验的完整性。 