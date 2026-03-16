# 面向 CAE 仿真领域的 LangGraph 多智能体自动化系统

## 📌 项目背景与核心架构

本项目旨在解决传统 CAE 仿真（如 Abaqus 建模）中参数设置繁琐、脚本编写门槛高的问题。系统接收用户的自然语言需求（例如“建一个子弹冲击模型，稍微改薄一点”），通过 LangGraph 构建的有向无环图（DAG）工作流，自动完成**意图识别、参数提取、物理规则校验与修正、以及仿真脚本生成**。

**核心亮点架构：** 系统采用 Agentic Workflow（智能体工作流）模式，有别于不可控的完全自主 Agent。通过 `StateGraph` 维护全局状态，并引入了 **Reflexion（反思纠错）** 机制。当大模型提取的物理参数违背工程常识时（如子弹半径为负数），Critic 节点会打回请求，强制大模型根据报错日志重新提取，形成闭环。

------

## 📂 项目模块深度拆解与面试知识点

整个项目分为四大核心层：**编排层（Graph）、节点逻辑层（Nodes）、能力扩展层（Skills & Templates）、外部工具层（MCP Tools）**。

### 1. 状态与工作流编排层 (`state.py` & `workflow.py`)

这是整个 Agent 系统的“骨架”和“神经中枢”。

- **`state.py` (全局状态机)**：
  - **做了什么**：定义了 `CAEAgentState` (TypedDict)。它就像流水线上的传送带，包含 `user_query`（用户输入）、`extracted_params`（提取结果）、`error_log`（报错信息）和 `retry_count`（重试次数）。
  - **面试亮点**：状态机管理是复杂 LLM 应用的基础。通过定义严格的 State，保证了各节点之间数据流转的强类型与可追溯性。记录 `retry_count` 更是防御性编程的体现，防止 LLM 陷入无限报错重试的死循环（项目中设定了最高 3 次熔断）。
- **`workflow.py` (DAG 路由引擎)**：
  - **做了什么**：把分散的函数（Nodes）连成了完整的业务逻辑图。
  - **面试亮点（重点！）**：定义了**条件边 (Conditional Edges)**。在 Critic 节点执行后，图并没有直接结束，而是通过 `check_result` 函数判断 `state["error_log"]`。如果有错，路由指向 `Extractor` 重新执行；无错才走向 `END`。这就是业界著名的 **Reflexion（反思回路）** 落地实现。

### 2. 节点逻辑层 (`nodes.py`)

这是包含大模型核心推理能力的“大脑”。共有四个核心 Node：

- **Node 1: Planner (意图识别节点)**
  - **逻辑**：作为“前台接待”，识别用户的自然语言意图，判断是走向 `bullet_skill` 还是 `tunnel_support_skill`，或者直接拦截不支持的请求（如流体仿真）。
  - **面试亮点**：**安全与解耦**。在复杂的企业级应用中，不能让一个大模型处理所有事。Planner 充当了语义路由器 (Semantic Router)，有效防止了 Prompt Injection（提示词注入），并决定后续加载哪一套专业的技能包。
- **Node 2: Extractor (动态参数提取节点) - 【技术含金量最高】**
  - **逻辑**：根据 Planner 选择的 Skill，动态去 `skills/` 目录下加载对应的 `instruction.md` 和 `schema.json`。随后调用 `llm.with_structured_output` 强制要求大模型按照 JSON 格式输出物理参数。
  - **面试亮点**：
    1. **动态挂载 (Dynamic Prompting)**：提示词没有硬编码在 Python 里。这意味着未来要增加“钻爆法隧道开挖支护决策”模块，只需新建一个文件夹，完全不用改动核心代码，符合开闭原则（OCP）。
    2. **强制结构化输出**：直接输出 JSON 保证了下游代码渲染的稳定性。
    3. **Human-in-the-Loop (HITL) 追问机制**：当用户的描述存在极端物理矛盾无法自动推理时，返回 `need_clarification` 状态，将控制权交还给用户进行多轮对话，极大增强了系统的可用性。
- **Node 3: Coder (脚本渲染节点)**
  - **逻辑**：拿到校验通过的 JSON 参数，利用 Jinja2 模板引擎，将参数无缝注入到预先写好的 `bullet.py` 或 `tunnel.py` 模板中，并生成带有时间戳的唯一脚本保存到沙盒 (`sandbox/`)。
  - **面试亮点**：**为什么不用大模型直接写 Abaqus/FLAC3D 代码？** 因为纯大模型写出的 CAE 脚本往往存在 API 调用错误或语法幻觉。采用 **"LLM 提取参数 + Jinja2 规则渲染"** 的混合模式，既发挥了 LLM 的自然语言理解优势，又利用传统模板保证了 100% 的工业级代码执行成功率。
- **Node 4: Critic (工程物理校验节点)**
  - **逻辑**：一套纯 Python 编写的硬性规则引擎。例如检查 `plate_thickness > 0`，以及复杂的约束关系（如子弹直径不能大于靶板长度）。如果违规，将错误详情写入 `error_log`。
  - **面试亮点**：**跨模态常识对齐**。大模型懂语言，但不懂桥隧工程或爆炸力学中的绝对物理定律。Critic 节点就是作为“资深总工”把关，将大模型缺乏的“空间几何与物理常识”通过代码逻辑补全，这是让 AI 走向工业实用的关键防线。

### 3. 能力扩展与配置层 (`skills/` & `templates/`)

- **`skills/` 目录**：包含各个仿真场景的“专家经验”。例如 `instruction.md` 里面详细规定了如果用户只说“薄一点”，系统应该默认取值 10.0。这种将**模糊语义映射为具体工程默认值**的规则设计，是非常懂业务的体现。
- **`templates/` 目录**：存放原生 CAE 脚本（如 Abaqus Python API），使用 `{{ geometry.plate_length }}` 作为占位符，等待 Coder 节点进行数据绑定。

### 4. 外部工具层 (`server.py` & `material_db.json`)

- **逻辑**：定义了一个轻量级的工具（Tool），允许大模型在遇到具体的材料名称（如“X-90特种钢”）但不知道其密度和弹性模量时，主动调用 `query_local_material_db` 去本地数据库查询。
- **面试亮点**：引入了 **Agent Tool Calling (工具调用)** 能力。这解决了大模型的知识盲区问题，使得系统可以通过外挂数据库获得最新、最精确的工程材料参数。

------

## 🔄 系统数据流转全景重现 (以 `main.py` 为例)

让我们看看你在 `main.py` 中输入的这句极度刁钻的测试用例是如何跑通的：

> *"帮我建一个子弹冲击模型... 子弹半径设置为 -15... 弹性模量设为 206000..."*

1. **[Planner]** 识别到“子弹冲击”，路由到 `bullet_skill`。
2. **[Extractor - 第一次尝试]** 完美地提取了参数，生成了 JSON，其中包含致命错误：`"bullet_radius": -15`。
3. **[Coder]** 将错误的 `-15` 渲染到了模板中。
4. **[Critic]** 介入审查，触发规则告警：*"错误：物理学不存在负数或零的半径，子弹半径必须为正数。"*，将其写入 `state["error_log"]`。
5. **[Workflow 路由]** 发现有报错，根据条件边，将状态机**打回给 Extractor**。
6. **[Extractor - Reflexion 触发]** 第二次被唤醒，但这次除了用户输入，它还收到了 Critic 的报错信息。大模型意识到自己的错误，自动将子弹半径修正为合理的正数绝对值（如 15）。
7. **[后续流程]** 重新走 Coder 生成正确代码 -> Critic 校验通过 -> Workflow 结束。

### 🎙️ 模拟面试第一轮：架构与数据流

#### ❓ 面试官提问 1：全局数据流与状态机机制

> **面试官：**“我看你的项目用了 LangGraph。你能脱离底层源码，从宏观上给我串讲一下，从你在 `main.py` 输入那段包含‘子弹半径-15’的刁钻自然语言开始，数据是怎么在你的各个代码文件之间流转的吗？特别提一下 `state.py` 在里面扮演了什么角色。”

**🗣️ 你的高分回答：** “面试官您好。整个系统的数据流转是一个典型的**有向无环图（DAG）状态机驱动模型**。

这里面，`state.py` 是整个系统的**数据总线（Data Bus）**。里面定义的 `CAEAgentState` 字典包含了用户问题、提取参数、代码、错误日志和重试次数。任何节点在处理完任务后，只能去修改这个 State 里的值，然后把更新后的 State 扔给下一个节点。这保证了数据的强类型约束和全局可追溯性。

从 `main.py` 启动开始，完整的数据流向如下：

1. **入口阶段：** `main.py` 构造了初始化的 `initial_state`（包含原始 Query），调用 `app.stream()` 将其推入工作流。
2. **路由阶段：** 数据首先进入 `nodes.py` 中的 `planner_node`。大模型分析后，将 State 中的 `selected_skill` 更新为 `bullet_skill`。
3. **提取阶段：** 数据流转到 `extractor_node`。它根据 `selected_skill` 去动态读取参数，并调用 LLM 输出结构化 JSON，更新 State 中的 `extracted_params`。由于您刚才提到用户输入了‘半径-15’，大模型如果照单全收，这里提取出的 `bullet_radius` 就会是 -15。
4. **代码渲染阶段：** `coder_node` 接收到参数，结合模板将其渲染为真实的 CAE 脚本，更新 State 中的 `generated_code` 并将其落盘到 `sandbox/` 目录下。
5. **工程校验阶段：** 这是最后一道防线。数据进入 `critic_node`。该节点包含纯 Python 编写的硬规则判定，它发现 `extracted_params` 中的半径为负数，触发违规。此时，它不修改代码，而是向 State 的 `error_log` 字段写入报错信息。
6. **图编排与循环：** 此时 `workflow.py` 中的条件边 `check_result` 捕获到 State 中存在 `error_log`，它会拒绝走向 `END`，而是将数据流**重新路由回 `extractor_node`**，形成闭环反思。直到校验通过，工作流才在 `workflow.py` 的指引下走向结束。”

------

#### ❓ 面试官提问 2：代码解耦与 OCP 原则（开闭原则）

> **面试官：**“传统的 Prompt 工程往往把系统提示词写死在代码里。但我注意到你拆分了 `nodes.py`、`skills/` 文件夹和 `templates/` 文件夹。如果我现在要求你新增一个‘藏区公路钻爆法隧道开挖支护智能化决策’的业务线，你需要修改核心逻辑代码吗？你是怎么设计的？”

**🗣️ 你的高分回答：** “不需要修改核心逻辑代码。这个架构严格遵循了软件工程中的**开闭原则（对扩展开放，对修改封闭）**。这也是我认为这个系统最具工程价值的地方。

在我的 `nodes.py` 的 `extractor_node` 中，没有任何硬编码的 Prompt。它的逻辑是：根据 Planner 传过来的 `current_skill`，动态地用 `os.path.join` 去 `skills/` 目录下寻找对应的文件夹。

如果要新增您说的‘钻爆法隧道支护决策’业务：

1. **配置层扩展：** 我只需要在 `skills/` 下新建一个 `tunnel_support_skill` 文件夹。在里面写一个 `instruction.md`（定义开挖方法、围岩等级的提取规则）和一个 `schema.json`（定义参数结构）。
2. **模板层扩展：** 在 `templates/` 下放入一个 `tunnel.py`，里面写好 Abaqus 或 FLAC3D 的 Python API，并在需要填入围岩参数的地方留好 Jinja2 的占位符（如 `{{ rock.elastic_modulus }}`）。
3. **节点解耦：** 回到 `nodes.py`，只有 `planner_node` 的系统提示词需要增加一条支持‘隧道支护’的分类说明，其余的 `extractor_node` 和 `coder_node` 会自动根据文件路径映射（`skill_to_template_map`）完成读取和渲染，一行核心控制流代码都不需要动。”

------

#### ❓ 面试官提问 3：Reflexion 机制与幻觉压制

> **面试官：**“大模型是个‘文科生’，在 CAE 这种严谨的理工科领域很容易产生常识性幻觉（比如长宽比失调）。你提到的反思纠错（Reflexion）机制，在 `workflow.py` 和 `nodes.py` 中具体是如何配合实现的？如何防止系统陷入死循环？”

**🗣️ 你的高分回答：** “大模型的幻觉主要来自于它缺乏真实世界的物理边界感。我的 Reflexion 机制就是给它配一个‘理科生监理’。

这种配合分为三步：

1. **触发拦截（`nodes.py - critic_node`）：** 这是一个完全去大模型化的确定性规则引擎。当它拿到参数后，会进行 `if bullet_diameter > plate_length` 这种刚性数学判断。一旦违背，将明确的工程解释（如‘子弹直径不能大于钢板尺寸’）写入 `error_log`。
2. **图流转路由（`workflow.py`）：** 图的条件边会监听这个 `error_log`。一旦发现不为空，`add_conditional_edges` 就会强行把数据传送带倒退回 `Extractor` 节点。
3. **上下文注入与自愈（`nodes.py - extractor_node`）：** 这是最关键的一步。当 `Extractor` 再次被唤醒时，它会检查 State。发现有 `error_log` 后，代码会**动态地向历史 Messages 中追加一条 System Prompt**：‘注意！上次提取的参数在物理校验时失败了。报错信息如下...’。大模型看到这个严厉的报错后，内部的 Attention 机制会迫使它重新审视刚才生成的数值，从而实现参数自愈。

至于防止死循环，我在 `state.py` 里设计了 `retry_count` 字段。每次经过 `extractor_node`，计数器加 1。`workflow.py` 里的 `check_result` 会优先判断 `retry_count >= 3`，一旦超过，强行终止当前任务。这在生产环境中极大保护了 Token 成本，防止恶意输入耗尽 API 额度。”

------

#### ❓ 面试官提问 4：外部工具调用（Tool Calling）与数据一致性

> **面试官：**“工程中有大量的专业材料参数，比如 C30 喷射混凝土的密度。你写了一个 `server.py` 和 `material_db.json`，你是怎么让大模型知道何时去查这个本地库，而不是自己瞎编一个数值的？”

**🗣️ 你的高分回答：** “这涉及大模型的边界认知问题。我通过**工具绑定与 Prompt 强约束**来解决。

1. **外部数据挂载：** `material_db.json` 扮演了企业内部私有资产的角色，它存放着极其精确的特种钢或围岩参数。在 `server.py` 中，我用 `@tool` 装饰器将查询逻辑封装成了一个标准的 MCP（Model Context Protocol）工具 `query_local_material_db`。
2. **指令级触发约束：** 虽然工具写好了，但大模型通常比较‘自信’，喜欢用自己预训练的近似值。因此，在 `skills/bullet_skill/instruction.md`（系统指令）中，我制定了严苛的业务规则，明确告知大模型：‘当用户没有明确提供数值时，**必须**调用工具查询本地数据库’。
3. *（进阶补全 - 展现你的代码敏锐度）* 不过，需要向您说明的是，在我当前提交的原型代码中，`nodes.py` 里的 `llm.with_structured_output` 暂时只绑定了 JSON Schema 以保证输出格式，还没有正式通过 `llm.bind_tools()` 将 `server.py` 里的工具注册给大模型实例。在下一步的迭代中，我会将工具调用（Function Calling）正式集成到 `extractor_node` 的执行逻辑中，从而完成真正的私有知识检索闭环。”