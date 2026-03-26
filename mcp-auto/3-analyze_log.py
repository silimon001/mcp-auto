import re
import csv
import json
from pathlib import Path
from typing import List, Dict, Optional, Union
from glob import glob

from dataset_setting import dataset_name
log_dir = "log_file"

class MCPLogAnalyzer:
    def __init__(self):
        self.servers_data = []
        self.parsed_files = []  # 记录已解析的文件
        
    def extract_server_name(self, line: str) -> Optional[str]:
        """从日志行中提取服务器名称，保留前面的数字"""
        # 匹配格式: /951246115_mcp-server-calculator_README.md
        pattern = r'/(\d+_[^/]+?)_README\.md'
        match = re.search(pattern, line)
        if match:
            return match.group(1)
        return None
    
    def extract_token_data(self, line: str) -> Optional[Dict]:
        """从Token Usage行中提取token数据"""
        if 'Token Usage:' in line:
            # 找到JSON字符串开始的位置
            json_start = line.find('{')
            json_end = line.rfind('}')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_str = line[json_start:json_end + 1]
                try:
                    token_data = json.loads(json_str)
                    return {
                        'completion_tokens': token_data.get('completion_tokens', 0),
                        'prompt_tokens': token_data.get('prompt_tokens', 0)
                    }
                except json.JSONDecodeError:
                    print(f"JSON解析错误: {json_str}")
                    return None
        return None
    
    def extract_tool_name(self, line: str) -> Optional[str]:
        """从工具调用行中提取工具名称"""
        if '[准备调用工具]' in line:
            # 匹配格式: [准备调用工具] Server: MCP-Auto, Tool: need_use_these_tools, Args: ...
            match = re.search(r'Tool:\s*([^,]+)', line)
            if match:
                return match.group(1).strip()
        return None
    
    def parse_log_file(self, log_file_path: Union[str, Path]) -> List[Dict]:
        """解析单个日志文件，提取每个MCP服务器的数据"""
        log_file_path = Path(log_file_path)
        
        print(f"正在解析日志文件: {log_file_path}")
        
        with open(log_file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        servers = []
        current_server = None
        current_round = 0
        in_server_section = False
        max_rounds = 15  # 最大轮次限制
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 检测新的MCP服务器开始
            if 'dealing with' in line and 'README.md' in line:
                if current_server:
                    # 如果服务器有数据但没有标志，且轮次达到15，标记为失败
                    if current_server['flag'] is None and len(current_server['rounds']) >= max_rounds:
                        current_server['flag'] = '❌ @@Task Failed@@'
                    elif current_server['flag'] is None and len(current_server['rounds']) > 0:
                        current_server['flag'] = '❌ @@Task Failed@@'
                    
                    servers.append(current_server)
                
                # 提取服务器名称
                server_name = self.extract_server_name(line)
                if not server_name:
                    # 尝试从路径中提取
                    parts = line.split('/')
                    for part in parts:
                        if '_README.md' in part:
                            server_name = part.replace('_README.md', '')
                            break
                
                if server_name:
                    current_server = {
                        'server_name': server_name,
                        'flag': None,
                        'rounds': [],
                        'source_file': log_file_path.name  # 记录来源文件
                    }
                    current_round = 0
                    in_server_section = True
                continue
            
            # 如果不在服务器处理中，跳过
            if not in_server_section:
                continue
            
            # 检测对话轮次
            communicate_match = re.search(r'--- Communicate Count: (\d+) ---', line)
            if communicate_match and current_server:
                current_round = int(communicate_match.group(1))
                # 确保不超过最大轮次
                if current_round <= max_rounds:
                    # 确保rounds列表足够长
                    while len(current_server['rounds']) < current_round:
                        current_server['rounds'].append({
                            'tool': None,
                            'completion_tokens': 0,
                            'prompt_tokens': 0
                        })
                continue
            
            # 检测Token Usage
            token_data = self.extract_token_data(line)
            if token_data and current_server and current_round > 0 and current_round <= max_rounds:
                if current_round <= len(current_server['rounds']):
                    current_server['rounds'][current_round - 1]['completion_tokens'] = token_data['completion_tokens']
                    current_server['rounds'][current_round - 1]['prompt_tokens'] = token_data['prompt_tokens']
                continue
            
            # 检测工具调用
            tool_name = self.extract_tool_name(line)
            if tool_name and current_server and current_round > 0 and current_round <= max_rounds:
                if current_round <= len(current_server['rounds']):
                    current_server['rounds'][current_round - 1]['tool'] = tool_name
                continue
            
            # 检测任务标志
            if any(marker in line for marker in ['✅ @@Task Done@@', '❌ @@Task Failed@@', '⚠️ @@Task Alert@@']):
                if current_server:
                    for marker in ['✅ @@Task Done@@', '❌ @@Task Failed@@', '⚠️ @@Task Alert@@']:
                        if marker in line:
                            current_server['flag'] = marker
                            break
                continue
        
        # 添加最后一个服务器
        if current_server:
            # 如果服务器有数据但没有标志，且轮次达到15，标记为失败
            if current_server['flag'] is None and len(current_server['rounds']) >= max_rounds:
                current_server['flag'] = '❌ @@Task Failed@@'
            elif current_server['flag'] is None and len(current_server['rounds']) > 0:
                current_server['flag'] = '❌ @@Task Failed@@'
            
            servers.append(current_server)
        
        # 将当前文件解析的结果添加到总数据中
        self.servers_data.extend(servers)
        self.parsed_files.append(log_file_path)
        
        print(f"  完成解析，找到 {len(servers)} 个MCP服务器")
        return servers
    
    def parse_log_directory(self, log_files: list[str]) -> List[Dict]:
        """解析目录下的所有日志文件"""

        print(f"找到 {len(log_files)} 个日志文件")
        
        all_servers = []
        for log_file in sorted(log_files):
            try:
                servers = self.parse_log_file(log_file)
                all_servers.extend(servers)
            except Exception as e:
                print(f"解析文件 {log_file} 时出错: {e}")
        
        return all_servers
    
    def generate_csv(self, output_path: str = 'mcp_log_analysis.csv'):
        """生成CSV文件，包含所有解析的数据"""
        if not self.servers_data:
            print("没有找到任何MCP服务器数据")
            return None
        
        # 准备CSV头部 - 固定15轮
        max_rounds = 15
        headers = ['MCP server', 'flag', 'source_file']  # 添加来源文件列
        for i in range(1, max_rounds + 1):
            headers.extend([
                f'round{i}_tool',
                f'round{i}_Output_Token',
                f'round{i}_Input_Token'
            ])
        
        # 写入CSV文件
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for server in self.servers_data:
                row = [
                    server['server_name'], 
                    server['flag'] or '❌ @@Task Failed@@',
                    server.get('source_file', 'unknown')
                ]
                
                for i in range(max_rounds):
                    if i < len(server['rounds']):
                        round_data = server['rounds'][i]
                        row.extend([
                            round_data['tool'] or '',
                            round_data['completion_tokens'],
                            round_data['prompt_tokens']
                        ])
                    else:
                        row.extend(['', 0, 0])
                
                writer.writerow(row)
        
        print(f"\nCSV文件已生成: {output_path}")
        print(f"共处理了 {len(self.parsed_files)} 个日志文件")
        print(f"总MCP服务器数: {len(self.servers_data)}")
        return output_path
    
    def print_summary(self):
        """打印分析摘要"""
        if not self.servers_data:
            print("没有找到任何MCP服务器数据")
            return
        
        print("=" * 80)
        print("MCP日志分析摘要")
        print(f"解析的文件数: {len(self.parsed_files)}")
        print("=" * 80)
        
        success_count = 0
        fail_count = 0
        alert_count = 0
        
        # 按来源文件分组统计
        file_stats = {}
        
        for i, server in enumerate(self.servers_data, 1):
            flag = server['flag'] or '❌ @@Task Failed@@'
            source_file = server.get('source_file', 'unknown')
            
            # 更新文件统计
            if source_file not in file_stats:
                file_stats[source_file] = {
                    'total': 0, 
                    'success': 0, 
                    'fail': 0, 
                    'alert': 0
                }
            
            file_stats[source_file]['total'] += 1
            if '✅' in flag:
                success_count += 1
                file_stats[source_file]['success'] += 1
            elif '❌' in flag:
                fail_count += 1
                file_stats[source_file]['fail'] += 1
            elif '⚠️' in flag:
                alert_count += 1
                file_stats[source_file]['alert'] += 1
        
        # 按文件打印统计
        print("\n按文件统计:")
        print("-" * 80)
        for file_name, stats in file_stats.items():
            print(f"{file_name}:")
            print(f"  总服务器数: {stats['total']}")
            print(f"  成功: {stats['success']} | 失败: {stats['fail']} | 警告: {stats['alert']}")
        
        # 总体统计
        print("\n" + "=" * 80)
        print("总体统计")
        print("=" * 80)
        
        total_servers = len(self.servers_data)
        total_rounds = sum(len(s['rounds']) for s in self.servers_data)
        total_completion = sum(sum(r['completion_tokens'] for r in s['rounds']) for s in self.servers_data)
        total_prompt = sum(sum(r['prompt_tokens'] for r in s['rounds']) for s in self.servers_data)
        
        print(f"解析的文件总数: {len(self.parsed_files)}")
        print(f"MCP服务器总数: {total_servers}")
        print(f"  成功: {success_count} ({success_count/total_servers*100:.1f}%)")
        print(f"  失败: {fail_count} ({fail_count/total_servers*100:.1f}%)")
        print(f"  警告: {alert_count} ({alert_count/total_servers*100:.1f}%)")
        print(f"总对话轮次: {total_rounds}")
        print(f"总Output Tokens: {total_completion}")
        print(f"总Input Tokens: {total_prompt}")
        print(f"总Tokens: {total_completion + total_prompt}")
        
        # 计算平均数据
        if total_servers > 0:
            print(f"\n平均每个服务器:")
            print(f"  对话轮次: {total_rounds/total_servers:.1f}")
            print(f"  Output Tokens: {total_completion/total_servers:.1f}")
            print(f"  Input Tokens: {total_prompt/total_servers:.1f}")


def analyze_single_mcp_log(log_file_path: str, dataset: str) -> Optional[str]:
    """
    分析单个MCP日志文件
    
    Args:
        log_file_path: 日志文件路径
    
    Returns:
        CSV文件路径
    """
    analyzer = MCPLogAnalyzer()
    
    # 解析日志
    print("正在解析日志文件...")
    try:
        servers = analyzer.parse_log_file(log_file_path)
    except Exception as e:
        print(f"解析日志文件时出错: {e}")
        return None
    
    if not servers:
        print("未找到MCP服务器数据")
        return None
    
    # 打印摘要
    analyzer.print_summary()
    
    # 生成CSV
    output_name = f"{log_dir}/mcp_analysis_{dataset}.csv"
    csv_path = analyzer.generate_csv(output_name)
    
    return csv_path


def analyze_all_mcp_logs(log_dir: list[str], dataset: str) -> Optional[str]:

    analyzer = MCPLogAnalyzer()
    
    # 解析日志
    print("正在解析日志文件...")
    
    # 解析目录下的所有日志文件
    try:
        servers = analyzer.parse_log_directory(log_dir)
    except Exception as e:
        print(f"解析目录时出错: {e}")
        return None
    
    if not servers:
        print("未找到任何MCP服务器数据")
        return None
    
    # 打印总体摘要
    analyzer.print_summary()
    
    # 生成CSV
    output_name = f"log_file/mcp_analysis_{dataset}.csv"
    csv_path = analyzer.generate_csv(output_name)
    
    return csv_path

if __name__ == "__main__":
    # 指定你的日志文件路径



    import os
    log_file = sorted(
        glob(os.path.join(log_dir, f"AMSD_py_*.log")),
        # reverse=True
    )

    if log_file:
        if len(log_file) == 1:
            csv_file = analyze_single_mcp_log(log_file[0], dataset_name)
            if csv_file:
                print(f"\n分析完成！结果已保存到: {csv_file}")
        elif len(log_file) > 1:
            csv_file = analyze_all_mcp_logs(log_file, dataset_name)
            if csv_file:
                print(f"\n分析完成！合并结果已保存到: {csv_file}")
    else:
        print(f"无效的路径: {log_dir}")
        print("请提供有效的日志文件(.log)或目录路径")