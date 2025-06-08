#!/usr/bin/env python3
"""
测试MediaProcessor的_save_to_database方法
特别关注字幕的timestamp处理
"""

import os
import sys
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 添加项目根目录到sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

# 首先Mock掉导入路径问题
sys.modules['src.openai_whisper'] = MagicMock()
sys.modules['src.video_processor'] = MagicMock()
sys.modules['src.file_detector'] = MagicMock()
sys.modules['src.logger'] = MagicMock()

# 定义FileType模拟类
class MockFileType:
    AUDIO = 'audio'
    VIDEO = 'video'

# 应用Mock
sys.modules['src.file_detector'].FileType = MockFileType

# 导入测试模块
from src.database import db_manager

# 创建一个独立的MediaProcessor类，只包含_save_to_database方法
class MediaProcessorForTest:
    """用于测试的简化版MediaProcessor类"""
    
    def __init__(self):
        """初始化"""
        self.temp_files = []
    
    def _save_to_database(self, file_info, recognition_result, subtitle_result, is_bilingual, processed_video_path=None, existing_series_id=None):
        """
        保存处理结果到数据库
        
        参数:
        - file_info: 文件信息
        - recognition_result: 识别结果  
        - subtitle_result: 字幕生成结果
        - is_bilingual: 是否双语
        - processed_video_path: 预处理后的视频路径
        - existing_series_id: 现有的系列ID (如果有)
        """
        try:
            print(f"开始保存到数据库: 文件={file_info.get('name', 'Unknown')}, 双语={is_bilingual}")
            
            # 如果提供了现有的系列ID，则直接使用
            if existing_series_id:
                series_id = existing_series_id
                print(f"使用现有系列ID: {series_id}")
            else:
                # 准备文件路径信息
                original_path = file_info.get('original_path', file_info['path'])
                
                # 1. 创建媒体系列记录
                series_id = db_manager.create_series(
                    name=file_info['name'],
                    file_path=original_path,  # 保存原始文件路径
                    file_type=file_info['type'],
                    duration=recognition_result.get('audio_duration')
                )
                print(f"创建媒体系列成功: ID={series_id}")
                
                # 如果有预处理的9:16视频，更新系列信息
                if processed_video_path:
                    db_manager.update_series_video_info(
                        series_id,
                        new_name=os.path.basename(processed_video_path),
                        new_file_path=processed_video_path
                    )
                    print(f"更新系列的9:16预处理视频信息: {processed_video_path}")
            
            # 2. 准备字幕数据
            subtitles_data = []
            chunks = recognition_result.get('chunks', [])
            print(f"处理字幕数据: {len(chunks)} 个chunks")
            
            if is_bilingual:
                # 双语模式
                english_chunks = recognition_result.get('english_chunks', [])
                chinese_chunks = recognition_result.get('chinese_chunks', [])
                print(f"双语模式: 英文chunks={len(english_chunks)}, 中文chunks={len(chinese_chunks)}")
                
                # 检查chunks、english_chunks和chinese_chunks的长度
                # 理论上应该一致，但实际可能有差异
                chunks_len = len(chunks)
                english_len = len(english_chunks)
                chinese_len = len(chinese_chunks)
                
                # 使用最短的长度作为循环次数，避免索引越界
                min_length = min(chunks_len, english_len, chinese_len)
                print(f"使用最短长度进行处理: chunks={chunks_len}, english={english_len}, chinese={chinese_len}, min={min_length}")
                
                # 检查和修复chunks中的时间戳
                total_duration = recognition_result.get('audio_duration', 0)
                
                for i in range(min_length):
                    chunk = chunks[i] if i < chunks_len else {'timestamp': [0, 0], 'text': ''}
                    timestamp = chunk.get('timestamp', [0, 0])
                    # 确保timestamp是一个至少有两个元素的列表
                    if not isinstance(timestamp, list) or len(timestamp) < 2:
                        timestamp = [0, 0]
                    
                    # 确保结束时间不为NULL且有效
                    if timestamp[1] is None or timestamp[1] <= timestamp[0]:
                        # 如果这是最后一个chunk，使用总时长作为结束时间
                        if i == min_length - 1 and total_duration > 0:
                            timestamp[1] = total_duration
                        # 否则，使用开始时间加上10秒或下一个开始时间作为结束时间
                        else:
                            next_start = chunks[i+1].get('timestamp', [0, 0])[0] if i+1 < chunks_len else 0
                            if next_start and next_start > timestamp[0]:
                                timestamp[1] = next_start
                            else:
                                timestamp[1] = timestamp[0] + 10
                    
                    # 获取对应的文本
                    english_text = english_chunks[i].get('text', '') if i < english_len else ''
                    chinese_text = chinese_chunks[i].get('text', '') if i < chinese_len else ''
                    
                    # 最后再次确保timestamp有效
                    begin_time = max(0, timestamp[0])
                    end_time = max(begin_time + 1, timestamp[1])  # 确保end_time大于begin_time
                    
                    print(f"处理双语字幕 Chunk {i}: timestamp=[{begin_time}, {end_time}], text={english_text[:20]}...")
                    
                    subtitles_data.append({
                        'begin_time': begin_time,
                        'end_time': end_time,
                        'english_text': english_text,
                        'chinese_text': chinese_text
                    })
            else:
                # 单语模式
                print("单语模式处理")
                
                # 检查和修复chunks中的时间戳
                valid_chunks = []
                total_duration = recognition_result.get('audio_duration', 0)
                
                for i, chunk in enumerate(chunks):
                    timestamp = chunk.get('timestamp', [0, 0])
                    # 确保timestamp是一个至少有两个元素的列表
                    if not isinstance(timestamp, list) or len(timestamp) < 2:
                        timestamp = [0, 0]
                    
                    # 确保结束时间不为NULL且有效
                    if timestamp[1] is None or timestamp[1] <= timestamp[0]:
                        # 如果这是最后一个chunk，使用总时长作为结束时间
                        if i == len(chunks) - 1 and total_duration > 0:
                            timestamp[1] = total_duration
                        # 否则，使用开始时间加上10秒作为结束时间
                        else:
                            next_start = chunks[i+1].get('timestamp', [0, 0])[0] if i+1 < len(chunks) else 0
                            if next_start and next_start > timestamp[0]:
                                timestamp[1] = next_start
                            else:
                                timestamp[1] = timestamp[0] + 10
                    
                    valid_chunks.append({
                        'text': chunk.get('text', ''),
                        'timestamp': timestamp
                    })
                
                # 使用修复后的chunks
                for i, chunk in enumerate(valid_chunks):
                    text = chunk.get('text', '')
                    timestamp = chunk.get('timestamp', [0, 0])
                    
                    # 最后再次确保timestamp有效
                    begin_time = max(0, timestamp[0])
                    end_time = max(begin_time + 1, timestamp[1])  # 确保end_time大于begin_time
                    
                    print(f"处理单语字幕 Chunk {i}: timestamp=[{begin_time}, {end_time}], text={text[:20]}...")
                    
                    subtitles_data.append({
                        'begin_time': begin_time,
                        'end_time': end_time,
                        'english_text': text,
                        'chinese_text': ''
                    })
            
            # 3. 首先删除现有的所有字幕
            if series_id:
                print(f"删除系列ID={series_id}的现有字幕")
                db_manager.delete_subtitles_by_series_id(series_id)
            
            # 4. 批量创建字幕记录
            if subtitles_data:
                print(f"准备保存 {len(subtitles_data)} 条字幕到数据库")
                # 记录前几条字幕数据以便调试
                for i, subtitle in enumerate(subtitles_data[:3]):
                    print(f"字幕 {i+1}: begin_time={subtitle['begin_time']}, end_time={subtitle['end_time']}")
                
                subtitle_ids = db_manager.create_subtitles(series_id, subtitles_data)
                print(f"数据库保存成功: 系列ID {series_id}, {len(subtitle_ids)} 条字幕")
            else:
                print("没有字幕数据需要保存")
            
        except Exception as e:
            print(f"保存到数据库失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            # 不抛出异常，避免影响主流程

class TestSaveToDatabase(unittest.TestCase):
    """测试MediaProcessor中的_save_to_database方法"""
    
    def setUp(self):
        """测试前准备工作"""
        # 创建临时数据库文件
        self.temp_dir = tempfile.mkdtemp()
        self.temp_db_path = os.path.join(self.temp_dir, "test_db.sqlite")
        
        # 备份原始数据库路径
        self.original_db_path = db_manager.db_path
        
        # 设置测试用的数据库路径
        db_manager.db_path = self.temp_db_path
        
        # 初始化数据库
        db_manager._init_database()
        
        # 创建测试用的MediaProcessor实例
        self.processor = MediaProcessorForTest()
    
    def tearDown(self):
        """测试后清理工作"""
        # 恢复原始数据库路径
        db_manager.db_path = self.original_db_path
        
        # 清理临时目录
        shutil.rmtree(self.temp_dir)
    
    def test_save_to_database_with_timestamps(self):
        """测试保存带有正确时间戳的字幕数据"""
        # 准备测试数据 - 文件信息
        file_info = {
            'name': 'test_video.mp4',
            'path': '/path/to/test_video.mp4',
            'type': 'video',
            'original_path': '/path/to/original_test_video.mp4'
        }
        
        # 准备测试数据 - 识别结果（模拟Whisper返回的结果）
        recognition_result = {
            'english_text': 'This is a test video with timestamps.',
            'chinese_text': '这是一个带时间戳的测试视频。',
            'is_bilingual': True,
            'audio_duration': 10.0,
            'chunks': [
                {
                    'text': 'This is a test',
                    'timestamp': [0.5, 3.0]  # 有效的时间戳
                },
                {
                    'text': 'video with timestamps.',
                    'timestamp': [3.2, 6.5]  # 有效的时间戳
                }
            ],
            'english_chunks': [
                {
                    'text': 'This is a test',
                    'timestamp': [0.5, 3.0]
                },
                {
                    'text': 'video with timestamps.',
                    'timestamp': [3.2, 6.5]
                }
            ],
            'chinese_chunks': [
                {
                    'text': '这是一个测试',
                    'timestamp': [0.5, 3.0]
                },
                {
                    'text': '带时间戳的视频。',
                    'timestamp': [3.2, 6.5]
                }
            ]
        }
        
        # 准备测试数据 - 字幕结果
        subtitle_result = {
            'success': True,
            'file_type': 'video',
            'subtitle_format': 'SRT',
            'subtitle_file': '/path/to/output/test_video.srt',
            'subtitle_content': '1\n00:00:00,500 --> 00:00:03,000\nThis is a test\n这是一个测试\n\n2\n00:00:03,200 --> 00:00:06,500\nvideo with timestamps.\n带时间戳的视频。',
            'is_bilingual': True
        }
        
        # 调用被测试的方法
        self.processor._save_to_database(
            file_info=file_info,
            recognition_result=recognition_result,
            subtitle_result=subtitle_result,
            is_bilingual=True
        )
        
        # 验证数据库中的系列
        series_list = db_manager.get_series()
        self.assertEqual(len(series_list), 1, "应该创建了一个系列")
        
        # 获取创建的系列ID
        series_id = series_list[0]['id']
        
        # 验证字幕
        subtitles = db_manager.get_subtitles(series_id)
        self.assertEqual(len(subtitles), 2, "应该创建了两条字幕")
        
        # 验证时间戳
        self.assertAlmostEqual(subtitles[0]['begin_time'], 0.5, places=1, 
                              msg="第一条字幕的开始时间应该是0.5")
        self.assertAlmostEqual(subtitles[0]['end_time'], 3.0, places=1,
                              msg="第一条字幕的结束时间应该是3.0")
        self.assertAlmostEqual(subtitles[1]['begin_time'], 3.2, places=1,
                              msg="第二条字幕的开始时间应该是3.2")
        self.assertAlmostEqual(subtitles[1]['end_time'], 6.5, places=1,
                              msg="第二条字幕的结束时间应该是6.5")
        
        # 验证文本内容
        self.assertEqual(subtitles[0]['english_text'], 'This is a test')
        self.assertEqual(subtitles[0]['chinese_text'], '这是一个测试')
        self.assertEqual(subtitles[1]['english_text'], 'video with timestamps.')
        self.assertEqual(subtitles[1]['chinese_text'], '带时间戳的视频。')
    
    def test_save_to_database_with_invalid_timestamps(self):
        """测试保存带有无效时间戳的字幕数据"""
        # 准备测试数据 - 文件信息
        file_info = {
            'name': 'test_video.mp4',
            'path': '/path/to/test_video.mp4',
            'type': 'video',
            'original_path': '/path/to/original_test_video.mp4'
        }
        
        # 准备测试数据 - 识别结果（带有无效时间戳）
        recognition_result = {
            'english_text': 'This is a test video with invalid timestamps.',
            'chinese_text': '这是一个带无效时间戳的测试视频。',
            'is_bilingual': True,
            'audio_duration': 10.0,
            'chunks': [
                {
                    'text': 'This is a test',
                    'timestamp': [0, 0]  # 无效的时间戳 - 开始和结束时间相同
                },
                {
                    'text': 'video with invalid timestamps.',
                    'timestamp': [3.0, None]  # 无效的时间戳 - 结束时间为None
                }
            ],
            'english_chunks': [
                {
                    'text': 'This is a test',
                    'timestamp': [0, 0]
                },
                {
                    'text': 'video with invalid timestamps.',
                    'timestamp': [3.0, None]
                }
            ],
            'chinese_chunks': [
                {
                    'text': '这是一个测试',
                    'timestamp': [0, 0]
                },
                {
                    'text': '带无效时间戳的视频。',
                    'timestamp': [3.0, None]
                }
            ]
        }
        
        # 准备测试数据 - 字幕结果
        subtitle_result = {
            'success': True,
            'file_type': 'video',
            'subtitle_format': 'SRT',
            'subtitle_file': '/path/to/output/test_video.srt',
            'subtitle_content': '字幕内容',
            'is_bilingual': True
        }
        
        # 调用被测试的方法
        self.processor._save_to_database(
            file_info=file_info,
            recognition_result=recognition_result,
            subtitle_result=subtitle_result,
            is_bilingual=True
        )
        
        # 验证数据库中的系列
        series_list = db_manager.get_series()
        self.assertEqual(len(series_list), 1, "应该创建了一个系列")
        
        # 获取创建的系列ID
        series_id = series_list[0]['id']
        
        # 验证字幕
        subtitles = db_manager.get_subtitles(series_id)
        self.assertEqual(len(subtitles), 2, "应该创建了两条字幕")
        
        # 验证时间戳修复
        # 第一条字幕：开始和结束时间相同，应该自动修复为合理值
        self.assertEqual(subtitles[0]['begin_time'], 0.0)
        self.assertGreater(subtitles[0]['end_time'], subtitles[0]['begin_time'], 
                          "结束时间应该大于开始时间")
        
        # 第二条字幕：结束时间为None，应该自动修复为合理值
        self.assertEqual(subtitles[1]['begin_time'], 3.0)
        self.assertGreater(subtitles[1]['end_time'], subtitles[1]['begin_time'],
                          "结束时间应该大于开始时间")
    
    def test_save_to_database_single_language(self):
        """测试保存单语言字幕数据"""
        # 准备测试数据 - 文件信息
        file_info = {
            'name': 'test_audio.mp3',
            'path': '/path/to/test_audio.mp3',
            'type': 'audio'
        }
        
        # 准备测试数据 - 识别结果（单语言）
        recognition_result = {
            'text': 'This is a single language test.',
            'audio_duration': 5.0,
            'chunks': [
                {
                    'text': 'This is a',
                    'timestamp': [0.2, 1.5]
                },
                {
                    'text': 'single language test.',
                    'timestamp': [1.7, 4.5]
                }
            ]
        }
        
        # 准备测试数据 - 字幕结果
        subtitle_result = {
            'success': True,
            'file_type': 'audio',
            'subtitle_format': 'SRT',
            'subtitle_file': '/path/to/output/test_audio.srt',
            'subtitle_content': '字幕内容',
            'is_bilingual': False
        }
        
        # 调用被测试的方法
        self.processor._save_to_database(
            file_info=file_info,
            recognition_result=recognition_result,
            subtitle_result=subtitle_result,
            is_bilingual=False
        )
        
        # 验证数据库中的系列
        series_list = db_manager.get_series()
        self.assertEqual(len(series_list), 1, "应该创建了一个系列")
        
        # 获取创建的系列ID
        series_id = series_list[0]['id']
        
        # 验证字幕
        subtitles = db_manager.get_subtitles(series_id)
        self.assertEqual(len(subtitles), 2, "应该创建了两条字幕")
        
        # 验证时间戳
        self.assertAlmostEqual(subtitles[0]['begin_time'], 0.2, places=1)
        self.assertAlmostEqual(subtitles[0]['end_time'], 1.5, places=1)
        self.assertAlmostEqual(subtitles[1]['begin_time'], 1.7, places=1)
        self.assertAlmostEqual(subtitles[1]['end_time'], 4.5, places=1)
        
        # 验证文本内容（单语言模式下只有英文）
        self.assertEqual(subtitles[0]['english_text'], 'This is a')
        self.assertEqual(subtitles[0]['chinese_text'], '')
        self.assertEqual(subtitles[1]['english_text'], 'single language test.')
        self.assertEqual(subtitles[1]['chinese_text'], '')
    
    def test_save_to_database_existing_series(self):
        """测试保存到现有系列"""
        # 创建一个现有系列
        existing_series_id = db_manager.create_series(
            name="existing_series",
            file_path="/path/to/existing.mp4",
            file_type="video"
        )
        
        # 准备测试数据
        file_info = {
            'name': 'existing_series.mp4',
            'path': '/path/to/existing.mp4',
            'type': 'video'
        }
        
        recognition_result = {
            'english_text': 'Test existing series',
            'chunks': [
                {
                    'text': 'Test existing series',
                    'timestamp': [1.0, 4.0]
                }
            ]
        }
        
        subtitle_result = {
            'success': True,
            'subtitle_format': 'SRT',
            'is_bilingual': False
        }
        
        # 调用被测试的方法，传入现有系列ID
        self.processor._save_to_database(
            file_info=file_info,
            recognition_result=recognition_result,
            subtitle_result=subtitle_result,
            is_bilingual=False,
            existing_series_id=existing_series_id
        )
        
        # 验证字幕是否添加到现有系列
        subtitles = db_manager.get_subtitles(existing_series_id)
        self.assertEqual(len(subtitles), 1, "应该添加了一条字幕到现有系列")
        self.assertEqual(subtitles[0]['english_text'], 'Test existing series')

if __name__ == '__main__':
    unittest.main() 