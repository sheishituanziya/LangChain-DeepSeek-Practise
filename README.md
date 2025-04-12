# LangChain-DeepSeek 应用实践

## 项目介绍

本项目是基于LangChain框架和DeepSeek API的一系列实践示例，旨在展示如何利用LangChain和大语言模型构建实用的AI应用。项目受到吴恩达的《LangChain for LLM Application Development》课程的启发，结合了DeepSeek最新开放的API，实现了一系列从基础到高级的应用示例。

## 内容概览

本项目包含以下几个核心部分：

1. **API调用基础** - `1_api_call.ipynb`
   - 基础API调用方法
   - 环境配置和密钥管理 

2. **提示词工程** - `2_prompt_engineering.ipynb`
   - 提示词模板设计
   - 参数化动态提示词
   - 结构化输出技巧

3. **链式调用技术** - `3_chain_call.ipynb`
   - 基础链构建
   - 顺序链处理
   - 组合链应用

4. **对话记忆系统** - `4_memory_chat.ipynb`
   - 内存对话记忆
   - 持久化存储方案
   - 多会话管理

5. **工具调用集成** - `5_tool_invoke.ipynb`
   - 时间工具
   - 计算器工具
   - 网络搜索工具

6. **RAG系统实现** - `6_rag_demo.ipynb`
   - 文档加载和处理
   - 向量存储和检索
   - 全流程RAG系统构建

## 使用说明

### 环境配置

1. 克隆本仓库
```bash
git clone https://github.com/yourusername/langchain-deepseek.git
cd langchain-deepseek
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
创建`.env`文件，添加以下内容：
```
DEEPSEEK_API_KEY = 你的DeepSeek API密钥
DEEPSEEK_API_BASE = https://api.deepseek.com/v1
```

### 运行示例

打开任意Jupyter笔记本，按顺序运行单元格即可。建议按照编号顺序学习，由浅入深。

## 项目背景

随着DeepSeek最近开放API调用，我想尝试结合LangChain框架探索更多大语言模型应用的可能性。这个项目是我学习和实践的记录，希望能为同样对LLM应用开发感兴趣的朋友提供一些参考。

项目中的示例深受吴恩达《LangChain for LLM Application Development》课程的启发，在此基础上进行了扩展和改进，特别针对中文场景和DeepSeek模型进行了优化。

## 贡献与交流

欢迎对LLM应用开发感兴趣的朋友一起交流学习！如果你有任何建议、问题或想法，请随时提出issue或PR。如果发现内容中有不准确的地方，也希望能够指正，让我们一起进步。