# 面向 CAE 仿真领域的RAG智能问答系统

## 📌 项目背景与简介

本项目是专为 **计算机辅助工程 (CAE)** 领域打造的检索增强生成 (RAG) 系统。针对工程文献中**公式密集、术语生僻、上下文指代模糊**等痛点，通过 **Marker 深度解析**、**双路混合检索**与**多轮对话查询重写**技术，构建了一个严谨的仿真专家助手。

## 🏗️ 项目核心架构

系统由 **离线知识处理** 与 **在线智能问答** 两大引擎组成：

1. **离线：高保真数据入库 (Offline Pipeline)**

- **深度文档解析**：集成 `Marker` 模型，将 PDF 转化为带 LaTeX 公式（`$$`）和结构化标题（`#`）的 Markdown 格式。
- **双重切片策略**：先用 `MarkdownHeaderTextSplitter` 进行语义级段落切分（保留 H1-H3 标题元数据），再用 `RecursiveCharacterTextSplitter` 结合公式占位符（`\n$$\n`）进行长度兜底。
- **幂等性保障**：引入 MD5 哈希校验机制，确保重复文档不被重复向量化，节省 Token 消耗。

2. **在线：上下文感知检索链 (Online Pipeline)**

- **查询重写 (Query Rewrite)**：利用 Qwen 大模型结合历史会话，将用户的模糊追问（如“它怎么设？”）重写为独立的专业搜索词（如“Abaqus C30 混凝土弹性模量设置”）。
- **混合召回 (Hybrid Retrieval)**：
  - **密集检索**：Chroma 向量库捕捉语义相关性。
  - **稀疏检索**：Jieba 分词 + BM25Okapi 算法实现专业术语的精准匹配。
- **深度重排 (Reranking)**：通过 **RRF (倒数排名融合)** 算法合并两路结果，并使用 `BGE-Reranker` 交叉编码器进行 Top-10 到 Top-3 的精选压滤，极大降低幻觉率。

## 🛠️ 技术栈选型

- **前端交互**：Streamlit (聊天界面 `app.py`、文档上传 `file_uploader.py`)
- **大模型框架**：LangChain
- **模型选型**：阿里云百炼 DashScope (`qwen-turbo`、`text-embedding-v4`)
- **文档解析**：Marker CLI (专门解决 PDF 复杂数学公式与多栏排版解析难题)
- **检索与重排**：ChromaDB (向量库), Jieba + BM25Okapi (关键词检索), Sentence-Transformers (`BAAI/bge-reranker-base`)
- **工程化部署**：Docker, Docker Compose

## 📂 项目目录结构

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
├── retriever_service.py  # 检索引擎：双路召回 + RRF 融合 + BGE 重排的完整实现
├── Dockerfile / docker-compose.yml / .dockerignore # 容器化部署文件
├── README.md # 使用说明文档
└── requirements.txt      # 依赖环境清单
```

## 核心模块与技术亮点 

### 核心模块：

1. **针对 CAE 领域的专业文档解析引擎 (`file_uploader.py` & `knowledge_base.py`)**

- **痛点**：传统的 PyPDF 或 pdfplumber 无法准确解析工程文献中的跨页表格和流体力学/固体力学公式。
- **解决方案**：集成 `Marker` 模型进行深度解析，将 PDF 高保真还原为 Markdown 格式，保留 `$$` 包裹的 LaTeX 公式和层级标题。
- **智能切片策略**：采用双重分块机制。优先使用 `MarkdownHeaderTextSplitter` 按 `H1/H2/H3` 逻辑段落进行语义切分，防止上下文割裂；针对超长段落，兜底使用 `RecursiveCharacterTextSplitter` 进行字符级长度限制。
- **工程鲁棒性**：实现基于 MD5 的文档去重机制，避免重复 Embedding 消耗 Token ；上传解析过程支持实时子进程日志输出，并包含临时文件自动清理机制。

2. **高精度双路混合检索与重排 (`retriever_service.py`)**

- **痛点**：单纯的向量检索对 CAE 领域特定的“长尾词”和“专有名词”（如：`本构模型`、`六面体网格划分`、`Drucker-Prager准则`）召回率低。
- **双路召回设计**：
  - **密集检索 (Dense)**：基于 `DashScopeEmbeddings` + Chroma 抓取语义相关性。
  - **稀疏检索 (Sparse)**：基于 Jieba 分词构建 `BM25Okapi` 索引，抓取精确的专业词汇匹配。
- **动态索引与熔断机制**：系统初始化或手动触发时，自动从 Chroma 同步全量文本构建 BM25 词频树。若向量库为空，系统会自动熔断 BM25 逻辑，降级为纯向量检索，防止冷启动崩溃。
- **倒数排名融合 (RRF)**：通过 RRF 算法将两路召回结果无量纲化融合。
- **BGE 交叉语义重排**：引入 `BAAI/bge-reranker-base` (Cross-Encoder) 对初步召回的 Top-10 文档进行 Question-Context 深度交叉注意力计算，精筛出 Top-3 喂给大模型，极大降低了幻觉率。

3. **基于 LCEL 的工程化 RAG 链与会话管理 (`rag.py` & `file_history_store.py`)**

- **底层架构**：深度使用 LangChain 的表达式语言 (LCEL) 构建流水线，将提问提取、混合检索、文档格式化 (注入来源和章节 Metadata)、提示词组装、大模型推理高度模块化。
- **自定义历史记忆机制**：放弃了依赖内存的 `ChatMessageHistory`，自己实现 `FileChatMessageHistory` 将 `session_id` 映射到本地 JSON 文件，实现了跨会话、防重启的多轮对话上下文追踪。
- **流式输出 (Streaming)**：无缝对接 Streamlit 的 `st.write_stream`，提供打字机式的极致用户体验。

### 亮点的详细阐述：

#### 一、 Marker 的底层工作流：Surya 之后发生了什么？

你可以把 Marker 理解为一个**“流水线（Pipeline）”**或者**“混合专家系统（MoE 思想在文档解析上的应用）”**。在 Surya 完成了“圈地（版面分析）”之后，Marker 会对不同的“地块”进行分类处理：

1. **第一步：Surya 版面分析与阅读顺序（Layout & Reading Order）**
   - Surya 利用视觉模型，在文档图像上画出一个个边界框（Bounding Boxes），并打上标签：这是“正文”、那是“标题”、这是“表格”、那是“公式”、这是“图片”。
   - 同时，Surya 会计算出人类视角的**阅读顺序**（比如双栏排版时，知道先读左列再读右列，而不是直接横着切断）。
2. **第二步：任务路由与专业模型解析（Routing & Extraction）**
   - **对于纯文本块（Text/Title）：** Marker 会提取底层 PDF 的原生字符流，或者调用高精度的 OCR 模型（如 Surya-OCR）提取文字，并修正换行符和拼写错误。
   - **对于公式块（Equation）：** 这是传统工具的死穴。Marker 会将公式区域的图像裁剪下来，送给专门的**数学公式识别模型**（例如 Texify 或类似 Nougat 的视觉模型），直接将其翻译成标准的 LaTeX 代码（如 `$E=mc^2$`）。
   - **对于表格块（Table）：** Marker 会调用表格结构识别（Table Structure Recognition）算法。不仅识别表格里的字，还能识别出网格线、合并单元格，然后将其重构成 Markdown 格式的表格（`| Header | Header |`）。
3. **第三步：Markdown 拼装与启发式清洗（Assembly & Post-processing）**
   - 最后，Marker 会根据第一步得出的阅读顺序，把文本、LaTeX 公式、Markdown 表格像拼乐高一样拼装起来，并利用启发式规则清洗掉多余的空格、页眉页脚，最终输出一份极其干净、**对大模型（LLM）极其友好**的 Markdown 文档。

------

#### 二、 为什么不用传统工具？(竞品对比分析)

在面试中，踩一捧一（有理有据地踩）是展现技术深度的最好方式。

| **解析工具**          | **核心原理**                                          | **致命缺点 (在 CAE 场景下)**                                 | **对大模型 (LLM) 的友好度**                                  |
| --------------------- | ----------------------------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ |
| **PyPDF / PyPDF2**    | 基于 PDF 底层代码流提取文本。                         | **无视觉概念。** 遇到双栏排版会直接跨栏读取造成语句错乱；**遇到公式会变成乱码符号**；表格会变成一堆没有结构的散字。 | 极差（全是噪音和乱码）。                                     |
| **pdfplumber**        | 基于字符的物理坐标（X,Y）进行提取。                   | 提取规则死板。**无法处理扫描版 PDF**；对于没有边框线的表格（三线表），经常无法正确还原行列关系；同样无法理解复杂公式。 | 较差（表格提取勉强可用，但公式依然无解）。                   |
| **Unstructured**      | 综合性极强的解析管道，融合了规则和 YOLOX 等视觉模型。 | **过于庞大且通用。** 它的目标是输出 JSON 元素列表，将其转化为干净 Markdown 的后续成本较高。在“公式转 LaTeX”这一细分领域的开箱即用效果不如 Marker。 | 良好（但需要较多二次开发）。                                 |
| **Marker (你的方案)** | **端到端的视觉+专有模型。**                           | 处理速度相对较慢（因为需要跑深度学习模型，占用 GPU 资源）。  | **极佳**（直接输出带标题树、表格、LaTeX 公式的结构化 Markdown）。 |

------

#### 三、 面试实战话术：“为什么选 Marker？”

当面试官问出“为什么要选这个模型，而不用 PyPDF 或者 pdfplumber？”时，你可以这样回答：

> “其实在项目初期，我也尝试过像 PyPDF 和 pdfplumber 这样的传统解析库，但在我们的 **CAE 仿真业务场景**下，它们根本走不通，原因有三个：
>
> **第一是公式的灾难性破坏。** CAE 仿真手册里充满了大量的偏微分方程和张量推导公式。传统的 PyPDF 提取出来全是不可读的乱码，大模型根本无法理解。而 Marker 内部集成了专用的数学公式识别模型，能把复杂的公式精准转化为 **LaTeX 格式**，保留了完整的数学语义。
>
> **第二是复杂表格的结构丢失。** 我们的文档里有很多材料参数表，甚至有‘表头合并’的嵌套表格。pdfplumber 虽然能基于线框提取表格，但对没有边框的三线表极易失效。Marker 通过视觉表格重建，能无损转化为 Markdown 表格，让大模型准确对应数据和表头。
>
> **第三是多栏排版的上下文割裂。** 很多学术手册是双栏甚至三栏排版。传统工具是按 Y 轴硬扫，会导致左边半句话和右边半句话拼在一起。Marker 前置的 Surya 模型能极其精准地分析出人类的**阅读顺序（Reading Order）**。
>
> **总结来说**，传统工具只是在‘提取字符’，而大模型 RAG 需要的是‘结构化知识’。Marker 输出的带有清晰层级（H1, H2）和排版的 Markdown 文档，能让后续的 Chunking（语义切块）变得极其精准，直接从数据供给侧把 RAG 的质量拉高了一个层级。这是我最终选择它的原因。”

**核心技巧：** 回答这个问题时，不要只谈纯粹的计算机理论，**一定要把话题拉回你的“土木工程/CAE”老本行**。提到“偏微分方程”、“材料参数表”，面试官立刻就会觉得：“这小伙子是真正结合业务痛点在做技术选型，而不是为了用大模型而用大模型。”

## 代码解读

### 第一部分：CAE_RAG_project 现有代码深度拆解

为了能在面试中应对任何深挖，你需要对每一个调用的类和每一段逻辑的“为什么（Why）”了如指掌。

#### 1. 核心神经中枢：`config_data.py`

**技术拆解与作用：**

这个文件是全量配置字典。它的存在使得项目避免了“硬编码（Hardcode）”，是非常规范的工程化做法。

- **环境变量注入**：通过 `os.environ` 配置了阿里云百炼的 `DASHSCOPE_API_KEY` 和兼容 `OpenAI` 的 `Base URL`。这使得你可以无缝切换任何支持 OpenAI 格式的开源模型。
- **分块策略（Chunking Strategy）参数**：
  - `chunk_size = 1000`, `chunk_overlap = 100`：经典的滑动窗口切分法。Overlap 保证了上下文在边界处不会断裂。
  - `separators`：特别注意你包含了 `\n$$\n` 和 `$$`。这是**极具含金量**的细节，说明你专门针对 CAE 领域论文中的 LaTeX 数学公式做了防截断处理，保证公式在向量库中的完整性。

#### 2. 离线数据摄入管道：`knowledge_base.py`

**技术拆解与作用：**

负责将非结构化文档转化为计算机可理解的“向量”，并存入数据库。

- **MD5 防重机制（幂等性设计）**：`get_string_md5` 和 `check_md5`。在处理大型文献库时，重复 Embedding 会极大浪费 Token 和时间。通过对文本内容计算 MD5 哈希值，实现了上传接口的“幂等性”（多次上传同一内容只有一次生效）。
- **混合切片刀法（双重 Splitter）**：
  - **第一刀（语义级）**：`MarkdownHeaderTextSplitter`。因为上游（Marker）输出了带有 `#` 的结构化 Markdown，这个切分器能保留父级标题。例如，某个片段会自带 Metadata `{"Header_H2": "材料本构模型"}`，这在后续 RAG 溯源时极具价值。
  - **第二刀（物理级兜底）**：`RecursiveCharacterTextSplitter`。如果某个标题下的段落依然超过了 1000 字符，这就起到兜底作用，防止超大 Chunk 撑爆大模型的上下文窗口。
- **Chroma 向量化入库**：调用 `DashScopeEmbeddings` 生成文本的高维向量表示，并附加自定义元数据（如 `source`, `create_time`, `operator`,`chunk_index`），写入本地 `persist_directory`。

#### 3. 多轮对话记忆中枢：`file_history_store.py`

**技术拆解与作用：**

突破大模型“无记忆”的限制，实现本地持久化的多轮对话。

- **继承与重写 `BaseChatMessageHistory`**：LangChain 默认的记忆是存在内存（RAM）里的，服务一重启就没了。你通过继承基类，重写了 `messages` 属性和 `add_message` 方法，将对话序列化（`message_to_dict`）为 JSON 格式存入本地文件。
- **基于 `session_id` 的会话隔离**：通过读取不同的文件路径，系统可以同时支持多个用户的多轮对话，互不串联。

#### 4. 高精度检索引擎：`retriever_service.py` (项目核心难点)

**技术拆解与作用：**

解决专业领域大模型“找不准”的问题，构建了企业级的“双路召回 + 重排序”架构。

- **双路召回（Dense + Sparse）**：
  - **向量召回（Chroma）**：擅长泛化和语义相近匹配（如搜“形变”能匹配到“位移”）。
  - **稀疏召回（BM25 + jieba）**：基于词频（TF-IDF 的变种）。擅长专业专有名词的精准匹配（如绝对匹配“Drucker-Prager准则”），不会因为语义泛化而跑偏。
- **数据一致性同步与熔断机制**：`sync_bm25_from_chroma` 方法每次初始化时，会将 Chroma 中的数据拉出来构建 BM25 词频树。里面你写了熔断逻辑（如果向量库为空，自动降级为只用向量检索），防止冷启动报错，工程鲁棒性极强。
- **倒数排名融合（RRF Algorithm）**：将两路的得分无量纲化。公式为 $Score = 1 / (k + rank)$。因为向量得分是余弦相似度，BM25 是绝对分数，两者量纲不同不能直接相加，RRF 是业内最成熟的解决不同检索器融合的算法。
- **交叉编码器重排（BGE-Reranker）**：双路召回了前 10 个（`initial_k`），但其中可能有水分。引入 Cross-Encoder 对 Query 和 Document 拼接后进行二次深度打分，精准提炼出最核心的 3 个（`final_k`）喂给大模型。

#### 5. RAG 业务流水线：`rag.py`

**技术拆解与作用：**

将检索器、记忆组件和大模型组装成一条自动化的 LCEL 流水线。

- **多功能 LCEL 链式组装（Nested Chains）**

  - **rewrite_chain（重写分支）**：这是一个独立的子链，专门负责将模糊的对话（如“那这个参数怎么设？”）转化为具体的检索词（如“LS-DYNA 中 MAT_024 材质模型的密度参数设置”）。

  - **RunnablePassthrough.assign**：这是本次更新的高级用法。它允许我们在不破坏原始 `input` 数据的同时，动态地在管道流中添加 `rewritten_query` 和 `context` 两个新变量。

- **上下文压缩与检索优化**

  - **智能检索词提取**：通过 `rewrite_prompt` 强迫大模型扮演 CAE 专家，结合 `history` 占位符，确保检索动作是基于全量对话信息的。

  - **perform_retrieval (精排逻辑)**：在流水线内嵌入了 `search_and_rerank`，实现了从 10 个候选文档中精选 3 个的操作，极大地提升了上下文的信噪比。

- **结构化文档格式化（Format Metadata）**
  - **溯源强化**：`format_document` 不再只是提取内容，它还自动解析 `Metadata`（如文件名、H1/H2 标题），生成的参考资料带有明显的 `[参考资料 n] (来源: xxx | 章节: xxx)` 标签，直接支撑了后续 Prompt 中的来源提取要求。

- **两阶段 Prompt 工程**

  - **重写 Prompt**：侧重于“术语转换”和“去模糊化”。

  - **QA Prompt**：侧重于“严谨性”和“逻辑推理”。特别新增了对**表格/离散数据**的推理授权，这在处理 CAE 仿真参数表时非常关键，弥补了纯语义检索的不足。

- **透明化调试监控**
  - 引入了 `print_rewritten_query` 和 `print_prompt` 两个辅助函数。在 LCEL 中，它们作为中间件（Middleware）存在，能让你在控制台实时看到“模型到底把我的话改成了什么”以及“最后喂给模型的内容长什么样”，是生产环境排查幻觉的利器。

#### 6. 前端展示与交互层：`app.py` & `file_uploader.py`

**技术拆解与作用：**

- **`file_uploader.py` (离线管理 UI)**：利用 `subprocess.Popen` 调用了外部的 Marker 库处理 PDF。这是一个重量级操作，因为流体力学、结构力学的 PDF 充满双栏和公式，这里你用流式输出在终端打印 Marker 日志，非常利于调试。处理后调用 `knowledge_base.py` 写入数据库。
- **`app.py` (在线聊天 UI)**：利用 Streamlit 的 `session_state` 保证页面刷新时大模型引擎和聊天记录不丢失。使用 `st.write_stream` 配合 `chain.stream` 实现了完美的打字机效果。

------

### 第二部分：项目数据流转与文件耦合关系

要回答“代码文件间如何联系”，我们可以模拟一次用户的请求全流程：

#### 流程 1：文献入库流 (Offline Pipeline)

1. 用户在 **`file_uploader.py`** 界面上传《某隧道开挖参数解析.pdf》。
2. **`file_uploader.py`** 在本地临时保存 PDF，唤起 Marker CLI 进行视觉排版和公式解析，生成 Markdown 文件。
3. 将解析出的 Markdown 字符串，作为参数传递给 **`knowledge_base.py`** 中的 `upload_by_str` 方法。
4. **`knowledge_base.py`** 引用 **`config_data.py`** 中的超参数，先过 MD5 查重。
5. 查重通过，走双重 Splitter 切片，调用 Embeddings 模型，最终落盘保存入 Chroma 的 DB 文件夹。

#### 流程 2：在线问答流 (Online QA Pipeline)

1. 用户在 **`app.py`** 界面输入问题：“如何设置上述隧道的开挖支护参数？”。
2. **`app.py`** 调用缓存在 Session 中的 **`rag.py`** 里的 `RagService.chain.stream()`。
3. LCEL 链启动，首先触发 **`rag.py`** 里的检索逻辑，实际调用的是 **`retriever_service.py`** 的 `search_and_rerank`。
4. **`retriever_service.py`** 读取 Chroma 数据库和 BM25 索引，经过双路召回 -> RRF 融合 -> BGE 重排，返回 Top-3 最相关的文本块，交还给 **`rag.py`**。
5. **`rag.py`** 中的 `RunnableWithMessageHistory` 会同时去调用 **`file_history_store.py`**，根据 `session_id` 拉取此前的聊天记录。
6. **`rag.py`** 将“Top-3 参考文本” + “历史聊天记录” + “当前问题” 填入 Prompt，发给 `ChatTongyi` (Qwen) 大模型推理。
7. 大模型的回复以流式 (Stream) 形式返回给 **`app.py`**，渲染在网页上。同时，回复内容被异步写回 **`file_history_store.py`** 持久化。

------

### 第三部分：架构演进与深度优化方案（独立列出）

正如你提到的，为了应对高并发、真实线上部署以及复杂的数据结构，当前架构只是一个优秀的“原型（Prototype）”。以下是针对你痛点的专业优化方案，可以作为你简历中的**“项目难点与下一步迭代方向”**：

#### 1. 历史记录带来的“追问失忆”问题（Query Rewrite）

- **痛点**：当前项目中，如果用户问：“它的弹性模量是多少？”，系统直接拿这句话去 Chroma 搜索，完全搜不到，因为缺乏主语。
- **解决方案**：在检索前，插入一个独立的**问题重写（Query Rewrite）**节点。
  - **技术实现**：使用一个较小/快速的大模型（如 Qwen-turbo），输入 `历史聊天记录` 和 `当前问题 ("它的弹性模量是多少？")`，让大模型输出一句独立且完整的话：`"用户正在询问刚才讨论的C30混凝土材料的弹性模量是多少。"`。
  - 拿这句重写后的完整话语，去调起 `retriever_service.py`，召回率将呈指数级提升。

#### 2. 线上部署与高并发问题

- **痛点**：Streamlit 是阻塞式的，适合做 Demo 不适合做高并发的生产环境。且 PDF 用 Marker 解析是一个极其耗时（甚至需要 GPU）的操作，同步等待会导致网页超时。
- **解决方案（前后端分离与微服务化）**：
  - **后端框架替换**：将 `app.py` 和业务逻辑剥离，使用 **FastAPI** 编写异步 (`async/await`) 的 API 接口，利用 Uvicorn 部署，天生支持高并发。
  - **会话存储升级**：放弃本地 JSON 读写 (`file_history_store.py`)，改用 **Redis** 存储 `session_id` 和历史记录，内存级读写速度，且支持分布式。
  - **消息队列处理 PDF**：在 `file_uploader.py` 环节，引入 **Celery + RabbitMQ/Redis** 消息队列。用户上传 PDF 后，后端立刻返回“解析任务已提交”，后台 worker 慢慢跑 Marker 解析，跑完再存入向量库。

#### 3. 混合路由机制（Semantic Routing）

- **痛点**：你的项目中既有大量非结构化文本（论文），也面临具体的结构化参数（如 MySQL 中的设备配置、特定钻爆法方案表）、乃至错综复杂的空间关系约束。纯用 RAG 效果不佳。
- **解决方案（引入 Agent 路由思维）**：
  - 在大模型接收问题的第一道关卡，设置一个**意图识别路由器（Semantic Router）**。
  - **路由分支 A (Text-to-SQL)**：当用户问“某型号盾构机的标准掘进速度是多少？”时，路由将其判定为结构化数据查询，直接将自然语言转化为 SQL，查内部 MySQL 设备库，不走向量检索。
  - **路由分支 B (GraphRAG / 知识图谱)**：当用户问“在高原冻土区域开挖隧道，开挖方法、支护形式和设备配置之间有什么依赖关系？”这种强关联问题时，调用 GraphRAG。基于图数据库（如 Neo4j）提取“实体-关系-实体”的三元组网络，沿着网络拓扑图寻找答案。
  - **路由分支 C (Vector RAG)**：即你目前已完成的部分，专门应对“某篇论文是如何定义屈服准则的”这类纯知识型文档问答。

#### 4. Query改写

- **解决方案**：
  - **语义增强**，通过 HyDE 生成假设文档，让模型先写“假答案”，再用答案去搜答案，提升召回相关度
  - **任务分解**，利用 Step-back 或子查询拆解，将一个复杂问题拆分为多个简单的、粒度更细的检索单元
  - **上下文补全**，进行指代消解与查询压缩，将多轮历史信息“脱水”，形成独立完整的语句
- **难点**：
  - **响应延迟**，改写增加LLM调用导致TTFT变长
  - **查询漂移**，改写后偏离原意，导致召回无关内容
  - **成本开销**，每条请求多消耗Token，增加运营负

## 评估板块

你需要从以下**三个核心维度**对你的系统建立监控和测评：

#### 1. 响应延迟测评 (Latency / System Profiling)

- **TTFT (Time To First Token)：**用户发问后，流式输出打出第一个字的耗时。
- **Retrieval Time：**检索器从 Chroma + BM25 中召回 Document 的耗时（混合检索通常会增加几百毫秒延迟）。
- **Embedding Time：**上传文档时的处理速度（即我们刚才打点的部分）。

#### 2. 检索质量测评 (Retrieval Evaluation)

- **Context Precision (上下文精度)：**召回的 Top-3 片段中，到底有多少是真正包含答案的？还是召回了一堆干扰信息？
- **Context Recall (上下文召回率)：**为了回答某个问题所需的所有前提条件，你的系统都成功找齐了吗？（这对于隧道施工这种多工序、强关联的知识点极其重要）。

#### 3. 生成质量测评 (Generation Evaluation)

- **Faithfulness (忠实度/幻觉率)：**大模型的回答，是否 100% 来源于你召回的参考资料？有没有自己胡编乱造隧道施工参数？
- **Answer Relevance (回答相关性)：**回答有没有偏题？

**🛠️ 测评工具推荐：** 你可以了解一下 **RAGAS (RAG Assessment)** 或者 **TruLens**。这两个开源框架可以自动化地帮你计算上述所有指标，给你的系统打出一个雷达图分数。这会让你的项目（或论文）看起来具有极高的学术严谨性和工程落地价值！

#### 📝 后续评估（Evaluation）该怎么做？

既然你要做系统的测评评估，针对入库（Indexing）阶段，你可以记录并评估以下三个核心指标：

1. **吞吐率 (Throughput)**
   - **计算公式**：`处理总字数 / 总耗时 (total_time)`
   - **意义**：评估你的系统每秒能处理多少字的知识入库（比如 5000字/秒）。这决定了未来如果给全量规程数据（比如上百本 PDF）建库需要多少小时。
2. **切片合理性评估 (Chunk Quality)**
   - **评测方法**：随机抽取入库的 50 个 `knowledge_chunks`，人工（或用 LLM 打分）评估：段落语义是否完整？有没有把一句话从中间截断？公式有没有被破坏？
   - **优化点**：如果切出来的东西牛头不对马嘴，你就需要调整 `config.chunk_size` 和 `config.chunk_overlap`。
3. **API 成本与并发瓶颈**
   - **评测方法**：记录每次入库请求的 Token 消耗量。
   - **瓶颈测试**：DashScope API 有 QPS（每秒请求数）和 TPM（每分钟 Token 数）限制。当上传超级大文件时，如果不做批处理（Batching）或者加延时（sleep），可能会触发阿里云的限流报错（HTTP 429 Too Many Requests）。

### 第一步：构建“黄金测试集” (Ground Truth Dataset)

评估的第一步，是你要和工作室的同学一起，人工整理出至少 **30~50 个**高质量的 QA 测试对。这些测试用例必须覆盖你们日常遇到的各种刁钻问题。

在你的代码目录下新建一个 `eval_dataset.json`，格式如下。请注意，这里的例子结合了你正在深入的**藏区公路钻爆法隧道开挖与支护**方向：

JSON

```
[
  {
    "question": "在藏区高寒高海拔环境下，钻爆法开挖隧道时，通风设备的配置有什么特殊要求？",
    "ground_truth": "根据《高寒高海拔隧道施工规范》，必须考虑空气稀薄导致的制氧量下降和柴油机械燃烧不充分。通风设备配置需按常规平原地区的 1.3~1.5 倍计算风量，并配备长距离射流风机，同时需考虑防冻保温措施。",
    "difficulty": "hard",
    "type": "equipment_config"
  },
  {
    "question": "Abaqus 里 Mohr-Coulomb 本构模型中，dilation angle（剪胀角）一般怎么取值？",
    "ground_truth": "对于一般的岩石材料，剪胀角通常取内摩擦角的一部分，通常在 0 到内摩擦角之间。若岩体不考虑体积膨胀，可保守取值为 0。",
    "difficulty": "medium",
    "type": "cae_parameter"
  }
]
```

*提示：一定要包含 `ground_truth`（标准答案），这是后续让大模型裁判打分的唯一标尺。*

------

### 第二步：确立 RAG 评估的“四大金刚”指标

业界目前最权威的评估框架是 **RAGAS**。它的核心就是从“检索”和“生成”两个维度，拆解出 4 个核心指标。你要在代码里让大模型裁判分别给这 4 项打分（0-5分）：

#### 🔍 维度一：检索质量 (Retrieval Quality)

1. **Context Precision (上下文精度)**：
   - **白话**：系统捞出来的 top-3 文本块里，是不是全都是干货？有没有夹杂没用的废话？
   - **低分表现**：捞出来的文献确实包含答案，但同时捞出来一堆毫不相干的章节。
2. **Context Recall (上下文召回率)**：
   - **白话**：为了完整回答“通风设备配置”这个问题，需要的约束条件（空气稀薄、1.3倍风量、防冻）有没有**全部**被捞出来？
   - **低分表现**：漏掉了“防冻”这个关键信息，导致大模型只能回答出一半。

#### 🧠 维度二：生成质量 (Generation Quality)

1. **Faithfulness (忠实度 / 反幻觉指数)**：
   - **白话**：大模型给出的回答，是不是 **100% 来源于**捞出来的参考资料？
   - **致命错误**：如果参考资料里根本没提参数的具体数值，大模型自己凭借网上的记忆“编”了一个剪胀角数值，这项直接打 0 分（在工程仿真中，参数造假是灾难性的）。
2. **Answer Relevance (回答相关性)**：
   - **白话**：大模型有没有正面回答用户的问题？
   - **低分表现**：用户问“怎么配置通风设备”，大模型长篇大论背诵了一段“通风的原理”，这就是答非所问。

------

### 第三步：编写自动化评估脚本 (`evaluator.py`)

你可以直接在项目里新建一个 `evaluator.py`，专门用来跑批量的自动化测试。

为了省钱且高效，**强烈建议你使用通义千问的 Qwen-Max 或者直接调用 OpenAI 的 GPT-4o-mini 作为裁判模型**（裁判必须比干活的模型更聪明）。

这里是一个评估脚手架的代码结构，你可以直接拿去用：

Python

```python
import json
import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.chat_models import ChatTongyi
from langchain_core.output_parsers import JsonOutputParser
# 引入你写好的 RagService
from rag import RagService 

# 初始化裁判模型 (必须用最聪明的模型来当裁判，比如 qwen-max)
judge_llm = ChatTongyi(model="qwen-max", temperature=0.0)

# 定义裁判的打分 Prompt
eval_prompt = ChatPromptTemplate.from_messages([
    ("system", """你是一个严苛的 CAE 工程领域评估专家。
请根据以下输入，评估 RAG 系统的表现，并严格输出 JSON 格式。

【评估指标】
1. Faithfulness (1-5分): 回答是否完全基于给定的检索内容，没有编造幻觉？
2. Answer Relevance (1-5分): 回答是否直接解决了用户的问题？

【输入数据】
用户问题: {question}
RAG 检索到的参考资料: {context}
RAG 生成的回答: {answer}
标准参考答案: {ground_truth}

请输出严格的 JSON 格式：
{{
    "faithfulness_score": int,
    "faithfulness_reason": "打分理由",
    "relevance_score": int,
    "relevance_reason": "打分理由"
}}
""")
])

eval_chain = eval_prompt | judge_llm | JsonOutputParser()

def run_evaluation():
    print("🚀 开始执行 RAG 系统自动化评估...")
    rag_engine = RagService()
    
    # 1. 加载测试集
    with open("eval_dataset.json", "r", encoding="utf-8") as f:
        dataset = json.load(f)
        
    results = []
    
    for idx, item in enumerate(dataset):
        print(f"\n--- 正在评估 Case {idx+1}/{len(dataset)} ---")
        question = item["question"]
        ground_truth = item["ground_truth"]
        
        # 2. 让你的 RAG 系统去作答！
        # 注意：你需要稍微改造一下 rag_engine.chain 的输出，让它不仅返回答案，还能把你格式化好的 context 一并返回用于评估
        response = rag_engine.chain.invoke({
            "input": question,
            # 评估时不需要历史记录，传入空列表
            "history": [] 
        }, config={"configurable": {"session_id": f"eval_{idx}"}})
        
        generated_answer = response["answer"]
        retrieved_context = response["context"] # 假设你修改了 pipeline 暴露了 context
        
        print(f"✅ RAG 作答完毕，提交裁判模型打分...")
        
        # 3. 让大模型裁判打分
        try:
            eval_res = eval_chain.invoke({
                "question": question,
                "context": retrieved_context,
                "answer": generated_answer,
                "ground_truth": ground_truth
            })
            
            # 合并结果
            eval_res["question"] = question
            results.append(eval_res)
            
            print(f"得分 -> 忠实度: {eval_res['faithfulness_score']}/5 | 相关性: {eval_res['relevance_score']}/5")
            print(f"裁判点评: {eval_res['faithfulness_reason']}")
            
        except Exception as e:
            print(f"❌ 裁判打分失败: {e}")
            
        time.sleep(1) # 防止 API 触发限流
        
    # 4. 汇总并保存评估报告
    avg_faith = sum(r["faithfulness_score"] for r in results) / len(results)
    avg_rel = sum(r["relevance_score"] for r in results) / len(results)
    
    print("\n" + "="*40)
    print(f"📊 评估完成！总体战报：")
    print(f"平均忠实度 (反幻觉): {avg_faith:.2f} / 5.0")
    print(f"平均相关性 (答准率): {avg_rel:.2f} / 5.0")
    print("="*40)
    
    with open("eval_report.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    run_evaluation()
```

### 💡 你现在的首要任务：

1. **去建数据集**：和工作室的同学一起，每人写 10 个你们觉得有价值的 CAE / 施工装备配置相关的 QA 对，把 `eval_dataset.json` 丰富起来。

2. **暴露 Context**：去你的 `rag.py` 里，稍微调整一下链条最后的输出。把大模型的回答和捞出来的 `context` 打包成一个字典返回（目前你的代码只 `yield` 了最终字符串）。

3. 🚀 破局方案：1 小时的“降维打击”策略

   其实，你完全不需要因为觉得麻烦而退缩。你之所以想推给队友，是因为你潜意识里觉得“做评估需要几千条数据，跑好几天”。

   **在个人/实验室项目中，你只需要花 1 个小时，做一次“微型评估（Micro-Evaluation）”，就能在面试中大杀四方：**

   1. **极其极简的数据集**：不要 50 条，你只需要自己手写 **5 条**最经典的 QA 对（比如 2 条问参数的，2 条问概念的，1 条故意问错的）。
   2. **跑通我给你的脚本**：把这 5 条数据塞进我上一回合给你的 `evaluator.py` 里，一键运行。
   3. **拿到真实的战报**：只需 2 分钟，你就能拿到一个真实的 JSON 报告，比如：“忠实度 4.8，相关性 3.2”。

   **有了这 5 条数据的运行结果，你的面试话术将发生质的飞跃：**

   > **面试完美话术模板：** “在项目后期，我为了量化系统能力，引入了 RAGAS 评估体系的核心思想。我提取了实验室真实的高频问题作为 Ground Truth，写了一个 Python 脚本调用 Qwen-Max 作为裁判模型打分。
   >
   > **我发现了一个非常有意思的现象**（*开始讲真实的 Bad Case*）：系统的召回率很高，但相关性得分只有 3.2 分。我通过排查底层的 Chroma 数据库发现，是因为 Marker 解析 PDF 时把一段表格拆散了，导致大模型回答时抓不到表头。
   >
   > **为了解决这个问题**，我立刻回去修改了系统的切片策略，加入了 `chunk_overlap`，并将重写查询（Query Rewrite）引入了 LangChain 的 LCEL 管道。再次运行评估脚本后，相关性得分直接提升到了 4.5 分。形成了一个完美的优化闭环。”

## 面试模拟

### 1. 核心知识储备：BGE-Reranker 与 RRF

#### 什么是 BGE-Reranker 交叉编码器 (Cross-Encoder)？

在 RAG 的检索阶段，我们通常有两大模型：**双编码器 (Bi-Encoder)** 和 **交叉编码器 (Cross-Encoder)**。

- **双编码器（你的 Chroma 向量库）：** 预先将所有知识库文档分别独立地转化为向量存起来。用户提问时，把问题转化为向量，然后算**余弦相似度**。速度极快，但因为问题和文档是分开编码的，大模型没法理解它们在一起时的细微语境。
- **交叉编码器（BGE-Reranker）：** 它是把用户的 Query 和 某一篇 Document **拼在一起**，作为一个整体输入给模型（例如输入 `[CLS] 问题 [SEP] 文档 [SEP]`），让模型内部的 Transformer 注意力机制去计算问题里的每一个词和文档里的每一个词的关联度。
- **用法总结：** 因为交叉编码器计算量极其庞大，它不能用来对几十万篇文档做全局搜索。它的标准用法是：**二阶段精排**。先用普通的检索（向量/BM25）粗筛出 Top-10 或 Top-20，然后把这 10 个文档连同用户的问题，打包送给 BGE-Reranker 进行逐一打分，最后根据得分重新排序，挑出 Top-3 喂给大模型。

#### RRF (Reciprocal Rank Fusion) 倒数排名融合怎么用？

当我们在系统里同时用了向量检索（查语义相关，比如“形变”匹配“位移”）和 BM25 稀疏检索（查关键词绝对匹配，比如绝对匹配“Drucker-Prager准则”）时，会遇到一个致命问题：**两者打分体系完全不同。** 向量检索的余弦相似度通常在 0 到 1 之间，而 BM25 的得分可能是 10、50 甚至上百。你没法直接把这俩分数加起来排序。

- **RRF 的核心思想：** 抛弃具体分数，**只看排名**。

- **用法与公式：** 将一个文档在各个检索器中的排名代入以下公式：
  $$
  Score(d) = \sum_{r \in R} \frac{1}{k + rank_r(d)}
  $$
  *其中  rank_r(d) 是文档 d 在第 r 个检索器中的排名，常数 k 一般取值为 60。* 只要把两路召回的文档用这个公式算个总分，就能完美融合成一个列表

------

### 2. 模拟面试实战 (Roleplay)

现在，你坐在了我的面前，面试正式开始。你可以将以下我的“预设回答”作为你的背诵模板，我在回答中巧妙地融入了工程实践中的痛点和原理。

> **👨‍💻 面试官 (我):** 看到你的项目中使用了 Chroma 和 BM25 的双路召回，为什么在融合结果的时候选择了 RRF 算法，而不是直接对它们的分数做加权归一化？

**🗣️ 候选人 (你):**

面试官您好。不选择直接加权归一化的主要原因是：**Dense 检索（向量）和 Sparse 检索（BM25）的分数分布差异极大，且非线性。**

向量检索的余弦相似度通常集中在 0.6 到 0.9 之间，波动范围很小；而 BM25 的得分是没有上限的，受长文档词频影响很大，可能跨度从几分到几百分。如果我们用简单的 Min-Max 归一化，一旦 BM25 出现一个极端高分，其他所有文档的 BM25 归一化分数都会被压扁趋近于 0，导致融合失效。

而 RRF 算法彻底抛弃了绝对分数，直接利用**排名的倒数**进行融合。这是一种无需训练的启发式算法，不管底层检索器的打分逻辑多么天差地别，RRF 都能给出一个相对平滑且公平的综合排序。

> **👨‍💻 面试官 (我):** 很好。那么在 RRF 的公式里，为什么分母通常要加一个常数 $k=60$，直接用 $1/rank$ 不行吗？

**🗣️ 候选人 (你):**

加上常数 $k$ 是为了**削弱“单一检索器排名第一”的绝对统治力**。

如果直接用 $1/rank$，排名第 1 的文档得分是 1，排名第 2 的得分是 0.5。这意味着第一名比第二名重要了整整一倍，权重衰减太剧烈了。

引入常数（比如 60）后，第一名是 $1/61$，第二名是 $1/62$，分数差距被大幅缩小。这样做的工程意义在于：一个文档只有在**多个检索器中都排名靠前**，它的总分才会高，从而避免了某个文档只是因为命中了冷僻词而在 BM25 排第一，就被错误地顶到最终结果的首位。

> **👨‍💻 面试官 (我):** 理解得很透彻。既然经过 RRF 融合后，文档已经排好序了，为什么后面还要再接一个 BGE-Reranker？这会不会增加系统的延迟？

**🗣️ 候选人 (你):**

确实会增加一部分延迟，但为了最终回答的准确性，这是非常必要的折中。

因为双路召回和 RRF 本质上还是**“粗排”**。向量检索采用的是 Bi-Encoder 架构，它计算相似度时，查询词和文档在底层是没有交互的；BM25 更是纯基于字面频率。而真实场景下的工程仿真问题往往包含了复杂的因果关系或条件限定。 BGE-Reranker 是基于 Cross-Encoder 架构的。它将用户的 Query 和召回的文档拼接在一起共同输入给 Transformer，能够利用强大的自注意力机制实现**词级别的深度交叉语义理解**。

为了控制延迟，我只将 RRF 融合后的 Top-10 候选文档送给 BGE-Reranker 进行重排。这样既保证了召回率，又利用较小的计算开销大幅提升了最终 Top-3 喂给 LLM 的上下文精准度，有效压制了幻觉。

> **👨‍💻 面试官 (我):** 那么如果在重排阶段，BGE-Reranker 报错或者超时了，你的系统会怎么处理？有兜底机制吗？

**🗣️ 候选人 (你):**

在实际工程中我会加入超时熔断机制。如果 BGE-Reranker 服务响应超时（例如超过 1.5 秒），或者显存溢出报错，代码会自动捕获异常，并直接将 RRF 粗排阶段融合出的 Top-K 结果作为兜底返回给大模型。虽然精度可能略有下降，但保证了整个系统的可用性，不会让前端智能客服出现死机或长久卡顿。

> **👨‍💻 面试官 (我):** 为什么要进行Query改写？

**🗣️ 候选人 (你):**

解决“语义鸿沟”，用户倾向于使用简短、模糊的口语，而知识库通常是详实、专业的书面语。改写能对齐两者的表达空间；消除“意图模糊”，原始Query往往缺失背景，改写通过引入上下文，江模糊的提问转化为具体、可检索的声明式描述；关联“历史信息”，在多轮对话中，用户常使用代词，改写能完成指代消解，确保每一轮检索都精准无误。

**2. 挡不住大厂的“穿透式提问”** 就算你强行把评估写在简历上，打算靠“背诵理论”蒙混过关，面试官只需两个真实的工程问题就能把你问穿：

- “你们用大模型做裁判时，**遇到过最大的 Bad Case（误判）是什么**？你们是怎么修改 Prompt 让裁判变聪明的？”
- “你们跑完评估后，发现 Context Precision（精度）和 Context Recall（召回率）分别是多少？**针对这个较低的数据，你具体改了代码里的哪行配置？** 效果提升了多少？” 如果你没有真正跑过那段脚本，看到过真实的 JSON 报错和离谱的分数，你绝对编不出真实的 Bad Case，一旦卡壳，整个项目的真实性都会被画上问号。

#### 🥚 第一层：直击痛点（产品与体验层）

**🗣️ 面试官可能问：** > “大模型的 API 直接返回一个完整的字符串不香吗？为什么要费劲去做流式输出？”

**💡 你该怎么答：**

- **核心词汇：首字响应时间 (TTFT - Time To First Token) 与白屏焦虑。**
- **回答策略：** “大模型的底层机制是自回归（Auto-regressive）的，也就是逐个 Token 往外吐。在复杂的 RAG 或工程计算场景中，模型生成完整回答可能需要好几秒甚至十几秒。如果不使用流式输出，用户会面临漫长的‘白屏等待’，以为系统卡死了。流式输出能让前端‘边接收边渲染’，极大地降低了首字响应时间 (TTFT)，用视觉上的动态效果掩盖了底层的推理延迟，这是大语言模型应用最基础的体验底线。”

#### 🧅 第二层：原理解析（代码与网络层）

**🗣️ 面试官可能问：**

> “在你的项目中，流式输出在前后端是怎么实现的？如果不用 Streamlit 这种封装好的框架，让你用 FastAPI 写一个后端，你会用什么协议？”

**💡 你该怎么答：**

- **核心词汇：Python 生成器 (`yield`)、SSE 协议 (Server-Sent Events)。**
- **回答策略：** “在目前的 Python 代码中，LangChain 的 `.stream()` 底层其实是返回了一个**生成器 (Generator)**，也就是不断地 `yield` 出文本片段。前端的 `st.write_stream` 就像一个迭代器去消费它。
- **拓展展现深度：** “如果未来项目是前后端分离的（比如 Vue/React + FastAPI），我会使用 **SSE (Server-Sent Events)** 协议。因为流式文本本质上是单向推送（服务器推给客户端），不需要 WebSocket 那样的全双工通信，SSE 基于标准 HTTP 协议，利用 `Transfer-Encoding: chunked`（分块传输编码），实现起来更轻量也更稳定。”

#### 🌰 第三层：实战排坑（架构与 Agent 层）—— 🌟 决胜局！

**🗣️ 面试官可能问：**

> “流式输出在结合多轮对话，或者结合 Agent（智能体）调用工具时，会遇到什么技术难点？你是怎么处理的？”

**💡 你该怎么答（结合你的系统特点）：**

- **痛点 1：历史状态断层。** “流式输出是一截一截的碎片，如果不做处理，大模型回答完之后，前端的对话历史里根本没有这句完整的话。所以必须在前端用一个变量（比如我用的 `full_response`）把水管里流出来的所有水滴拼接起来，等流式结束后，再统一 `append` 到 session 状态里落盘，保证上下文的连贯。”
- **痛点 2：Agent 思考过程的过滤。** “在做复杂任务（比如基于 LangGraph 做自动化调度节点）时，Agent 的运行是分阶段的。它可能会先输出调用了某个 API（比如查询装备库），拿到结果后再思考。这时的流式数据不仅有最终的‘聊天文本’，还有‘工具调用的 JSON 结构’。这就需要在流式输出时加上**事件过滤器**（比如解析 LangChain 的 `astream_events`），屏蔽掉后端的机器代码，只把面向用户的自然语言 `yield` 给前端。”

### 1. 技术选型的 Trade-off (权衡) 能力

面试官会问：“既然 Marker 这么慢，你当时为什么不选速度更快的传统 OCR（比如 PaddleOCR）或者 PyMuPDF？”

- **满分回答逻辑：** “因为在 CAE 仿真手册这个特定场景下，**数据质量的优先级远高于离线处理速度**。传统 OCR 对无边框公式和嵌套表格的解析极其糟糕，会导致入库的文本全是乱码。如果源头数据就是错的，后面的检索和 LLM 生成再快也是‘垃圾进，垃圾出’ (Garbage In, Garbage Out)。所以我宁愿牺牲离线阶段的解析速度，利用视觉大模型来换取极高的 Markdown/LaTeX 重构精度，从而保证最终 RAG 的问答质量。”

### 2. 工程架构的解耦与设计能力

面试官会问：“那解析这么慢，如果用户上传了一份 500 页的手册，系统卡死了怎么办？”

- **满分回答逻辑：** “在架构设计上，我将系统严格分为了**‘离线数据处理流’**和**‘在线问答检索流’**（这正好对应你画的左右两边）。Marker 的慢只存在于离线端。在工程落地时，我会采用异步任务队列（如 Celery）来处理文档解析，用户上传后立即返回‘解析中’状态，后台慢慢跑。而用户的在线提问走的是向量检索和 LLM，这部分可以做到毫秒级或秒级响应，完全不受 Marker 速度的影响。”

### 3. 深入垂直领域的定制能力 (你的杀手锏)

面试官其实最感兴趣的是你简历里写的这句话：**“针对CAE场景自定义公式保护策略”**。

- 开源大模型谁都会调，但只有你真正懂土木/桥隧/CAE 领域的痛点。你发现了通用分块方法会把 `\n$$\n` 这种长公式切断导致语义丢失，并且你写代码提升了它的切分优先级，把公式完整地保护了下来。**这叫“基于业务场景的深度优化”，这才是面试官最看重的工程落地能力。**

### 项目背景板块

------

#### 1. 明确项目定位：不是商业产品，是“教研室内部生产力工具”

面试时，大方地承认这个系统目前部署在本地或实验室局域网。

**话术参考：**

> “受限于个人的算力和服务器资源，这个 RAG 引擎目前主要作为我个人以及教研室内部的**效率验证原型（POC）**在本地运行，并没有对外网开放公测。目前的重点还是打磨检索精度和针对 CAE 复杂公式的解析能力，后续实习如果有充足的资源，再考虑服务化和工程化部署。”

这样说，面试官不仅不会觉得系统“水”，反而会觉得你非常务实，懂边界，没有眼高手低。

#### 2. 完美包装“项目由来”：从痛点出发，而不是“导师分派”

千万不要说“导师让我做个 RAG”。面试官喜欢看的是**“自驱力”**——你发现了问题，并用 AI 技术解决了问题。你可以把你目前的研究课题作为背景板，顺理成章地引出这个工具。

**面试官问：“这个项目的背景是什么？怎么想到要做这个的？”** **话术参考：**

> “这个项目的灵感来源于我平时做课题时的切身痛点。我在推进关于藏区公路隧道开挖支护智能化决策与装备配置的研究时，需要大量依赖像 FLAC3D、Abaqus 这类专业的 CAE 软件进行数值模拟。
>
> 但这些软件的官方手册和技术规范动辄几千页，里面全是复杂的参数代号、嵌套表格和力学公式。传统的 Ctrl+F 或者普通的搜索引擎根本查不到带有复杂排版的特定模型公式，导致我和同门在查阅资料上浪费了大量时间。
>
> 刚好我一直在关注大模型和 RAG 技术，我就想，为什么不自己搭一个专门针对我们土木/CAE 领域的智能知识库呢？所以我就以解决这个实际的查阅痛点为初衷，发起了这个项目。”

这套话术简直无懈可击：既展现了你**懂具体的业务场景（工程痛点）**，又展现了你的**技术自驱力**。

#### 3. 定义你的角色：从 0 到 1 的独立开发者

在这个 RAG 项目中，你的角色不应该是“参与者”，而必须是**“发起者和核心开发者”**。

**话术参考：**

> “在这个项目中，我是唯一的独立开发者。从最开始的痛点调研，到左侧的数据清洗、Marker 离线高精度解析管道的设计，再到右侧 Chroma 向量库的搭建、双路召回的检索策略（RRF算法），以及最后通过 LangChain 组装 LLM 提示词链，整个从 0 到 1 的核心引擎全链路都是由我独立设计并代码实现的。”

#### 4. 如果被问到“导师的项目”，如何巧妙切换？

有时候面试官可能会好奇你的研究生正职工作，问：“那你导师的具体项目是什么？和这个 RAG 有什么关系？”

这时候，你需要把宏观的**“工程决策研究”**和微观的**“AI 工具开发”**区分开，把 RAG 描述为你为了更好地完成科研任务而打造的**“基础设施”**。

**话术参考：**

> “我导师的宏观项目是关于复杂地质下隧道施工的智能化决策与调度。在这个大课题中，我们需要处理海量的地质勘探规则、施工规范和数值仿真结果。
>
> 这个 RAG 引擎可以理解为我为了更好地支撑大课题而研发的‘底层知识底座’。比如，通过我做的这个高精度检索系统，我们可以更快速、准确地从规范中提取支护参数，作为后续辅助智能决策系统的输入。RAG 项目是我个人主导的技术探索，它极大地提升了我们在主干课题上的研究效率。”

## 代码源文件 CAE_RAG_project

### app.py

```python
import streamlit as st  # 构建简易的前端网页
import uuid  # 引入 uuid 生成唯一标识
from rag import RagService # 引入写好的 RagService 类串联整个流程
from file_history_store import get_history # 引入从文件中读取历史记录的函数

st.set_page_config(page_title="CAE 仿真专家助手", layout="wide")
st.title("🛠️ CAE 智能客服与文档助手")
st.divider()  # 添加分隔线

# 👇 全局初始化 RagService 实例，仅首次加载时执行
@st.cache_resource(show_spinner="正在全局初始化大模型引擎与知识库...")
def init_rag_engine():
    return RagService()
rag_engine = init_rag_engine() # 👈 初始化 RagService 实例

# 👇 为当前用户（浏览器标签页）生成唯一的 session_id
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4()) # 例如：'e3b0c442-989b-464c-8693-...'

# 👇 初始化当前用户的聊天记录（如果不存在）
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": "你好，我是专注于 CAE 领域的智能客服。请问有什么工程仿真方面的问题可以帮助你？"}]

with st.sidebar:
    st.header("⚙️ 系统管理")
    if st.button("🔄 同步最新知识库"):
        with st.spinner("正在对齐稀疏索引与向量库数据..."):
            rag_engine.retriever_service.sync_bm25_from_chroma()
            st.success("同步完成！检索器已就绪。")

    if st.button("🗑️ 清空当前对话"):
        history = get_history(st.session_state["session_id"])
        history.clear()
        st.session_state["messages"] = [{"role": "assistant", "content": "对话已清空，让我们重新开始吧！\n\n 你好，我是专注于 CAE 领域的智能客服。请问有什么工程仿真方面的问题可以帮助你？"}]
        st.rerun()

# 渲染历史聊天记录
for message in st.session_state["messages"]:
    st.chat_message(message["role"]).write(message["content"])

# 👇 处理用户输入
prompt = st.chat_input("在这里输入你的问题，例如：在 Abaqus 中材料屈服强度参数应该如何设置？")
if prompt:
    st.chat_message("user").write(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("🧠 正在进行多路召回与交叉重排..."):
            
            # 动态构造属于当前用户的 config，覆盖掉全局的 session_id
            user_config = {
                "configurable": {
                    "session_id": st.session_state["session_id"]
                }
            }
            # 把专属 config 传给大模型，这样 LangChain 就会自动去文件里找属于这个 UUID 的记录，并完成流式输出
            res_stream = rag_engine.chain.stream(
                {"input": prompt}, 
                user_config 
            )
            full_response = st.write_stream(res_stream)                   
    st.session_state["messages"].append({"role": "assistant", "content": full_response})
```

### file_uploader.py

```python
import streamlit as st
import os
import subprocess
import shutil

# --- 页面配置 ---
st.set_page_config(page_title="CAE 知识库批量更新", page_icon="📚", layout="wide")
st.title("📚 CAE 专属知识库批量更新控制台")
st.markdown("支持**多文件同时上传** (PDF / Markdown)，系统将自动排队、深度解析并注入大模型知识库。")

# --- 1. 定义工作目录 ---
BASE_DIR = "G:/vscode/LangChain_Project/CAE_RAG_project" # 部署到服务器时，请确保修改为服务器的绝对路径！
TEMP_UPLOAD_DIR = os.path.join(BASE_DIR, "temp_uploads") 
MARKER_OUTPUT_DIR = os.path.join(BASE_DIR, "marker_output") 

for d in [TEMP_UPLOAD_DIR, MARKER_OUTPUT_DIR]:
    os.makedirs(d, exist_ok=True)

# ==========================================
# 🌟 全局缓存锁 (懒加载)
# ==========================================
@st.cache_resource(show_spinner=False)
def get_kb_service():
    from knowledge_base import KnowledgeBaseService 
    return KnowledgeBaseService()

# --- 2. 多文件上传组件 ---
# 定义一个企业级全局常量
MAX_FILES_LIMIT = 10 

uploaded_files = st.file_uploader(
    f"请将需要入库的 CAE 文献拖拽至此处 (支持 pdf/md，单次最多允许 {MAX_FILES_LIMIT} 个)", 
    type=["pdf", "md"],
    accept_multiple_files=True 
)

if uploaded_files:
    total_files = len(uploaded_files)
    
    # ==========================================
    # 🚨 核心风控：数量超限拦截器
    # ==========================================
    if total_files > MAX_FILES_LIMIT:
        # 显示刺眼的红色错误提示，要求用户手动删减
        st.error(f"❌ 队列超载！您当前选中了 **{total_files}** 个文件，系统单次最多支持处理 **{MAX_FILES_LIMIT}** 个。")
        st.warning("👉 请点击上方文件列表右侧的 'X' 移除多余的文档，以解锁入库功能。")
        
        # 此时代码运行结束，底下的“开始处理”按钮根本不会被渲染出来，彻底阻断执行！
        
    else:
        # 如果数量合规，正常走后面的流程
        total_size_mb = sum([f.size for f in uploaded_files]) / (1024 * 1024)
        st.info(f"📁 待处理队列合规：共 **{total_files}** 个文件，总大小 **{total_size_mb:.2f} MB**")

        # --- 3. 批量处理主逻辑 (一键托管模式) ---
        if st.button("🚀 开始批量解析与入库", type="primary"):        
            with st.spinner("⏳ 正在唤醒大模型与向量数据库引擎..."):
                kb_service = get_kb_service()

            progress_bar = st.progress(0.0, text="准备启动批处理队列...")
            st.markdown("### 📝 实时执行日志")
            log_container = st.container(height=450) # 固定高度面板，保持页面整洁
        
            stats = {"success": 0, "skip": 0, "error": 0}
            error_details = []

            # ==========================================
            # 🔄 开启文件遍历流水线
            # ==========================================
            for index, file in enumerate(uploaded_files):
                file_name = file.name
                file_type = file_name.split(".")[-1].lower()
                base_name = os.path.splitext(file_name)[0]
            
                # 刷新总体进度条
                current_progress = (index) / total_files
                progress_bar.progress(current_progress, text=f"正在处理 ({index+1}/{total_files}): {file_name}")
            
                if index > 0:
                    log_container.markdown(f"---")
                log_container.write(f"▶️ **开始处理文档 [{index+1}/{total_files}]:** `{file_name}`")
            
                temp_file_path = os.path.join(TEMP_UPLOAD_DIR, file_name)
                marker_folder_path = os.path.join(MARKER_OUTPUT_DIR, base_name)
                marker_md_path = os.path.join(marker_folder_path, f"{base_name}.md")
                parsed_text = None
            
                try:
                    # 步骤 1：落地临时文件
                    with open(temp_file_path, "wb") as f:
                        f.write(file.getvalue())

                    # 步骤 2：解析文件
                    if file_type == "md":
                        with open(temp_file_path, "r", encoding="utf-8") as f:
                            parsed_text = f.read()
                        log_container.write("✅ Markdown 读取成功")
                    
                    elif file_type == "pdf":
                        log_container.write("🧠 正在调用 Marker 提取 PDF 内容与公式...")
                        command = ["marker_single", temp_file_path, "--output_dir", MARKER_OUTPUT_DIR]
                    
                        # 融合你的绝佳设计：流式截断监听 Marker 进程，防止前端卡死！
                        process = subprocess.Popen(
                            command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                            text=True, bufsize=1, encoding="utf-8", errors="replace"
                        )
                    
                        for line in process.stdout:
                            print(line.replace("\ufffd", "█"), end="", flush=True) # 后台终端依然保留全量日志
                        
                        process.wait()
                    
                        if process.returncode == 0 and os.path.exists(marker_md_path):
                            with open(marker_md_path, "r", encoding="utf-8") as f:
                                parsed_text = f.read()
                            log_container.write("✅ PDF 深度解析成功")
                        else:
                            raise Exception("Marker 解析失败或未生成预期文件")

                    # 步骤 3：提交入库
                    if parsed_text:
                        log_container.write("⚙️ 正在切片并调用大模型向量化...")
                        # 利用你写好的对讲机机制，把进度实时打在滚动面板上
                        result = kb_service.upload_by_str(parsed_text, file_name, progress_callback=log_container.write)
                    
                        if "[成功]" in result:
                            stats["success"] += 1
                            log_container.success(f"🎉 入库完成：{result}")
                        elif "[跳过]" in result:
                            stats["skip"] += 1
                            log_container.warning(f"⏭️ 发现重复：{result}")
                        else:
                            raise Exception(result)

                except Exception as e:
                    # 异常隔离：记录失败，继续跑下一篇
                    stats["error"] += 1
                    error_msg = f"❌ '{file_name}' 处理失败: {str(e)}"
                    log_container.error(error_msg)
                    error_details.append(error_msg)
                
                finally:
                    # 步骤 4：仅清理用户上传的原始临时文件，保留 Marker 产出的宝贵资产！
                    log_container.write("🧹 正在清理当前上传的临时文件...")
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

            # ==========================================
            # 🏁 批处理结束，展示最终战报
            # ==========================================
            progress_bar.progress(1.0, text="✅ 队列处理完毕！")
        
            st.markdown("### 📊 批量入库战报")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("总计提交", f"{total_files} 份")
            col2.metric("✅ 成功入库", f"{stats['success']} 份")
            col3.metric("⏭️ 跳过重复", f"{stats['skip']} 份")
            col4.metric("❌ 解析失败", f"{stats['error']} 份")
        
            if error_details:
                with st.expander("查看失败详情"):
                    for err in error_details:
                        st.error(err)
```

### knowledge_base.py

```python
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_core.documents import Document # 需要引入 Document 对象
import hashlib
import os
import config_data as config
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 环境变量
load_dotenv()

# 确保 API Key 存在
api_key = os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("未找到 DASHSCOPE_API_KEY，请检查 .env 文件配置")


def check_md5(md5_str: str) -> bool:
    """检查传入的md5字符串是否已经被处理过了"""
    # 确保父目录存在
    md5_dir = os.path.dirname(config.md5_path)
    if md5_dir:
        os.makedirs(md5_dir, exist_ok=True)
        
    if not os.path.exists(config.md5_path):
        with open(config.md5_path, "w", encoding="utf-8") as f:
            pass # 创建空文件
        return False
        
    # 使用 with 确保文件正确关闭
    with open(config.md5_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() == md5_str:
                return True
    return False

def save_md5(md5_str: str):
    """将传入的md5字符串记录到文件内保存"""
    with open(config.md5_path, "a", encoding="utf-8") as f:
        f.write(md5_str + "\n")
    
def get_string_md5(input_str: str, encoding='utf-8') -> str:
    """将传入的字符串转换为md5字符串"""
    md5_obj = hashlib.md5()
    md5_obj.update(input_str.encode(encoding=encoding))
    return md5_obj.hexdigest()

class KnowledgeBaseService:
    def __init__(self):
        os.makedirs(config.persist_directory, exist_ok=True)
        
        # 初始化向量模型 (使用阿里云 DashScope)
        self.embeddings = DashScopeEmbeddings(model="text-embedding-v4")
        
        # 初始化 Chroma 向量库
        self.chroma = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embeddings,
            persist_directory=config.persist_directory,
        )
        
        # 🔪 武器库 1：Markdown 结构手术刀 (专治 PDF 和 MD 文件)
        headers_to_split_on = [
            ("#", "Header_H1"),
            ("##", "Header_H2"),
            ("###", "Header_H3"),
        ]
        self.md_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False
        )

        # 🔪 武器库 2：字符长度切片刀 (保底防爆仓)
        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            separators=config.separators,
        )   

    def upload_by_str(self, data: str, filename: str, progress_callback=None) -> str:
        """将传入的字符串（从PDF/Markdown文件提取的文本）上传到知识库中"""
        # 定义一个内部的小喇叭函数，方便调用
        def report(msg):
            if progress_callback:
                progress_callback(f"\n{msg}\n")

        # 1. 安全校验：防止空数据入库
        if not data or not data.strip():
            return f"[失败] '{filename}' 提取到的文本为空，无法上传向量库"

        # 2. 生成 MD5 并查重
        md5_hex = get_string_md5(data)
        if check_md5(md5_hex):
            return f"[跳过] 文件 '{filename}' 的内容已存在知识库中"
        
        # 判断文件后缀，决定切片策略
        file_ext = filename.split(".")[-1].lower()
        report("✂️ **1. 正在进行文档切片...**")

        # 3. 拆分文本流获取 Documents 对象
        # 因为系统限制了输入源为 MD 或转化后的 MD，直接统一使用 Markdown 结构化切片 + 字符切片兜底
        print(f"[{filename}] 触发结构化切片管道...")
        md_docs = self.md_splitter.split_text(data)
        # 二次切分：防止某个标题下的段落超过 chunk_size
        final_docs = self.char_splitter.split_documents(md_docs)

        report(f"✅ 切片完成！共切分出 `{len(final_docs)}` 个片段")

        # 4. 重组 Texts 和 Metadatas
        knowledge_chunks = []
        metadatas = []
        
        for i, doc in enumerate(final_docs):
            knowledge_chunks.append(doc.page_content)
            
            # 继承 Markdown 切分器提取到的标题层级（如果有的话）
            meta = doc.metadata.copy() 
            # 补充我们系统的通用元数据
            meta.update({
                "source": filename,
                "create_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "operator": "user",
                "chunk_index": i
            })
            metadatas.append(meta)
        report("🧠 **2. 正在生成多维向量特征并存入 Chroma...**")
        # 6. 写入 Chroma 数据库
        self.chroma.add_texts(
            texts=knowledge_chunks,
            metadatas=metadatas
        )
        report(f"✅ 向量化与入库完成！")
        save_md5(md5_hex)
        return f"[成功] '{filename}' 已切分为 {len(knowledge_chunks)} 个片段并入库"


if __name__ == "__main__":
    # 测试代码
    try:
        service = KnowledgeBaseService()
        r = service.upload_by_str("这是一个集成测试字符串", "test_file.txt")
        print(r)
    except Exception as e:
        print(f"初始化或上传失败: {e}")
```

### retriever_service.py

```python
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import jieba # 导入 jieba 分词库，用于中文文本的分词
from rank_bm25 import BM25Okapi # 导入 BM25 算法，用于文本检索和排名
from sentence_transformers import CrossEncoder # 导入 BGE-Reranker 模型，用于文本重排序
from langchain_chroma import Chroma
from langchain_core.documents import Document
import config_data as config
from langchain_community.embeddings import DashScopeEmbeddings
from dotenv import load_dotenv
load_dotenv()

# 👇 定义混合检索器服务类
class HybridRetrieverService:
    def __init__(self, embedding):
        print("\n" + "="*50)
        print("🚀 初始化混合检索引擎 (Chroma Vector + BM25 Sparse + Reranker)")
        
        # 1. 挂载已有的 Chroma 向量数据库
        self.embedding = embedding
        self.vector_store = Chroma(
            collection_name=config.collection_name,
            embedding_function=self.embedding,
            persist_directory=config.persist_directory,
        )
        # 2. 构建 BM25 索引
        self.bm25 = None
        self.chunks = []
        self.sync_bm25_from_chroma()
        # 3. 初始化重排序引擎
        print("🧠 正在加载 BGE-Reranker 交叉编码重排序模型...")
        self.reranker = CrossEncoder('BAAI/bge-reranker-base')
        print("="*50 + "\n")

    #  👇 同步 Chroma 向量库到 BM25 索引
    def sync_bm25_from_chroma(self):
        """
        核心桥接逻辑：从 Chroma 中提取所有切片文本，实时构建 BM25 词频索引。
        """
        print("📚 正在从 Chroma 向量库同步数据构建 BM25 索引...")
        try:
            db_data = self.vector_store.get() 
            
            # 严格检查空数据，防止冷启动崩溃
            if not db_data or not db_data.get('documents'):
                print("⚠️ 当前向量库为空，暂不构建 BM25 索引。")
                self.bm25 = None
                self.chunks = []
                return
            self.chunks = [
                Document(page_content=txt, metadata=meta) 
                for txt, meta in zip(db_data['documents'], db_data['metadatas'])
            ]

            # 使用 jieba 对文档内容进行分词，用于 BM25 索引
            tokenized_corpus = [list(jieba.cut_for_search(doc.page_content)) for doc in self.chunks]
            # 确保语料库不为空才初始化 BM25
            if tokenized_corpus:
                self.bm25 = BM25Okapi(tokenized_corpus)
                print(f"✅ BM25 索引构建完毕，共计 {len(self.chunks)} 个文档切片。")
            else:
                self.bm25 = None
                
        except Exception as e:
            print(f"❌ 构建 BM25 索引时发生错误: {e}")
            self.bm25 = None
            self.chunks = []

    #  👇 双路召回与 RRF 融合
    def _hybrid_retrieve(self, query: str, top_k: int = 10, rrf_k: int = 60) -> list[Document]:
        """第一阶段：双路召回与 RRF 融合"""
        # --- 路线 A：Chroma 向量检索 ---
        dense_results = self.vector_store.similarity_search(query, k=top_k)
        
        # --- 路线 B：BM25 关键词检索 ---
        # 安全熔断：如果没有 BM25 索引，直接返回向量检索结果，不再执行 RRF
        if not self.bm25 or not self.chunks:
            print("⚠️ 未发现 BM25 索引，自动降级为纯向量检索。")
            return dense_results 
        tokenized_query = list(jieba.cut_for_search(query)) # 对查询进行分词
        bm25_scores = self.bm25.get_scores(tokenized_query) # 计算 BM25 得分
        bm25_top_indices = sorted(range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True)[:top_k] # 取 BM25 得分最高的 top_k 个文档索引
        sparse_results = [self.chunks[i] for i in bm25_top_indices] # 从 BM25 索引中提取 top_k 个文档

        # --- 路线 C：RRF (倒数排名融合) ---
        fused_scores = {}
        # (1)Chroma 向量检索的 RRF 贡献
        for rank, doc in enumerate(dense_results):
            doc_key = doc.page_content 
            if doc_key not in fused_scores:
                fused_scores[doc_key] = {"doc": doc, "score": 0.0}
            fused_scores[doc_key]["score"] += 1.0 / (rrf_k + rank + 1)
        # (2)BM25 关键词检索的 RRF 贡献
        for rank, doc in enumerate(sparse_results):
            doc_key = doc.page_content
            if doc_key not in fused_scores:
                fused_scores[doc_key] = {"doc": doc, "score": 0.0}
            fused_scores[doc_key]["score"] += 1.0 / (rrf_k + rank + 1)
        # (3)按 RRF 得分降序并截取
        reranked_results = sorted(fused_scores.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in reranked_results[:top_k]]

    #  👇 重排序
    def search_and_rerank(self, query: str, initial_k: int = 10, final_k: int = 3) -> list[Document]:
        """第二阶段：调用此方法执行完整的 RAG 检索链路"""
        print(f"🔍 [阶段 1] 混合检索召回前 {initial_k} 个片段...")
        initial_docs = self._hybrid_retrieve(query, top_k=initial_k)
        if not initial_docs:
            return []

        print(f"⚖️ [阶段 2] BGE-Reranker 进行深度交叉语义打分...")
        cross_inp = [[query, doc.page_content] for doc in initial_docs]
        scores = self.reranker.predict(cross_inp)
        # 绑定得分并排序
        scored_docs = list(zip(initial_docs, scores))
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        print(f"🎯 [阶段 3] 优中选优，输出最终的 Top-{final_k}！")
        # 只要文档，剔除分数，方便后续 LangChain 调用
        final_docs = [doc for doc, score in scored_docs[:final_k]]
        return final_docs


if __name__ == "__main__":   
    # 初始化嵌入模型和检索服务
    embedding = DashScopeEmbeddings(model="text-embedding-v4")
    retriever_service = HybridRetrieverService(embedding)
    
    # 执行混合检索 + 重排序
    query_text = "什么是有限元分析？"
    results = retriever_service.search_and_rerank(query_text, initial_k=10, final_k=3)
    
    print("\n📝 最终检索结果：")
    for i, doc in enumerate(results):
        print(f"[{i+1}] 来源: {doc.metadata.get('source', '未知')} | 内容: {doc.page_content[:50]}...")
```

### file_history_store.py

```python
import json
import os
from langchain_core.messages import BaseMessage, message_to_dict, messages_from_dict
from langchain_core.chat_history import BaseChatMessageHistory
from typing import Sequence

def get_history(session_id):
    return FileChatMessageHistory(session_id, "./chat_history")

class FileChatMessageHistory(BaseChatMessageHistory):
    def __init__(self, session_id, storage_path):
        self.session_id = session_id
        self.storage_path = storage_path
        self.file_path = os.path.join(self.storage_path, self.session_id)
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

    @property
    def messages(self) -> list[BaseMessage]:
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                messages_data = json.load(f)
                return messages_from_dict(messages_data)
        except FileNotFoundError:
            return []
        
    def add_message(self, message: Sequence[BaseMessage]) -> None:
        all_messages = self.messages
        all_messages.append(message)
        new_messages = [message_to_dict(message) for message in all_messages]
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(new_messages, f)
    def clear(self) -> None:
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump([], f)
```

### rag.py

```python
from retriever_service import HybridRetrieverService # 导入写好的混合检索器
from langchain_community.embeddings import DashScopeEmbeddings # 导入阿里百炼 DashScope 嵌入模型
from langchain_community.chat_models import ChatTongyi # 提供阿里通义千问大语言模型的接口
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder # 构建聊天格式的提示模板, 创建消息占位符用于动态插入对话历史
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory 
from file_history_store import get_history # 导入历史记录管理模块
import config_data as config
import os
from dotenv import load_dotenv
load_dotenv()

def print_prompt(prompt):
    print("="*20 + " 最终发给大模型的 Prompt " + "="*20)
    print(prompt.to_string())
    print("="*60)
    return prompt

def print_rewritten_query(query):
    print(f"\n✨ [查询重写] 原始提问已被大模型优化为检索词: 【 {query} 】\n")
    return query

# 👇 定义智能 RAG 服务类
class RagService(object):
    def __init__(self):
        print("🤖 正在初始化智能 RAG 核心服务...")
        
        # 1. 接入混合检索器 (Chroma + BM25 + BGE Reranker)
        self.retriever_service = HybridRetrieverService(
            embedding=DashScopeEmbeddings(model=config.embedding_model)
        )

        # 2. 初始化大模型 (这个模型会被 QA 和 重写 共用)
        self.chat_model = ChatTongyi(model=config.chat_model, temperature=0.1)

        # 3. 构造重写专门的 Prompt
        contextualize_q_system_prompt = (
            "你是一个专业的 CAE 工程仿真搜索词优化专家。"
            "给定下面的聊天历史记录和最新的用户提问，"
            "该问题可能依赖于历史对话的上下文才能看懂（比如使用了代词或省略了主语）。"
            "请结合历史，把最新的问题重写为一个独立、完整、包含专业术语的搜索词，以便于在向量数据库中进行精准检索。"
            "如果原问题不需要重写，请原样返回。"
            "**绝对禁止回答问题，只输出重写后的确切句子！**"
        )
        self.rewrite_prompt = ChatPromptTemplate.from_messages([
            ("system", contextualize_q_system_prompt),
            MessagesPlaceholder("history"), # 动态注入的历史记录
            ("human", "最新提问：{input}")
        ])

        # 4. 构造专家级 QA Prompt
        self.qa_prompt_template = ChatPromptTemplate.from_messages([
            ("system", 
             "你是一个严谨的 CAE 领域仿真工程专家。请仔细阅读以下【参考资料】，并根据资料内容专业、准确地回答用户的提问。\n\n"
             "回答要求：\n"
             "1. 主要基于参考资料中的信息进行回答。\n"
             "2. 对于表格或离散数据，允许结合常见的工程或常识背景进行合理的逻辑推理。”\n"
             "3. 如果实在无法推断，再回答：“抱歉，根据现有的知识库，暂无法解答该问题。\n\n"
             "【参考资料】:\n{context}"), 
            ("system", "以下是与用户的近期对话历史："),
            MessagesPlaceholder("history"),
            ("user", "【用户提问】: {input}")
        ])
        
        # 5. 构建 LCEL 链
        self.chain = self.__get_chain()

    def __get_chain(self):
        
        # 构建重写链条 (Prompt -> LLM -> String)
        rewrite_chain = self.rewrite_prompt | self.chat_model | StrOutputParser() | print_rewritten_query

        # 包装检索方法，适配 LangChain 的管道
        def perform_retrieval(rewritten_query: str) -> list[Document]:
            # 调用重排序混合检索，召回 10 个，最终保留 3 个
            return self.retriever_service.search_and_rerank(rewritten_query, initial_k=10, final_k=3)

        # 格式化文档输出，用于 Prompt 模板
        def format_document(docs: list[Document]):
            if not docs:
                return "没有找到相关的参考资料。"
            formatted_str = ""
            for i, doc in enumerate(docs):
                source = doc.metadata.get('source', '未知文档')
                header = doc.metadata.get('Header_H1', '') or doc.metadata.get('Header_H2', '')
                tag = f"来源: {source}" + (f" | 章节: {header}" if header else "")
                formatted_str += f"[参考资料 {i+1}] ({tag})\n{doc.page_content}\n\n"
            return formatted_str

        # 构建 QA 基础链条
        base_chain = (
            RunnablePassthrough.assign(
                # 第一步：把 input 和 history 传给 rewrite_chain，生成 rewritten_query
                rewritten_query=rewrite_chain
            )
            | RunnablePassthrough.assign(
                # 第二步：用 rewritten_query 去执行检索，并格式化成 context 文本
                context=lambda x: format_document(perform_retrieval(x["rewritten_query"]))
            )
            # 第三步：现在我们有了 input, history, context，传给 QA Prompt
            | self.qa_prompt_template
            | print_prompt 
            | self.chat_model
            | StrOutputParser()
        )
        
        # 挂载历史消息记忆
        conversation_chain = RunnableWithMessageHistory(
            base_chain, 
            get_history, 
            input_messages_key="input", 
            history_messages_key="history", 
        )

        return conversation_chain
```

### config_data.py

```python
import os
# 1. 配置百炼的 API Key 和 Base URL
# 注意：把这里的 YOUR_BAILIAN_API_KEY 换成你自己的
os.environ["DASHSCOPE_API_KEY"] = "sk-b3a13529205641398551a75bdebcc940"
# 阿里云百炼的 OpenAI 兼容端点
os.environ["OPENAI_API_BASE"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

md5_path = "data/md5.text"

collection_name = "rag"
persist_directory = "data/chroma_db"

chunk_size = 1000
chunk_overlap = 100
separators = ["\n\n", "\n", " ", ".", "。", "!", "！", "?", "？", "\n$$\n", "$$"]
max_spliter_char_number = 1000

similarity_threshold = 2

embedding_model = "text-embedding-v4"
chat_model = "qwen-turbo"

session_config = {
    "configurable": {"session_id": "user_001"}
}
```

