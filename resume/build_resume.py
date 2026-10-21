#!/usr/bin/env python3
"""Generate the targeted resume (DOCX) for the Feishu healthcare KA sales role.

Usage:
    python3 resume/build_resume.py            # writes the .docx next to this script

Content lives in the data structures below so wording can be tuned without
touching the layout code.
"""
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT_DIR = Path(__file__).resolve().parent
OUT_NAME = "许增楠-医疗健康行业大客户销售-飞书.docx"

CJK_FONT = "微软雅黑"
LATIN_FONT = "Calibri"
ACCENT = RGBColor(0x1F, 0x4E, 0x79)
MUTED = RGBColor(0x59, 0x59, 0x59)
BODY_PT = 10
SMALL_PT = 9

# --------------------------------------------------------------------------
# Content
# --------------------------------------------------------------------------

NAME = "许增楠"
HEADLINE = "医疗健康行业-大客户销售（飞书）｜意向城市：深圳 / 广州"
CONTACT = [
    "手机：15626104764",
    "邮箱：15626104764@163.com",
    "企业管理硕士（市场营销 / 医药营销方向）",
    "英语 CET-6、BEC 中级｜粤语良好",
]

STRENGTHS = [
    (
        "医疗健康行业企业级客户销售经验：",
        "先后任职强生医疗、罗氏制药、视源医疗显示、辉瑞制药等医疗健康企业市场与销售端，"
        "覆盖医疗器械、制药、医疗 IT 硬件三大细分赛道及医疗机构、药企、器械企业三类目标客户；"
        "熟悉医院科室决策链与企业采购逻辑，具备从区域生意规划、重点客户开拓、渠道赋能到签单落地的全流程 B 端销售能力。",
    ),
    (
        "行业分析与解决方案讲解能力：",
        "企业管理硕士（医药营销方向），现任高校市场营销专任教师，主讲《数字营销》《营销渠道管理》等课程；"
        "主持中医药内容营销课题并在知网收录期刊发表成果，能够独立完成行业研究、形成策略洞察，"
        "并面向客户与专家完成结构化方案讲解（曾负责产品卫星会、科室会及学术活动宣讲）。",
    ),
    (
        "数字化与 AI 营销视角：",
        "研究方向为数字营销、AI 营销、医药营销，持续跟踪医疗大健康行业数字化转型、组织协同与营销技术趋势，"
        "能够把协同办公 / SaaS / AI 产品价值与制药、器械、医疗机构客户的业务场景结合，输出行业解决方案思路。",
    ),
    (
        "跨部门协作与大型项目落地：",
        "在强生期间协同市场部、渠道伙伴与临床专家落地 10+ 场大型学术活动（单场规模最高 40 万元），"
        "参与白皮书、手术指南编写等行业内容项目；沟通协调能力强，可覆盖华南及港澳地区客户沟通。",
    ),
]

EXPERIENCE = [
    {
        "org": "广州南方学院 · 商学院",
        "title": "市场营销专任教师",
        "period": "2024.02 – 至今",
        "place": "广州",
        "bullets": [
            "主讲《数字营销》《营销渠道管理》《电子商务原理》等课程，系统梳理 B 端营销、渠道管理与数字化转型方法论，"
            "持续产出面向医疗健康行业的营销策略研究。",
            "主持校级科研课题《中医药内容营销对消费意愿的影响机制研究》，成果发表于《商场现代化》（2026，知网收录），"
            "聚焦医药行业数字化内容营销路径与客户转化机制。",
            "协助参与工商管理专业人才培养方案制订与规划；长期面向不同对象进行结构化表达与方案讲解。",
        ],
    },
    {
        "org": "强生（上海）医疗器材有限公司 · 能量外科与微创外科",
        "title": "销售培训生",
        "period": "2022.07 – 2024.01",
        "place": "广州",
        "bullets": [
            "区域生意规划：基于业绩目标收集市场与竞品信息，完成区域市场分析、生意规划及销售策略制定与落地，业绩指标超额达成。",
            "重点客户开拓与维护：持续拜访核心客户及关键决策人，洞察客户痛点并提供针对性解决方案，传递产品与品牌价值，建立长期稳定的客户关系。",
            "渠道管理与赋能：协助经销商制定行动目标与计划，负责渠道人员产品知识培训，协同拜访重点客户，定期盘点渠道业绩并给予指导。",
            "学术活动与行业内容：围绕客户需求策划并全程落地 10+ 场大型学术活动（含全国性活动，单场规模最高 40 万元）；"
            "与市场部协同推进白皮书、手术指南编写及社交媒体科普等项目在区域落地。",
            "方案讲解：负责会议现场产品卫星会及日常科室会宣讲，具备面向临床专家与客户的专业讲解能力。",
        ],
    },
    {
        "org": "广州视源电子科技股份有限公司 · 医疗显示事业部",
        "title": "销售兼市场实习生",
        "period": "2021.01 – 2021.07",
        "place": "广州",
        "bullets": [
            "医疗机构新市场开拓：陌生拜访多家医院影像科，挖掘客户需求与关注点，传递公司品牌与产品价值，发掘商机并建立客户关系。",
            "产品与方案讲解：独立接待客户及渠道商参观产业园并负责公司与产品介绍；参加学术会议负责产品讲解。",
            "市场内容产出：独立负责 4 部宣传视频拍摄与产品新闻稿撰写，围绕临床核心需求提炼产品卖点，对接媒体、设计等外部供应商。",
        ],
    },
    {
        "org": "上海罗氏制药有限公司 · 淋巴瘤产品组",
        "title": "区域市场部实习生",
        "period": "2019.03 – 2020.01",
        "place": "广州",
        "bullets": [
            "对接多位市场部、销售部经理，汇总区域销量、学术活动、临床专家反馈、竞品动态等数据，输出销售月报与分析 PPT，为区域市场策略制定提供支持。",
            "协助区域市场活动项目的策划、组织与落地，系统学习药企市场推广与客户管理方法。",
        ],
    },
    {
        "org": "广州市中大管理咨询有限公司 · 市场部",
        "title": "市场分析实习生",
        "period": "2018.10 – 2019.03",
        "place": "广州",
        "bullets": [
            "参与“粤港澳大湾区人才创新发展大会”政府项目执行（物料组组长）；追踪行业与竞争对手动态，撰写峰会领导主持稿、致辞稿及管理咨询科普文章。",
        ],
    },
]

PROJECT = {
    "org": "梅州泽山口腔医院 5 年战略规划",
    "title": "导师助理",
    "period": "2018.10 – 2019.10",
    "place": "",
    "bullets": [
        "高层对接：直接对接医院决策层，收集战略目标、市场地位、竞争格局与管理模式等信息。",
        "行业与数据分析：研究国内外口腔行业政策、技术与商业模式动态；对比竞品价目、测算人均业绩产出与人员饱和度，"
        "搭建盈亏平衡、财务绩效与客流量分析表评估新分院发展情况。",
        "策略输出：完成 SWOT 分析与基于体验触点的患者就诊流程调研（访谈 + 问卷），形成可落地的优化建议。",
    ],
}

RESEARCH = [
    "主持校级课题《中医药内容营销对消费意愿的影响机制研究》。",
    "《中医药内容营销对消费意愿的影响机制：形而上与形而下内容的双路径作用》，《商场现代化》，2026。",
    "《透视直播电商解读营销的流变与永恒》，广东省社科联 2020 年岭南学术论坛（新营销·新经济）会议论文，获评优秀论文。",
    "《国产动漫火爆，动漫 IP 如何打动消费者》，《国际品牌观察》，2020（知网收录）。",
]

EDUCATION = [
    {
        "org": "广东外语外贸大学",
        "title": "企业管理 · 硕士",
        "period": "2019.08 – 2022.06",
        "place": "广州",
        "bullets": [
            "研究方向：市场营销（品牌营销、医药营销）；连续三年获校级奖学金（一等 2 次、二等 1 次）。",
        ],
    },
    {
        "org": "广州中医药大学",
        "title": "国际经济与贸易（医药方向） · 本科",
        "period": "2015.09 – 2019.06",
        "place": "广州",
        "bullets": [
            "GPA 3.8（专业排名第 2）；修读《药理学》《西医学概论》等医药课程；连续四年获校级奖学金。",
        ],
    },
]

SKILLS = [
    ("办公与分析工具：", "Word / PowerPoint（熟练）、Excel（数据透视表、常用函数）、SPSS、AMOS、Xmind。"),
    ("语言：", "英语（CET-6、BEC 中级）、粤语（良好）、普通话。"),
    ("个人特质：", "学习能力强、勤奋有韧劲、对结果负责；习惯主动复盘不足并持续改进。"),
]

# --------------------------------------------------------------------------
# Layout helpers
# --------------------------------------------------------------------------


def set_run_font(run, size=BODY_PT, bold=False, color=None, italic=False):
    run.font.name = LATIN_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:eastAsia"), CJK_FONT)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)


def para(doc, before=0, after=2, line=1.15, align=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if align is not None:
        p.alignment = align
    return p


def add_bottom_border(paragraph, color="1F4E79", size=8):
    ppr = paragraph._element.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    pbdr.append(bottom)
    ppr.append(pbdr)


def section_title(doc, text):
    p = para(doc, before=8, after=3)
    r = p.add_run(text)
    set_run_font(r, size=12.5, bold=True, color=ACCENT)
    add_bottom_border(p)
    p.paragraph_format.keep_with_next = True
    return p


def bullet(doc, text, lead=None, size=BODY_PT):
    p = para(doc, after=1.5, line=1.2)
    pf = p.paragraph_format
    pf.left_indent = Cm(0.45)
    pf.first_line_indent = Cm(-0.45)
    r = p.add_run("•\t")
    set_run_font(r, size=size, color=ACCENT)
    pf.tab_stops.add_tab_stop(Cm(0.45))
    if lead:
        r = p.add_run(lead)
        set_run_font(r, size=size, bold=True)
    r = p.add_run(text)
    set_run_font(r, size=size)
    return p


def entry_header(doc, org, title, period, place):
    """Org + title on the left, period/place right-aligned via tab stop."""
    p = para(doc, before=4, after=1)
    section = doc.sections[0]
    usable = section.page_width - section.left_margin - section.right_margin
    p.paragraph_format.tab_stops.add_tab_stop(usable, WD_TAB_ALIGNMENT.RIGHT)
    r = p.add_run(org)
    set_run_font(r, size=11, bold=True)
    r = p.add_run("  |  " + title)
    set_run_font(r, size=10.5, bold=True, color=ACCENT)
    right = period + ("  |  " + place if place else "")
    r = p.add_run("\t" + right)
    set_run_font(r, size=SMALL_PT + 0.5, color=MUTED)
    return p


def entry(doc, item):
    # Keep each entry (header + bullets) on one page so no bullet gets orphaned.
    header = entry_header(doc, item["org"], item["title"], item["period"], item["place"])
    header.paragraph_format.keep_with_next = True
    bullets = [bullet(doc, b) for b in item["bullets"]]
    for p in bullets[:-1]:
        p.paragraph_format.keep_with_next = True
    for p in bullets:
        p.paragraph_format.keep_together = True


def header_block(doc):
    p = para(doc, after=0, line=1.0)
    r = p.add_run(NAME)
    set_run_font(r, size=22, bold=True, color=ACCENT)
    r = p.add_run("    求职意向：" + HEADLINE)
    set_run_font(r, size=10.5, bold=True)

    table = doc.add_table(rows=2, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.LEFT
    table.autofit = True
    for i, text in enumerate(CONTACT):
        cell = table.cell(i // 2, i % 2)
        cp = cell.paragraphs[0]
        cp.paragraph_format.space_after = Pt(0)
        cp.paragraph_format.space_before = Pt(1)
        r = cp.add_run(text)
        set_run_font(r, size=SMALL_PT + 0.5, color=MUTED)
    sep = para(doc, before=2, after=0, line=1.0)
    add_bottom_border(sep, size=12)


def build():
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = section.right_margin = Cm(1.7)
    section.top_margin = Cm(1.4)
    section.bottom_margin = Cm(1.3)

    normal = doc.styles["Normal"]
    normal.font.name = LATIN_FONT
    normal.font.size = Pt(BODY_PT)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CJK_FONT)

    header_block(doc)

    section_title(doc, "核心优势")
    for lead, text in STRENGTHS:
        bullet(doc, text, lead=lead)

    section_title(doc, "工作经历")
    for item in EXPERIENCE:
        entry(doc, item)

    section_title(doc, "项目经历")
    entry(doc, PROJECT)

    section_title(doc, "科研课题与论文")
    for text in RESEARCH:
        bullet(doc, text, size=SMALL_PT + 0.5)

    section_title(doc, "教育背景")
    for item in EDUCATION:
        entry(doc, item)

    section_title(doc, "技能与语言")
    for lead, text in SKILLS:
        bullet(doc, text, lead=lead)

    out = OUT_DIR / OUT_NAME
    doc.save(out)
    print(f"wrote {out}")
    return out


if __name__ == "__main__":
    build()
