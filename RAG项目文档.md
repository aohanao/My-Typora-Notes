# 面向 CAE 仿真领域的智能问答系统 (RAG)

## 📌 项目背景与简介

本项目是一个专注于计算机辅助工程 (CAE) 领域的检索增强生成 (RAG) 系统。针对传统工程仿真领域文献中存在大量复杂公式、专业术语密集、知识检索困难等痛点，构建了一套完整的智能客服与知识库助手。系统支持带会话记忆的多轮对话，并实现了高精度的混合检索与深度语义重排。

## 🏗️ 项目核心架构

整个系统分为“离线数据入库”与“在线检索问答”两条主链路：

1. **知识库构建 (Offline Pipeline)**：支持 PDF/Markdown 格式的工程文献上传。针对 CAE 文献包含大量数学公式的特点，引入 Marker 进行深度解析；配合 MD5 校验防重、Markdown 结构化分块，最终存入 Chroma 向量数据库。
2. **混合检索问答 (Online Pipeline)**：采用 `向量检索 (Chroma)` + `稀疏检索 (BM25)` 的双路召回策略，通过 RRF (倒数排名融合) 算法合并结果，最后使用 `BGE-Reranker` 交叉编码器进行深度语义重排。大模型基于 LangChain LCEL 链介入，结合本地持久化的历史会话提供流式解答。

## 🛠️ 技术栈选型

- **前端交互**：Streamlit (聊天界面 `app.py`、文档管理 `file_uploader.py`)
- **大模型框架**：LangChain (LCEL 编排、历史记录管理、文档处理)
- **语言模型 & 向量模型**：阿里云百炼 DashScope (`qwen-turbo`、`text-embedding-v4`)
- **文档解析**：Marker CLI (专门解决 PDF 复杂数学公式与多栏排版解析难题)
- **检索与重排**：ChromaDB (向量库), Jieba + BM25Okapi (关键词检索), Sentence-Transformers (`BAAI/bge-reranker-base`)
- **工程化部署**：Docker, Docker Compose

## 📂 项目目录结构

Plaintext

```
CAE_RAG_project/
├── chat_history/         # 会话持久化：存储用户多轮对话历史的 JSON 文件
├── data/
│   ├── chroma_db/        # 向量库持久化：Chroma 本地数据库文件
│   └── md5.text          # 防重校验：记录已入库文档的 MD5 哈希值
├── marker_output/        # 解析输出：Marker 提取的 PDF 结构化 Markdown 文件
├── temp_uploads/         # 临时缓存：存放用户上传的临时文件 (处理后清理)
├── app.py                # 在线主入口：智能对话问答前端界面
├── file_uploader.py      # 离线主入口：知识库更新与文档解析前端
├── config_data.py        # 全局配置中心 (模型参数、路径、阈值、API Keys)
├── file_history_store.py # 会话管理：继承 LangChain BaseChatMessageHistory 的本地文件存储实现
├── knowledge_base.py     # 知识入库：封装 Chunking (按 Markdown 标题降级切分) 与 Embedding 逻辑
├── rag.py                # RAG 核心链：基于 LCEL 构建带记忆的生成流水线
├── retriever_service.py  # 检索引擎：双路召回 (Dense + Sparse) + RRF 融合 + BGE 重排的完整实现
├── Dockerfile / docker-compose.yml / .dockerignore # 容器化部署文件
└── requirements.txt      # 依赖环境清单
```

## 🚀 核心模块与技术亮点 (含金量解析)

### 1. 针对 CAE 领域的专业文档解析引擎 (`file_uploader.py` & `knowledge_base.py`)

- **痛点**：传统的 PyPDF 或 pdfplumber 无法准解析工程文献中的跨页表格和流体力学/固体力学公式。
- **解决方案**：集成 `Marker` 模型进行深度解析，将 PDF 高保真还原为 Markdown 格式，保留 `$$` 包裹的 LaTeX 公式和层级标题。
- **智能切片策略**：采用双重分块机制。优先使用 `MarkdownHeaderTextSplitter` 按 `H1/H2/H3` 逻辑段落进行语义切分，防止上下文割裂；针对超长段落，兜底使用 `RecursiveCharacterTextSplitter` 进行字符级长度限制。
- **工程鲁棒性**：实现基于 MD5 的文档去重机制，避免重复 Embedding 消耗 Token ；上传解析过程支持实时子进程日志输出，并包含临时文件自动清理机制。

### 2. 高精度双路混合检索与重排 (`retriever_service.py`)

- **痛点**：单纯的向量检索对 CAE 领域特定的“长尾词”和“专有名词”（如：`本构模型`、`六面体网格划分`、`Drucker-Prager准则`）召回率低。
- **双路召回设计**：
  - **密集检索 (Dense)**：基于 `DashScopeEmbeddings` + Chroma 抓取语义相关性。
  - **稀疏检索 (Sparse)**：基于 Jieba 分词构建 `BM25Okapi` 索引，抓取精确的专业词汇匹配。
- **动态索引与熔断机制**：系统初始化或手动触发时，自动从 Chroma 同步全量文本构建 BM25 词频树。若向量库为空，系统会自动熔断 BM25 逻辑，降级为纯向量检索，防止冷启动崩溃。
- **倒数排名融合 (RRF)**：通过 RRF 算法将两路召回结果无量纲化融合。
- **BGE 交叉语义重排**：引入 `BAAI/bge-reranker-base` (Cross-Encoder) 对初步召回的 Top-10 文档进行 Question-Context 深度交叉注意力计算，精筛出 Top-3 喂给大模型，极大降低了幻觉率。

### 3. 基于 LCEL 的工程化 RAG 链与会话管理 (`rag.py` & `file_history_store.py`)

- **底层架构**：深度使用 LangChain 的表达式语言 (LCEL) 构建流水线，将提问提取、混合检索、文档格式化 (注入来源和章节 Metadata)、提示词组装、大模型推理高度模块化。
- **自定义历史记忆机制**：放弃了依赖内存的 `ChatMessageHistory`，自己实现 `FileChatMessageHistory` 将 `session_id` 映射到本地 JSON 文件，实现了跨会话、防重启的多轮对话上下文追踪。
- **流式输出 (Streaming)**：无缝对接 Streamlit 的 `st.write_stream`，提供打字机式的极致用户体验。

## 第一部分：CAE_RAG_project 现有代码深度拆解

为了能在面试中应对任何深挖，你需要对每一个调用的类和每一段逻辑的“为什么（Why）”了如指掌。

### 1. 核心神经中枢：`config_data.py`

**技术拆解与作用：**

这个文件是全量配置字典。它的存在使得项目避免了“硬编码（Hardcode）”，是非常规范的工程化做法。

- **环境变量注入**：通过 `os.environ` 配置了阿里云百炼的 `DASHSCOPE_API_KEY` 和兼容 OpenAI 的 Base URL。这使得你可以无缝切换任何支持 OpenAI 格式的开源模型。
- **分块策略（Chunking Strategy）参数**：
  - `chunk_size = 1000`, `chunk_overlap = 100`：经典的滑动窗口切分法。Overlap 保证了上下文在边界处不会断裂。
  - `separators`：特别注意你包含了 `\n$$\n` 和 `$$`。这是**极具含金量**的细节，说明你专门针对 CAE 领域论文中的 LaTeX 数学公式做了防截断处理，保证公式在向量库中的完整性。

### 2. 离线数据摄入管道：`knowledge_base.py`

**技术拆解与作用：**

负责将非结构化文档转化为计算机可理解的“向量”，并存入数据库。

- **MD5 防重机制（幂等性设计）**：`get_string_md5` 和 `check_md5`。在处理大型文献库时，重复 Embedding 会极大浪费 Token 和时间。通过对文本内容计算 MD5 哈希值，实现了上传接口的“幂等性”（多次上传同一内容只有一次生效）。
- **混合切片刀法（双重 Splitter）**：
  - **第一刀（语义级）**：`MarkdownHeaderTextSplitter`。因为上游（Marker）输出了带有 `#` 的结构化 Markdown，这个切分器能保留父级标题。例如，某个片段会自带 Metadata `{"Header_H2": "材料本构模型"}`，这在后续 RAG 溯源时极具价值。
  - **第二刀（物理级兜底）**：`RecursiveCharacterTextSplitter`。如果某个标题下的段落依然超过了 1000 字符，这就起到兜底作用，防止超大 Chunk 撑爆大模型的上下文窗口。
- **Chroma 向量化入库**：调用 `DashScopeEmbeddings` 生成文本的高维向量表示，并附加自定义元数据（如 `source`, `create_time`, `operator`），写入本地 `persist_directory`。

### 3. 多轮对话记忆中枢：`file_history_store.py`

**技术拆解与作用：**

突破大模型“无记忆”的限制，实现本地持久化的多轮对话。

- **继承与重写 `BaseChatMessageHistory`**：LangChain 默认的记忆是存在内存（RAM）里的，服务一重启就没了。你通过继承基类，重写了 `messages` 属性和 `add_message` 方法，将对话序列化（`message_to_dict`）为 JSON 格式存入本地文件。
- **基于 `session_id` 的会话隔离**：通过读取不同的文件路径，系统可以同时支持多个用户的多轮对话，互不串联。

### 4. 高精度检索引擎：`retriever_service.py` (项目核心难点)

**技术拆解与作用：**

解决专业领域大模型“找不准”的问题，构建了企业级的“双路召回 + 重排序”架构。

- **双路召回（Dense + Sparse）**：
  - **向量召回（Chroma）**：擅长泛化和语义相近匹配（如搜“形变”能匹配到“位移”）。
  - **稀疏召回（BM25 + jieba）**：基于词频（TF-IDF 的变种）。擅长专业专有名词的精准匹配（如绝对匹配“Drucker-Prager准则”），不会因为语义泛化而跑偏。
- **数据一致性同步与熔断机制**：`sync_bm25_from_chroma` 方法每次初始化时，会将 Chroma 中的数据拉出来构建 BM25 词频树。里面你写了熔断逻辑（如果向量库为空，自动降级为只用向量检索），防止冷启动报错，工程鲁棒性极强。
- **倒数排名融合（RRF Algorithm）**：将两路的得分无量纲化。公式为 $Score = 1 / (k + rank)$。因为向量得分是余弦相似度，BM25 是绝对分数，两者量纲不同不能直接相加，RRF 是业内最成熟的解决不同检索器融合的算法。
- **交叉编码器重排（BGE-Reranker）**：双路召回了前 10 个（`initial_k`），但其中可能有水分。引入 Cross-Encoder 对 Query 和 Document 拼接后进行二次深度打分，精准提炼出最核心的 3 个（`final_k`）喂给大模型。

### 5. RAG 业务流水线：`rag.py`

**技术拆解与作用：**

将检索器、记忆组件和大模型组装成一条自动化的 LCEL 流水线。

- **LCEL (LangChain Expression Language) 链式组装**：
  - `RunnablePassthrough` 获取用户当前输入。
  - `RunnableLambda(extract_query) | perform_retrieval | format_document`：这组管道将用户问题丢入上一节的混合检索器，并将返回的 `Document` 对象格式化为带来源的纯文本结构。
- **Prompt 模板工程**：强约束系统 Prompt（“必须完全基于参考资料...禁止编造...提取来源标签”），有效抑制了 LLM 在 CAE 领域的幻觉。结合了 `MessagesPlaceholder("history")` 用于将历史记录注入。
- **RunnableWithMessageHistory**：终极封装器，自动劫持大模型的输入和输出，将其自动更新到 `file_history_store` 的本地 JSON 中。

### 6. 前端展示与交互层：`app.py` & `file_uploader.py`

**技术拆解与作用：**

- **`file_uploader.py` (离线管理 UI)**：利用 `subprocess.Popen` 调用了外部的 Marker 库处理 PDF。这是一个重量级操作，因为流体力学、结构力学的 PDF 充满双栏和公式，这里你用流式输出在终端打印 Marker 日志，非常利于调试。处理后调用 `knowledge_base.py` 写入数据库。
- **`app.py` (在线聊天 UI)**：利用 Streamlit 的 `session_state` 保证页面刷新时大模型引擎和聊天记录不丢失。使用 `st.write_stream` 配合 `chain.stream` 实现了完美的打字机效果。

------

## 第二部分：项目数据流转与文件耦合关系

要回答“代码文件间如何联系”，我们可以模拟一次用户的请求全流程：

### 流程 1：文献入库流 (Offline Pipeline)

1. 用户在 **`file_uploader.py`** 界面上传《某隧道开挖参数解析.pdf》。
2. **`file_uploader.py`** 在本地临时保存 PDF，唤起 Marker CLI 进行视觉排版和公式解析，生成 Markdown 文件。
3. 将解析出的 Markdown 字符串，作为参数传递给 **`knowledge_base.py`** 中的 `upload_by_str` 方法。
4. **`knowledge_base.py`** 引用 **`config_data.py`** 中的超参数，先过 MD5 查重。
5. 查重通过，走双重 Splitter 切片，调用 Embeddings 模型，最终落盘保存入 Chroma 的 DB 文件夹。

### 流程 2：在线问答流 (Online QA Pipeline)

1. 用户在 **`app.py`** 界面输入问题：“如何设置上述隧道的开挖支护参数？”。
2. **`app.py`** 调用缓存在 Session 中的 **`rag.py`** 里的 `RagService.chain.stream()`。
3. LCEL 链启动，首先触发 **`rag.py`** 里的检索逻辑，实际调用的是 **`retriever_service.py`** 的 `search_and_rerank`。
4. **`retriever_service.py`** 读取 Chroma 数据库和 BM25 索引，经过双路召回 -> RRF 融合 -> BGE 重排，返回 Top-3 最相关的文本块，交还给 **`rag.py`**。
5. **`rag.py`** 中的 `RunnableWithMessageHistory` 会同时去调用 **`file_history_store.py`**，根据 `session_id` 拉取此前的聊天记录。
6. **`rag.py`** 将“Top-3 参考文本” + “历史聊天记录” + “当前问题” 填入 Prompt，发给 `ChatTongyi` (Qwen) 大模型推理。
7. 大模型的回复以流式 (Stream) 形式返回给 **`app.py`**，渲染在网页上。同时，回复内容被异步写回 **`file_history_store.py`** 持久化。

------

## 第三部分：架构演进与深度优化方案（独立列出）

正如你提到的，为了应对高并发、真实线上部署以及复杂的数据结构，当前架构只是一个优秀的“原型（Prototype）”。以下是针对你痛点的专业优化方案，可以作为你简历中的**“项目难点与下一步迭代方向”**：

### 1. 历史记录带来的“追问失忆”问题（Query Rewrite）

- **痛点**：当前项目中，如果用户问：“它的弹性模量是多少？”，系统直接拿这句话去 Chroma 搜索，完全搜不到，因为缺乏主语。
- **解决方案**：在检索前，插入一个独立的**问题重写（Query Rewrite）**节点。
  - **技术实现**：使用一个较小/快速的大模型（如 Qwen-turbo），输入 `历史聊天记录` 和 `当前问题 ("它的弹性模量是多少？")`，让大模型输出一句独立且完整的话：`"用户正在询问刚才讨论的C30混凝土材料的弹性模量是多少。"`。
  - 拿这句重写后的完整话语，去调起 `retriever_service.py`，召回率将呈指数级提升。

### 2. 线上部署与高并发问题

- **痛点**：Streamlit 是阻塞式的，适合做 Demo 不适合做高并发的生产环境。且 PDF 用 Marker 解析是一个极其耗时（甚至需要 GPU）的操作，同步等待会导致网页超时。
- **解决方案（前后端分离与微服务化）**：
  - **后端框架替换**：将 `app.py` 和业务逻辑剥离，使用 **FastAPI** 编写异步 (`async/await`) 的 API 接口，利用 Uvicorn 部署，天生支持高并发。
  - **会话存储升级**：放弃本地 JSON 读写 (`file_history_store.py`)，改用 **Redis** 存储 `session_id` 和历史记录，内存级读写速度，且支持分布式。
  - **消息队列处理 PDF**：在 `file_uploader.py` 环节，引入 **Celery + RabbitMQ/Redis** 消息队列。用户上传 PDF 后，后端立刻返回“解析任务已提交”，后台 worker 慢慢跑 Marker 解析，跑完再存入向量库。

### 3. 混合路由机制（Semantic Routing）

- **痛点**：你的项目中既有大量非结构化文本（论文），也面临具体的结构化参数（如 MySQL 中的设备配置、特定钻爆法方案表）、乃至错综复杂的空间关系约束。纯用 RAG 效果不佳。
- **解决方案（引入 Agent 路由思维）**：
  - 在大模型接收问题的第一道关卡，设置一个**意图识别路由器（Semantic Router）**。
  - **路由分支 A (Text-to-SQL)**：当用户问“某型号盾构机的标准掘进速度是多少？”时，路由将其判定为结构化数据查询，直接将自然语言转化为 SQL，查内部 MySQL 设备库，不走向量检索。
  - **路由分支 B (GraphRAG / 知识图谱)**：当用户问“在高原冻土区域开挖隧道，开挖方法、支护形式和设备配置之间有什么依赖关系？”这种强关联问题时，调用 GraphRAG。基于图数据库（如 Neo4j）提取“实体-关系-实体”的三元组网络，沿着网络拓扑图寻找答案。
  - **路由分支 C (Vector RAG)**：即你目前已完成的部分，专门应对“某篇论文是如何定义屈服准则的”这类纯知识型文档问答。