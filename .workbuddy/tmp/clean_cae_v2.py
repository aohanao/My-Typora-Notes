# -*- coding: utf-8 -*-
"""CAE_Agent项目文档 v2 生成脚本：保留原分类骨架，仅做清理。
操作均基于原文行号（已核对），输出到 CAE_Agent项目文档_v2.md。
"""
import io, sys

SRC = r"D:\GitHub\My-Typora-Notes\CAE_Agent项目文档.md"
DST = r"D:\GitHub\My-Typora-Notes\CAE_Agent项目文档_v2.md"

with io.open(SRC, "r", encoding="utf-8") as f:
    raw = f.read()
lines = raw.split("\n")
n = len(lines)
print("total lines:", n)

out = []

HEADER_NOTE = """
> **v2 清理版说明**：保留原有技术分类骨架，仅做清理——① 清除 AI 辅导对话残留；② 「大模型 + 计算机八股」整体迁出至《计算机与大模型八股.md》（三份项目文档共用）；③ 原未归档的"分布式异步任务推演"收编为「工程化演进」章节；④ Agent/Skill-Benchmark SOP 归位为「评测方法论」章节。
"""

REVIEW_BLOCK = """**复盘：框架归属的口径教训**

面试官问"参照了什么框架"，是在问"你的地基是什么"——答案是 **LangGraph**。OpenClaw 和 Hermes 只是项目里参考使用的工具，不是系统的基础框架，混着说会给人"只知道名词、不知其意"的印象。

> ✅ 正确回答："我们的多智能体系统基于 LangGraph 的状态机架构自行搭建。同时为了加速开发，我们参考/使用了 OpenClaw 的插件生态来做工具集成层，参考了 Hermes 的 Harness 设计思路来做评测和记忆管理。但核心的决策流编排是我们基于 LangGraph 的 StateGraph 自己设计的。"

补充：简历里写的"Trace/Span 架构"就是 OpenTelemetry 的核心概念——埋点探针 = OTel SDK 的 Instrumentation，Trace/Span = OTel 的数据模型。被追问"Trace/Span 基于什么协议"时，直接答 OpenTelemetry。"""

MIGRATED_BLOCK = """## 公共基础（已迁出）

> 「大模型」与「计算机八股」两章已整体迁出至《计算机与大模型八股.md》，三份项目文档共用一份、避免重复维护。迁出内容：Few-shot / CoT / ReAct / Prompt Caching、Message 四类型、Transformer 架构、SFT / LoRA / QLoRA、训练三阶段；RPC、TCP/HTTP、代理、端口、负载均衡、GIL、并发/并行、进程/线程/协程、SQL、Linux、Redis。

---

## 工程化演进：长时仿真任务的异步化改造

> 本节回答三个递进问题：① 当前系统的运行边界在哪（浏览器 / Agent 后端 / 仿真机分别关掉会怎样）；② 同步阻塞架构为什么撑不住 4 小时长任务；③ 借鉴 ai-review-copilot 的异步任务化改造方案。"""

HARNESS_NOTE = """
> 本节是前文 Harness Engineering、智能体评测与 Benchmark SOP 的**面试串讲版**，用于快速过执行链路与指标口径；细节见前文各章。"""

for i, line in enumerate(lines, 1):
    s = line.rstrip("\r")

    # 1) 文档头：标题后插入清理说明
    if i == 1:
        out.append(s)
        out.append(HEADER_NOTE)
        continue

    # 2) 722-744 框架归属对话残留 -> 复盘块
    if 722 <= i <= 744:
        if i == 722:
            out.append(REVIEW_BLOCK)
        continue

    # 3) 1812 工具调用残留
    if i == 1812:
        continue

    # 4) 1851-1855 对话残留
    if 1851 <= i <= 1855:
        if i == 1851:
            out.append("这正是大模型智能体开发中，**\u201c计数触发（基于消息轮数）\u201d**与**\u201c容量触发（基于 Token 体积）\u201d**之间的核心差异，可以作为面试中有含金量的技术深度点展开：")
        continue

    # 5) 1870 吹捧句
    if i == 1870:
        out.append("这种\u201c不仅考虑常规状态，还防范高体积突发数据\u201d的设计，体现了**防御性编程（Defensive Programming）**思想。")
        continue

    # 6) 1872 对话式引入
    if i == 1872:
        out.append("高频追问：**现在很多模型（比如 Qwen-2.5、GPT-4o）的上下文窗口动辄 12.8 万（128K）甚至上百万，为什么我们还要在代码里假设 `MAX_TOKENS = 8000`？**")
        continue

    # 7) 2173-2174 工具调用残留
    if 2173 <= i <= 2174:
        continue

    # 8) 2176 对话式引入
    if i == 2176:
        out.append("下面从**可观测性记录（OpenTelemetry）**和**智能体间通信（LangGraph State）**两个维度拆解：")
        continue

    # 9) 3084-3593 大模型+八股迁出，替换为迁移说明 + 工程化演章节头
    if 3084 <= i <= 3593:
        if i == 3084:
            out.append(MIGRATED_BLOCK)
        continue

    # 10) 3594-3596 对话残留
    if 3594 <= i <= 3596:
        continue

    # 11) 3625 吹捧句
    if i == 3625:
        continue

    # 12) 3633-3637 对话引入 -> 章节小标题
    if 3633 <= i <= 3637:
        if i == 3633:
            out.append("### 终极部署形态：全站服务器集中部署（B/S 架构）")
            out.append("")
            out.append("在实际的工业落地和企业私有化部署中，会把整个系统全部打包放进服务器，而不是让用户自己在本地用 Docker 跑 Agent。这种架构有几个巨大的优势：")
        continue

    # 13) 3669 吹捧句
    if i == 3669:
        out.append("面试时把这三步演进讲清楚，是体现工程落地眼光和系统设计思维的加分点。")
        continue

    # 14) 3675-3677 工具调用残留
    if 3675 <= i <= 3677:
        continue

    # 15) 3679 对话式引入
    if i == 3679:
        out.append("对于大模型 Agent 驱动工业软件（如 Abaqus、Ansys 等仿真软件）这种**长链路、长时间任务**的场景，**同步断联**是生产环境中最经典、最棘手的痛点。")
        continue

    # 16) 3681 对话式引入
    if i == 3681:
        out.append("下面从**当前系统的做法**、**为什么会断联**、**业界标准的生产级解决方案**三个层面拆解：")
        continue

    # 17) 3755-3762 工具调用残留
    if 3755 <= i <= 3762:
        continue

    # 18) 3764 吹捧句
    if i == 3764:
        out.append("可以直接借鉴 `ai-review-copilot` 项目已有的架构设计。")
        continue

    # 19) 3953 SOP 标题归位 H1 -> H2
    if i == 3953:
        out.append("## Agent/Skill-Benchmark 评测 SOP（跨项目通用方法论）")
        continue

    # 20) 3954-4239 SOP 内部标题降一级
    if 3954 <= i <= 4239:
        if s.startswith("### "):
            out.append("#" + s)
        elif s.startswith("## "):
            out.append("#" + s)
        else:
            out.append(line)
        continue

    # 21) 4242 面试版章节加定位说明
    if i == 4242:
        out.append(s)
        out.append(HARNESS_NOTE)
        continue

    out.append(line)

text = "\n".join(out)
if not text.endswith("\n"):
    text += "\n"
with io.open(DST, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("written:", DST, "lines:", text.count("\n") + 1)

# 校验：确认关键内容仍在
checks = [
    ("## 智能体范式", 1), ("## Harness Engineering", 1), ("## Context Engineering", 1),
    ("## Memory", 1), ("## MCP", 1), ("## OpenTelemetry 借鉴", 1), ("## 指标优化", 1),
    ("## 工程化演进：长时仿真任务的异步化改造", 1),
    ("## Agent/Skill-Benchmark 评测 SOP（跨项目通用方法论）", 1),
    ("## CAE-Agent Harness 评测体系迭代优化（面试版梳理）", 1),
]
for kw, _ in checks:
    c = text.count(kw)
    print(("OK " if c == 1 else "FAIL ") + kw + f" ({c})")
for bad in ["完全正确", "Viewed ", "Listed directory", "你的直觉非常敏锐", "非常棒", "## 计算机八股", "## 大模型\n"]:
    c = text.count(bad)
    print(("CLEAN " if c == 0 else "REMAIN ") + repr(bad) + f" ({c})")
