from __future__ import annotations

import os
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    def generate(self, system_prompt: str, user_prompt: str) -> str: ...
    def generate_vision(
        self,
        system_prompt: str,
        image_blocks: list[dict],
        text_prompt: str,
    ) -> str: ...


# ---------------------------------------------------------------------------
# Real Anthropic client (wraps tony's AnthropicClient)
# ---------------------------------------------------------------------------

class AnthropicLLMClient:
    """Simple prompt→text wrapper around tony's AnthropicClient.

    Uses send_message() (non-streaming) — powergen only needs a single
    response per call, not a tool-use loop.
    """

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        from tony.api_client import AnthropicClient  # type: ignore[import]
        self._client = AnthropicClient(model=model)
        self._model = model

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        from tony.api_client import MessageRequest  # type: ignore[import]
        from tony.models import TextBlock  # type: ignore[import]

        req = MessageRequest(
            model=self._model,
            max_tokens=8192,
            messages=[{"role": "user", "content": user_prompt}],
            system=[{"type": "text", "text": system_prompt}],
            stream=False,
        )
        resp = self._client.send_message(req)
        for block in resp.content:
            if isinstance(block, TextBlock):
                return block.text
        return ""

    def generate_vision(
        self,
        system_prompt: str,
        image_blocks: list[dict],
        text_prompt: str,
    ) -> str:
        from tony.api_client import MessageRequest  # type: ignore[import]
        from tony.models import TextBlock  # type: ignore[import]

        content: list[dict] = image_blocks + [{"type": "text", "text": text_prompt}]
        req = MessageRequest(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": content}],
            system=[{"type": "text", "text": system_prompt}],
            stream=False,
        )
        resp = self._client.send_message(req)
        for block in resp.content:
            if isinstance(block, TextBlock):
                return block.text
        return ""

    def close(self) -> None:
        self._client.close()


# ---------------------------------------------------------------------------
# Mock client (offline testing)
# ---------------------------------------------------------------------------

_MOCK_PLAN_JSON = """{
  "overview": "A 5-slide introduction to AI-powered development tools.",
  "slide_summaries": [
    "Title slide: The Future of AI Development",
    "Problem: Developer productivity bottlenecks today",
    "Solution: AI pair programming and automation",
    "Demo: Live examples with tony and powergen",
    "Call to action: Getting started today"
  ],
  "references": [],
  "open_questions": ["Should we include benchmark data?"]
}"""

_MOCK_SPEC_JSON = """{
  "title": "The Future of AI Development",
  "audience": "Software engineers and tech leads",
  "tone": "professional",
  "theme_reference": "",
  "slides": [
    {
      "index": 0,
      "title": "The Future of AI Development",
      "bullets": [],
      "layout": "Title Slide",
      "notes": "Welcome the audience and introduce the topic."
    },
    {
      "index": 1,
      "title": "Developer Productivity Bottlenecks",
      "bullets": [
        "Context switching costs 40% of focus time",
        "Repetitive boilerplate slows delivery",
        "Code review backlogs accumulate"
      ],
      "layout": "Title and Content",
      "notes": "Open with pain points the audience recognises."
    },
    {
      "index": 2,
      "title": "AI Pair Programming & Automation",
      "bullets": [
        "LLM agents handle repetitive coding tasks",
        "Natural language → working code",
        "Continuous context awareness"
      ],
      "layout": "Title and Content",
      "notes": "Transition from problem to solution."
    },
    {
      "index": 3,
      "title": "Live Demo: tony & powergen",
      "bullets": [
        "tony: AI agent CLI for code tasks",
        "powergen: AI presentation generator",
        "Both built on Anthropic Claude"
      ],
      "layout": "Title and Content",
      "notes": "Show a quick demo if time allows."
    },
    {
      "index": 4,
      "title": "Get Started Today",
      "bullets": [
        "pip install tony-cli",
        "Set ANTHROPIC_API_KEY",
        "Run: tony / powergen"
      ],
      "layout": "Title and Content",
      "notes": "End with a clear call to action."
    }
  ]
}"""


_MOCK_TEMPLATE_ANALYSIS_JSON = """{
  "slides": [
    {
      "slide_index": 1,
      "slide_relevant": true,
      "text_nodes": [
        {"original_text": "Presentation Title", "purpose": "title"},
        {"original_text": "Subtitle or tagline here", "purpose": "body"}
      ]
    },
    {
      "slide_index": 2,
      "slide_relevant": false,
      "text_nodes": [
        {"original_text": "How to use this template", "purpose": "title"},
        {"original_text": "Replace slide 1 with your topic title", "purpose": "bullet"},
        {"original_text": "Delete this instructions slide before presenting", "purpose": "bullet"}
      ]
    },
    {
      "slide_index": 3,
      "slide_relevant": true,
      "text_nodes": [
        {"original_text": "Slide Heading", "purpose": "title"},
        {"original_text": "First bullet point", "purpose": "bullet"},
        {"original_text": "Second bullet point", "purpose": "bullet"},
        {"original_text": "Third bullet point", "purpose": "bullet"}
      ]
    }
  ]
}"""

_MOCK_TEMPLATE_MAPPING_JSON = """{
  "mappings": [
    {"slide_index": 1, "original_text": "Presentation Title", "replacement_text": "Q1 Sales Review"},
    {"slide_index": 1, "original_text": "Subtitle or tagline here", "replacement_text": "APAC Region — January to March"},
    {"slide_index": 2, "original_text": "How to use this template", "replacement_text": "Instructions (should be skipped by filter)"},
    {"slide_index": 3, "original_text": "Slide Heading", "replacement_text": "Key Highlights"},
    {"slide_index": 3, "original_text": "First bullet point", "replacement_text": "Revenue up 12% YoY"},
    {"slide_index": 3, "original_text": "Second bullet point", "replacement_text": "New enterprise accounts: 8"},
    {"slide_index": 3, "original_text": "Third bullet point", "replacement_text": "Customer retention rate: 94%"}
  ]
}"""

_MOCK_DISTILL_JSON = """{
  "version": "1.0",
  "source": {
    "file_name": "mock_lecture.pptx",
    "file_hash": "",
    "distilled_at": ""
  },
  "global_summary": "A mock lecture covering paging and the Translation Lookaside Buffer (TLB). Introduces virtual-to-physical address mapping and explains how the TLB accelerates translation.",
  "main_topics": ["paging", "address translation", "TLB", "virtual memory"],
  "chunks": [
    {
      "chunk_id": "chunk_01",
      "slide_range": [1, 2],
      "titles": ["Overview", "Paging Basics"],
      "summary_short": "Introduces paging as a fixed-size memory management scheme and the page table used for address translation.",
      "key_points": [
        "Virtual memory is divided into fixed-size pages.",
        "Physical memory is divided into frames of the same size.",
        "The page table maps virtual page numbers to physical frame numbers."
      ],
      "definitions": [
        {"term": "paging", "definition": "A memory management scheme that divides virtual memory into fixed-size pages and physical memory into fixed-size frames."},
        {"term": "page table", "definition": "A data structure that maps virtual page numbers to physical frame numbers."}
      ],
      "entities": ["paging", "page table", "virtual memory", "frame"],
      "question_signatures": [
        "What is paging?",
        "How does address translation work in paging?",
        "What is a page table?"
      ],
      "keywords": ["paging", "page table", "frame", "virtual address", "physical address"],
      "anchors": {
        "start_slide": 1,
        "end_slide": 2,
        "prev_title": null,
        "next_title": "Translation Lookaside Buffer"
      }
    },
    {
      "chunk_id": "chunk_02",
      "slide_range": [3, 4],
      "titles": ["Translation Lookaside Buffer", "TLB Example"],
      "summary_short": "Explains the TLB as a cache for recent page table translations and illustrates hit vs miss latency.",
      "key_points": [
        "The TLB caches recent page table entries in hardware.",
        "A TLB hit avoids a slow page table memory lookup.",
        "A TLB miss falls back to the full page table at the cost of one extra memory access."
      ],
      "definitions": [
        {"term": "TLB", "definition": "A small hardware cache storing recent virtual-to-physical page table translations."}
      ],
      "entities": ["TLB", "page table", "TLB hit", "TLB miss"],
      "question_signatures": [
        "What is a TLB?",
        "Why does a TLB improve performance?",
        "What happens on a TLB miss?"
      ],
      "keywords": ["TLB", "translation lookaside buffer", "TLB hit", "TLB miss", "cache"],
      "anchors": {
        "start_slide": 3,
        "end_slide": 4,
        "prev_title": "Paging Basics",
        "next_title": null
      }
    }
  ]
}"""


_MOCK_PLAN_CATALOG_JSON = """[
  {
    "pattern_id": "tutor_intro_01",
    "slots": {
      "tutor_name": "Dr. Sarah Chen",
      "credentials": "PhD Economics, Harvard Business School",
      "bio": "10 years retail industry experience\\nFormer VP of Sales at Fortune 500\\nSpecialises in seasonal demand cycles",
      "section_title": "Tutor Intro"
    }
  },
  {
    "pattern_id": "course_overview_01",
    "slots": {
      "course_title": "MKTG 401: Seasonal Sales Strategy",
      "assessment_header": "Assessment Methods",
      "assessment_body": "Midterm case analysis (30%)\\nFinal group project (40%)\\nClass participation (30%)",
      "learning_points_header": "Learning Objectives",
      "learning_points_body": "Understand seasonal demand cycles\\nDevelop promotional pricing strategies\\nAnalyse historical sales data patterns"
    }
  },
  {
    "pattern_id": "three_option_comparison_01",
    "slots": {
      "main_title": "Which Strategy Fits Your Product?",
      "option_1_title": "Early Bird Pricing",
      "option_1_body": "Launch 8 weeks before peak season\\nGradual price increase builds momentum\\nIdeal for planned purchase categories",
      "option_2_title": "Flash Sales",
      "option_2_body": "24-48 hour high-urgency windows\\nClears excess seasonal inventory\\nDrives rapid volume spikes",
      "option_3_title": "Loyalty Discounts",
      "option_3_body": "Reward repeat customers first\\nStaggered discount tiers\\nProtects margin long-term"
    }
  }
]"""

_MOCK_CATALOG_V2_JSON = """[
  {
    "source_slide": 1,
    "slide_id": "title",
    "reusable": false,
    "slots": [
      {"name": "title",    "shape_name": "文本占位符 48", "content_type": "text", "max_chars": 60},
      {"name": "subtitle", "shape_name": "文本框 10",     "content_type": "text", "max_chars": 100}
    ]
  },
  {
    "source_slide": 3,
    "slide_id": "profile",
    "reusable": false,
    "slots": [
      {"name": "name",        "shape_name": "文本框 20", "content_type": "text",    "max_chars": 30},
      {"name": "credentials", "shape_name": "文本框 21", "content_type": "text",    "max_chars": 80},
      {"name": "bio",         "shape_name": "文本框 22", "content_type": "bullets", "max_chars": 200}
    ]
  }
]"""

# ---------------------------------------------------------------------------
# v3 mock responses (fill command — catalog + plan)
# ---------------------------------------------------------------------------
# Shape names verified against test/test.pptx:
#   Slide 1: 'Title 2', 'TextBox 15' (×2), '文本框 8'
#   Slide 2: '文本占位符 48', '文本框 10', '文本框 15', '文本框 20', '文本框 27'
#   Slide 3: '文本框 10', '文本框 1'  (section header layout)

_MOCK_CATALOG_V3_JSON = """[
  {
    "source_slide": 1,
    "slide_id": "title",
    "reusable": false,
    "description": "Cover slide with university, student/advisor info, and course description",
    "slots": [
      {"name": "university_program",    "shape_name": "Title 2",    "content_type": "text",    "max_chars": 80},
      {"name": "student_advisor_info",  "shape_name": "TextBox 15", "content_type": "bullets", "max_chars": 120},
      {"name": "course_description",    "shape_name": "\\u6587\\u672c\\u6846 8",  "content_type": "text", "max_chars": 40}
    ]
  },
  {
    "source_slide": 2,
    "slide_id": "profile",
    "reusable": false,
    "description": "Advisor profile with name, affiliation, credentials, and bio",
    "slots": [
      {"name": "name",        "shape_name": "\\u6587\\u672c\\u5360\\u4f4d\\u7b26 48", "content_type": "text",    "max_chars": 30},
      {"name": "affiliation", "shape_name": "\\u6587\\u672c\\u6846 10",              "content_type": "text",    "max_chars": 80},
      {"name": "credentials", "shape_name": "\\u6587\\u672c\\u6846 15",              "content_type": "text",    "max_chars": 150},
      {"name": "bio",         "shape_name": "\\u6587\\u672c\\u6846 20",              "content_type": "bullets", "max_chars": 250}
    ]
  },
  {
    "source_slide": 3,
    "pattern_id": "section_header",
    "reusable": true,
    "description": "Section divider with title and subtitle",
    "fit_for": ["chapter breaks", "section intros", "topic transitions"],
    "slots": [
      {"name": "section_title",    "shape_name": "\\u6587\\u672c\\u6846 10", "content_type": "text", "max_chars": 40},
      {"name": "section_subtitle", "shape_name": "\\u6587\\u672c\\u6846 1",  "content_type": "text", "max_chars": 80}
    ]
  },
  {
    "source_slide": 4,
    "pattern_id": "keep_04",
    "reusable": false,
    "description": "Numbered two-card layout — course selection GPA requirements (generic, keep as-is)",
    "slots": []
  },
  {
    "source_slide": 5,
    "pattern_id": "keep_05",
    "reusable": false,
    "description": "Numbered four-card layout — retake rules and costs (generic, keep as-is)",
    "slots": []
  }
]"""

_MOCK_PLAN_V3_JSON = """[
  {
    "op": "fill_special",
    "slide_id": "title",
    "slots": {
      "university_program": "University of Toronto Mississauga\\nComputer Science Program",
      "student_advisor_info": "\\u8def\\u89c5\\u5b66\\u751f\\uff1a[ 2026\\u7ea7\\uff0cEthan ]\\n\\u8def\\u89c5\\u5bfc\\u5e08\\uff1a[ Johnny ]",
      "course_description": "CSC 162 \\u8bfe\\u7a0b\\u9009\\u8bfe\\u89c4\\u5212"
    }
  },
  {
    "op": "fill_special",
    "slide_id": "profile",
    "slots": {
      "name": "Johnny Gan",
      "affiliation": "University of Toronto, Canada\\n\\u8ba1\\u7b97\\u673a\\u79d1\\u5b66\\u7855\\u58eb",
      "credentials": "Undergraduate GPA 3.8/4.0 | 6 years academic experience with Computer related courses",
      "bio": "Systems programming enthusiast\\nTA for CSC 108 and CSC 148\\nExpertise in data structures and algorithms"
    }
  },
  {"op": "keep", "source_slide": 3},
  {"op": "keep", "source_slide": 4},
  {"op": "keep", "source_slide": 5},
  {
    "op": "clone_pattern",
    "pattern_id": "section_header",
    "slots": {
      "section_title": "CSC 162 \\u8bfe\\u7a0b\\u89c4\\u5212",
      "section_subtitle": "\\u672c\\u5b66\\u671f\\u5fc5\\u4fee\\u8bfe\\u7a0b\\u53ca\\u5b66\\u4e60\\u5efa\\u8bae"
    }
  },
  {
    "op": "clone_pattern",
    "pattern_id": "section_header",
    "slots": {
      "section_title": "\\u65f6\\u95f4\\u7ebf",
      "section_subtitle": "Key milestones and deadlines"
    }
  }
]"""

_MOCK_GENERATE_PLAN_JSON = """[
  {"type": "title", "special_slide": "title", "slots": {"title": "大学选课指南", "subtitle": "帮助新生规划最优学习路径"}},
  {"type": "section_divider", "title": "第一章：选课基础规则"},
  {"type": "content_structured", "title": "选课数量限制", "points": [
    {"title": "最低选课数量", "desc": "每学期至少选修12学分，低于此数视为非全日制"},
    {"title": "最高选课数量", "desc": "每学期最多选修20学分，超出需系主任批准"}
  ]},
  {"type": "content_simple", "title": "选课流程要点", "bullets": [
    "选课前查阅培养方案，确认学分要求",
    "优先选修必修课和先修课程",
    "选修课在满足必修后再行安排",
    "注意选课截止日期，逾期无法更改"
  ]},
  {"type": "section_divider", "title": "第二章：进阶策略"},
  {"type": "two_column", "title": "课程选择策略对比", "left": {
    "heading": "稳健型选课",
    "bullets": ["每学期14-16学分", "避免同期多门高难度课", "留出时间参加实习"]
  }, "right": {
    "heading": "快速型选课",
    "bullets": ["每学期18-20学分", "适合学习能力强的学生", "注意不要过度负担"]
  }},
  {"type": "timeline", "title": "大一选课时间轴", "steps": [
    {"label": "入学前", "desc": "阅读培养方案，了解必修课列表"},
    {"label": "第1-2周", "desc": "参加选课说明会，咨询学长学姐"},
    {"label": "第3周", "desc": "提交第一志愿选课申请"},
    {"label": "第4周", "desc": "确认选课结果，处理冲突"}
  ]},
  {"type": "special", "special_slide": "profile", "slots": {"name": "学业顾问", "credentials": "教务处选课指导专员", "bio": "协助学生规划四年课程\\n熟悉各院系课程要求\\n定期举办选课工作坊"}}
]"""

_MOCK_CATALOG_JSON = """[
  {
    "pattern_id": "tutor_intro_01",
    "source_slide": 1,
    "layout_name": "自定义版式",
    "description": "个人简介页，左侧照片，右侧姓名、学历和个人简介文字",
    "slots": [
      {"name": "name",        "shape_name": "文本占位符 48", "content_type": "text",    "max_chars": 30},
      {"name": "credentials", "shape_name": "文本框 10",     "content_type": "text",    "max_chars": 80},
      {"name": "bio",         "shape_name": "文本框 15",     "content_type": "bullets", "max_chars": 200}
    ],
    "fit_for": ["导师介绍", "讲师简介", "个人背景说明"],
    "not_fit_for": ["课程内容", "数据展示", "多列对比"],
    "reusable": false
  },
  {
    "pattern_id": "course_overview_01",
    "source_slide": 2,
    "layout_name": "DEFAULT-master",
    "description": "课程标题 + 两段式结构（section header + 正文），适合单课程详细介绍",
    "slots": [
      {"name": "course_title",    "shape_name": "Text 1", "content_type": "text",    "max_chars": 60},
      {"name": "section_header_1","shape_name": "Text 2", "content_type": "text",    "max_chars": 40},
      {"name": "section_body_1",  "shape_name": "Text 3", "content_type": "bullets", "max_chars": 300},
      {"name": "section_header_2","shape_name": "Text 4", "content_type": "text",    "max_chars": 40},
      {"name": "section_body_2",  "shape_name": "Text 5", "content_type": "bullets", "max_chars": 300}
    ],
    "fit_for": ["课程介绍", "考核方式说明", "学习重点列举", "章节详解"],
    "not_fit_for": ["多列对比", "流程图", "纯视觉内容"],
    "reusable": true
  },
  {
    "pattern_id": "prerequisite_chain_01",
    "source_slide": 3,
    "layout_name": "DEFAULT-master",
    "description": "标题 + 先修链流程图节点 + 底部双栏课程说明 + takeaway条",
    "slots": [
      {"name": "title",       "shape_name": "Text 1",  "content_type": "text", "max_chars": 70},
      {"name": "chain_label", "shape_name": "Text 2",  "content_type": "text", "max_chars": 50},
      {"name": "takeaway",    "shape_name": "Text 26", "content_type": "text", "max_chars": 120}
    ],
    "fit_for": ["先修关系说明", "路径规划", "课程链展示"],
    "not_fit_for": ["纯文字内容", "多段落正文", "个人介绍"],
    "reusable": true
  },
  {
    "pattern_id": "multi_option_comparison_01",
    "source_slide": 4,
    "layout_name": "DEFAULT-master",
    "description": "标题 + 三列选项对比，每列含独立标题和正文",
    "slots": [
      {"name": "title",      "shape_name": "Text 3",  "content_type": "text",    "max_chars": 60},
      {"name": "col1_title", "shape_name": "Text 5",  "content_type": "text",    "max_chars": 30},
      {"name": "col1_body",  "shape_name": "Text 6",  "content_type": "bullets", "max_chars": 250},
      {"name": "col2_title", "shape_name": "Text 8",  "content_type": "text",    "max_chars": 30},
      {"name": "col2_body",  "shape_name": "Text 9",  "content_type": "bullets", "max_chars": 250},
      {"name": "col3_title", "shape_name": "Text 11", "content_type": "text",    "max_chars": 30},
      {"name": "col3_body",  "shape_name": "Text 12", "content_type": "bullets", "max_chars": 250}
    ],
    "fit_for": ["多方案对比", "选项分析", "多场景展示"],
    "not_fit_for": ["单一主题", "流程说明", "个人介绍"],
    "reusable": true
  }
]"""

_MOCK_VISION_RESPONSE = (
    "[Visual: A diagram showing example content with labeled nodes and connecting arrows. (mock)]"
)


class MockLLMClient:
    """Returns canned responses for offline / CI testing."""

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        # Use system_prompt only for Layer 2 detection: user_prompt for call 2
        # contains the full analysis JSON (with "text_nodes"), which would
        # cause a false match if we checked combined.
        sp = system_prompt.lower()
        # v3 catalog: "three roles: special, reusable, or keep" is unique to v3 prompt
        if "three roles: special, reusable, or keep" in sp:
            return _MOCK_CATALOG_V3_JSON
        # v3 planner: "presentation content planner" + "fill_special" op type
        if "presentation content planner" in sp and "fill_special" in sp:
            return _MOCK_PLAN_V3_JSON
        if "template structure analyzer" in sp:    # old catalog (fill command)
            return _MOCK_CATALOG_JSON
        if "template analyzer" in sp:              # new catalog v2 (generate command)
            return _MOCK_CATALOG_V2_JSON
        if "slide content planner" in sp:          # new content generator (generate command)
            return _MOCK_GENERATE_PLAN_JSON
        if "presentation content planner" in sp:   # old catalog planner (fill command)
            return _MOCK_PLAN_CATALOG_JSON
        if "presentation analyst" in sp:
            return _MOCK_TEMPLATE_ANALYSIS_JSON
        if "presentation writer" in sp:
            return _MOCK_TEMPLATE_MAPPING_JSON
        if "knowledge distiller" in sp:
            return _MOCK_DISTILL_JSON
        # Layer 1 responses
        combined = (system_prompt + user_prompt).lower()
        if "spec" in combined and "slides" in combined and "audience" in combined:
            return _MOCK_SPEC_JSON
        return _MOCK_PLAN_JSON

    def generate_vision(
        self,
        system_prompt: str,
        image_blocks: list[dict],
        text_prompt: str,
    ) -> str:
        return _MOCK_VISION_RESPONSE


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def make_llm_client(mock: bool = False, model: str = "claude-sonnet-4-6") -> LLMClient:
    """Return a MockLLMClient or AnthropicLLMClient.

    Priority: explicit mock flag > POWERGEN_USE_MOCK env var > real client.
    """
    if mock or os.environ.get("POWERGEN_USE_MOCK") == "1":
        return MockLLMClient()
    return AnthropicLLMClient(model=model)
