from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LOCAL_DEPS = ROOT / ".deps"
if LOCAL_DEPS.exists():
    sys.path.insert(0, str(LOCAL_DEPS))
sys.path.insert(0, str(ROOT / "src"))

from kb_index import DB_PATH, KnowledgeBase, build_index
from visual_quality import make_visual_workplan, validate_visual_workplan


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate(project: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in (
        "project_id",
        "project_name",
        "location",
        "planning_intents",
        "site",
        "controls",
        "program_mix",
        "cost_assumptions",
    ):
        if field not in project:
            errors.append(f"缺少字段：{field}")
    if errors:
        return errors
    site_area = float(project["site"].get("area_m2", 0))
    if site_area <= 0:
        errors.append("site.area_m2 必须大于 0")
    mix_total = sum(float(value) for value in project["program_mix"].values())
    if not math.isclose(mix_total, 1.0, abs_tol=0.001):
        errors.append(f"program_mix 合计必须为 1，当前为 {mix_total:.4f}")
    controls = project["controls"]
    for ratio_name in (
        "max_building_density",
        "min_green_ratio",
        "public_space_ratio",
    ):
        value = float(controls.get(ratio_name, -1))
        if not 0 <= value <= 1:
            errors.append(f"controls.{ratio_name} 必须在 0 到 1 之间")
    if float(controls["target_far"]) > float(controls["max_far"]):
        errors.append("target_far 不得高于 max_far")
    visual = project.get("visual_requirements", {})
    if visual.get("preserve_aspect_ratio") is False:
        errors.append("visual_requirements.preserve_aspect_ratio 必须为 true")
    if visual.get("allow_nonuniform_scaling") is True:
        errors.append("禁止卫片或GIS图层非等比例拉伸")
    tolerance = float(visual.get("aspect_ratio_tolerance", 1e-6))
    if not 0 < tolerance <= 1e-6:
        errors.append("卫片投影视口比例误差阈值必须在 0 到 1e-6 之间")
    return errors


def retrieve_evidence(
    kb: KnowledgeBase, project: dict[str, Any]
) -> list[dict[str, Any]]:
    query_specs: list[tuple[str, str | None, int]] = [
        ("城市更新片区策划 主要内容 成果形式", "A", 4),
        ("城市更新规划 实施 项目库 运营", "A", 3),
        ("贵州 城市更新 片区 项目建设", "B", 4),
        ("卫片 GIS 等比例 照片 预留图纸 成果质检", "C", 6),
    ]
    for intent in project["planning_intents"]:
        query_specs.append((intent, None, 2))

    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query, library, limit in query_specs:
        for result in kb.search(query, limit=limit, knowledge_base=library):
            if result["chunk_id"] in seen:
                continue
            result["query"] = query
            evidence.append(result)
            seen.add(result["chunk_id"])
    return evidence


def calculate_metrics(project: dict[str, Any]) -> dict[str, Any]:
    site = project["site"]
    controls = project["controls"]
    area = float(site["area_m2"])
    target_far = min(float(controls["target_far"]), float(controls["max_far"]))
    total_gfa = area * target_far
    max_footprint = area * float(controls["max_building_density"])
    provisional_storeys = max(1, math.ceil(total_gfa / max(max_footprint, 1)))
    footprint = total_gfa / provisional_storeys
    actual_density = footprint / area
    public_space = area * float(controls["public_space_ratio"])
    green_area = area * float(controls["min_green_ratio"])
    parking = math.ceil(
        total_gfa / 1000 * float(controls["parking_spaces_per_1000m2"])
    )
    program_gfa = {
        name: round(total_gfa * float(ratio), 2)
        for name, ratio in project["program_mix"].items()
    }
    return {
        "site_area_m2": round(area, 2),
        "target_far": round(target_far, 4),
        "max_far": float(controls["max_far"]),
        "total_gfa_m2": round(total_gfa, 2),
        "existing_gfa_m2": round(float(site.get("existing_gfa_m2", 0)), 2),
        "new_gfa_m2": round(
            max(0.0, total_gfa - float(site.get("existing_gfa_m2", 0))), 2
        ),
        "building_footprint_m2": round(footprint, 2),
        "building_density": round(actual_density, 4),
        "max_building_density": float(controls["max_building_density"]),
        "average_storeys": provisional_storeys,
        "average_height_m": round(
            provisional_storeys * float(controls["average_storey_height_m"]), 2
        ),
        "green_area_m2": round(green_area, 2),
        "green_ratio": float(controls["min_green_ratio"]),
        "public_space_m2": round(public_space, 2),
        "public_space_ratio": float(controls["public_space_ratio"]),
        "parking_spaces": parking,
        "program_gfa_m2": program_gfa,
        "calculation_notes": [
            "容积率按总建筑面积/片区总用地面积计算。",
            "绿地与公共空间可能重叠，不应直接相加作为剩余用地扣减。",
            "平均层数按满足建筑密度上限的整数层向上取整。",
        ],
    }


def calculate_finance(
    project: dict[str, Any], metrics: dict[str, Any]
) -> dict[str, Any]:
    costs = project["cost_assumptions"]
    site = project["site"]
    new_cost = (
        metrics["new_gfa_m2"] * float(costs["new_construction_yuan_m2"])
    )
    renovation_cost = float(site.get("renovation_gfa_m2", 0)) * float(
        costs["renovation_yuan_m2"]
    )
    public_cost = metrics["public_space_m2"] * float(
        costs["public_space_yuan_m2"]
    )
    direct_base = new_cost + renovation_cost + public_cost
    other_cost = direct_base * float(costs["other_cost_ratio"])
    contingency = (direct_base + other_cost) * float(costs["contingency_ratio"])
    total_investment = direct_base + other_cost + contingency
    direct_revenue = (
        metrics["new_gfa_m2"]
        * float(costs["direct_value_yuan_m2"])
        * float(costs["revenue_realization_ratio"])
    )
    gap = total_investment - direct_revenue
    return {
        "new_construction_cost_yuan": round(new_cost, 2),
        "renovation_cost_yuan": round(renovation_cost, 2),
        "public_space_cost_yuan": round(public_cost, 2),
        "other_cost_yuan": round(other_cost, 2),
        "contingency_yuan": round(contingency, 2),
        "total_investment_yuan": round(total_investment, 2),
        "direct_revenue_yuan": round(direct_revenue, 2),
        "funding_gap_yuan": round(gap, 2),
        "cost_per_total_gfa_yuan_m2": round(
            total_investment / max(metrics["total_gfa_m2"], 1), 2
        ),
        "warning": (
            "本测算不含征拆、土地、融资利息、税费和长期运营现金流，"
            "仅用于策划阶段方案比较。"
        ),
    }


def make_projects(project: dict[str, Any], metrics: dict[str, Any]) -> list[dict[str, Any]]:
    templates = {
        "老旧小区改造": ("存量住区综合提升", "近期启动", "改造", "公共服务与环境提升"),
        "完整社区补短板": ("完整社区设施补短板", "近期启动", "新建+改造", "社区公共服务"),
        "历史文化保护传承": ("历史文化资源保护活化", "重点实施", "保护修缮", "文化与运营"),
        "存量产业空间活化": ("低效产业空间活化", "重点实施", "功能置换", "产业与就业"),
    }
    projects: list[dict[str, Any]] = []
    investment = metrics["total_gfa_m2"]
    for index, intent in enumerate(project["planning_intents"], start=1):
        name, stage, method, benefit = templates.get(
            intent, (f"{intent}专项", "储备研究", "综合整治", "综合效益")
        )
        projects.append(
            {
                "project_code": f"{project['project_id']}-P{index:02d}",
                "project_name": name,
                "planning_intent": intent,
                "implementation_stage": stage,
                "renewal_method": method,
                "indicative_gfa_m2": round(
                    investment / max(1, len(project["planning_intents"])), 2
                ),
                "expected_benefit": benefit,
                "status": "策划储备",
                "review_required": "是",
            }
        )
    return projects


def make_massing(project: dict[str, Any], metrics: dict[str, Any]) -> dict[str, Any]:
    boundary = project["site"].get("boundary_geojson")
    if not boundary:
        return {"type": "FeatureCollection", "features": []}
    try:
        from shapely import affinity
        from shapely.geometry import box, mapping, shape
    except ImportError:
        feature = dict(boundary)
        feature["properties"] = {
            **feature.get("properties", {}),
            "height_m": metrics["average_height_m"],
            "storeys": metrics["average_storeys"],
            "gfa_m2": metrics["total_gfa_m2"],
        }
        return {"type": "FeatureCollection", "features": [feature]}

    site_shape = shape(boundary["geometry"])
    min_x, min_y, max_x, max_y = site_shape.bounds
    total_width = max_x - min_x
    footprint_ratio = metrics["building_footprint_m2"] / max(
        metrics["site_area_m2"], 1
    )
    shrink = math.sqrt(min(1.0, footprint_ratio))
    cursor = min_x
    features: list[dict[str, Any]] = []
    items = list(project["program_mix"].items())
    for index, (name, ratio) in enumerate(items):
        next_x = max_x if index == len(items) - 1 else cursor + total_width * ratio
        strip = site_shape.intersection(box(cursor, min_y, next_x, max_y))
        block = affinity.scale(
            strip, xfact=shrink, yfact=shrink, origin="centroid"
        )
        gfa = metrics["program_gfa_m2"][name]
        footprint = block.area
        storeys = max(1, math.ceil(gfa / max(footprint, 1)))
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "block_id": f"B{index + 1:02d}",
                    "program": name,
                    "gfa_m2": gfa,
                    "footprint_m2": round(footprint, 2),
                    "storeys": storeys,
                    "height_m": round(
                        storeys
                        * float(project["controls"]["average_storey_height_m"]),
                        2,
                    ),
                    "model_status": "策划体块参数",
                },
                "geometry": mapping(block),
            }
        )
        cursor = next_x
    return {"type": "FeatureCollection", "features": features}


def make_quality(
    project: dict[str, Any],
    metrics: dict[str, Any],
    evidence: list[dict[str, Any]],
    massing: dict[str, Any],
    visual_review: dict[str, Any],
) -> dict[str, Any]:
    checks = [
        {
            "check": "业态配比合计",
            "passed": math.isclose(
                sum(project["program_mix"].values()), 1.0, abs_tol=0.001
            ),
        },
        {
            "check": "目标容积率不超过上限",
            "passed": metrics["target_far"] <= metrics["max_far"],
        },
        {
            "check": "建筑密度不超过上限",
            "passed": metrics["building_density"]
            <= metrics["max_building_density"] + 1e-6,
        },
        {"check": "存在可追溯证据", "passed": bool(evidence)},
        {
            "check": "体块建筑面积与指标一致",
            "passed": math.isclose(
                sum(
                    feature["properties"]["gfa_m2"]
                    for feature in massing["features"]
                ),
                metrics["total_gfa_m2"],
                rel_tol=0.001,
            )
            if massing["features"]
            else True,
        },
        *visual_review["checks"],
    ]
    hard_failures = [item for item in checks if not item["passed"]]
    controls_are_assumptions = (
        project["controls"].get("source_status") == "model_assumption"
    )
    status = "不通过" if hard_failures else (
        "带条件通过" if controls_are_assumptions else "通过"
    )
    return {
        "status": status,
        "checks": checks,
        "review_items": [
            "核实容积率、建筑密度、绿地率和停车指标的法定依据。",
            "补充现状权属、建筑质量、人口和公共服务设施调查。",
            "核实历史文化资源名录、保护范围和建设控制要求。",
            "补充征拆、土地、融资利息、税费和运营现金流测算。",
            *visual_review["review_items"],
        ],
    }


def write_report(
    path: Path,
    project: dict[str, Any],
    metrics: dict[str, Any],
    finance: dict[str, Any],
    projects: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    quality: dict[str, Any],
    visual_plan: dict[str, Any],
) -> None:
    mix_rows = "\n".join(
        f"| {name} | {project['program_mix'][name]:.1%} | {value:,.0f} |"
        for name, value in metrics["program_gfa_m2"].items()
    )
    project_rows = "\n".join(
        f"| {item['project_code']} | {item['project_name']} | "
        f"{item['implementation_stage']} | {item['renewal_method']} |"
        for item in projects
    )
    evidence_rows_list = []
    for index, item in enumerate(evidence[:16], start=1):
        locator = item.get("source_locator")
        if not locator:
            locator = f"PDF 第 {item['pdf_page']} 页"
        evidence_rows_list.append(
            f"{index}. 《{item['source_file']}》{locator}，"
            f"{item['document_status']}，{item['extraction_method']} 抽取，"
            f"置信度 {item['confidence']:.3f}：{item['quotation']}"
        )
    evidence_rows = "\n".join(evidence_rows_list)
    visual_rows = "\n".join(
        f"| {item['figure_id']} | {item['section']} | {item['title']} | "
        f"{item['evidence_class']} | {item['status']} |"
        for item in visual_plan["figures"]
    )
    report = f"""# {project['project_name']}片区更新策划与指标测算报告

## 1. 项目概况

- 项目编号：{project['project_id']}
- 区位：{project['location']}
- 片区面积：{metrics['site_area_m2']:,.0f} 平方米
- 策划目标：{'、'.join(project['planning_intents'])}
- 成果质检：{quality['status']}

## 2. 策划结论

本轮以存量提质、公共服务补短板、文化保护活化和产业空间更新为主线。
按当前策划假设，目标容积率为 {metrics['target_far']:.2f}，总建筑面积约
{metrics['total_gfa_m2']:,.0f} 平方米，新增建筑面积约
{metrics['new_gfa_m2']:,.0f} 平方米。控制指标目前标记为
`{project['controls'].get('source_status', 'model_assumption')}`，在进入正式方案前必须核实法定依据。

## 3. 指标测算

| 指标 | 测算值 |
| --- | ---: |
| 总用地面积 | {metrics['site_area_m2']:,.0f} m² |
| 目标容积率 / 上限 | {metrics['target_far']:.2f} / {metrics['max_far']:.2f} |
| 总建筑面积 | {metrics['total_gfa_m2']:,.0f} m² |
| 建筑密度 / 上限 | {metrics['building_density']:.1%} / {metrics['max_building_density']:.1%} |
| 平均层数 / 高度 | {metrics['average_storeys']} 层 / {metrics['average_height_m']:.1f} m |
| 绿地面积 / 绿地率 | {metrics['green_area_m2']:,.0f} m² / {metrics['green_ratio']:.1%} |
| 公共空间 | {metrics['public_space_m2']:,.0f} m² |
| 停车位 | {metrics['parking_spaces']:,} 个 |

## 4. 功能业态

| 功能 | 配比 | 建筑面积（m²） |
| --- | ---: | ---: |
{mix_rows}

## 5. 项目库

| 编码 | 项目名称 | 时序 | 更新方式 |
| --- | --- | --- | --- |
{project_rows}

## 6. 投资与平衡

| 项目 | 金额（亿元） |
| --- | ---: |
| 新建工程 | {finance['new_construction_cost_yuan'] / 1e8:.2f} |
| 存量改造 | {finance['renovation_cost_yuan'] / 1e8:.2f} |
| 公共空间 | {finance['public_space_cost_yuan'] / 1e8:.2f} |
| 其他费用 | {finance['other_cost_yuan'] / 1e8:.2f} |
| 预备费 | {finance['contingency_yuan'] / 1e8:.2f} |
| 总投资 | {finance['total_investment_yuan'] / 1e8:.2f} |
| 直接收益 | {finance['direct_revenue_yuan'] / 1e8:.2f} |
| 资金缺口 | {finance['funding_gap_yuan'] / 1e8:.2f} |

{finance['warning']}

## 7. 知识库证据

{evidence_rows}

## 8. 图件与照片工作计划

卫片和GIS图件必须统一使用投影视口，不得分别拉伸。网络照片仅作为线索，
缺失资料对应图件必须以制图任务预留图框表达。

| 编号 | 所属小节 | 图件 | 证据类型 | 状态 |
| --- | --- | --- | --- | --- |
{visual_rows}

## 9. 假设与人工复核

- 现阶段控制指标、业态配比和成本收益单价均为策划测算输入，不是法定结论。
- 《贵州省“十五五”城市更新行动规划》源文件为征求意见稿。
- 《城市更新规划编制工作手册》为扫描件，引用前应查看对应 PDF 页面。
- 需补充现状权属、建筑安全、历史文化、地质灾害、交通和市政专项调查。
- 空间体块为参数化示意，不替代控规、建筑方案或测绘成果。
"""
    path.write_text(report, encoding="utf-8")


def run(project_path: Path, output_dir: Path) -> dict[str, Any]:
    project = load_json(project_path)
    errors = validate(project)
    if errors:
        raise ValueError("；".join(errors))
    if not DB_PATH.exists():
        build_index()
    kb = KnowledgeBase()
    evidence = retrieve_evidence(kb, project)
    metrics = calculate_metrics(project)
    finance = calculate_finance(project, metrics)
    projects = make_projects(project, metrics)
    massing = make_massing(project, metrics)
    visual_plan = make_visual_workplan(project)
    visual_review = validate_visual_workplan(visual_plan)
    quality = make_quality(
        project, metrics, evidence, massing, visual_review
    )
    assumptions = {
        "controls": project["controls"],
        "program_mix": project["program_mix"],
        "cost_assumptions": project["cost_assumptions"],
        "status": "待人工复核",
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "scenario.json": {
            "project": {
                "project_id": project["project_id"],
                "project_name": project["project_name"],
                "location": project["location"],
                "planning_intents": project["planning_intents"],
            },
            "metrics": metrics,
            "finance": finance,
            "assumption_register": assumptions,
        },
        "evidence.json": evidence,
        "massing.geojson": massing,
        "visual_workplan.json": visual_plan,
        "quality_report.json": quality,
    }
    for name, payload in artifacts.items():
        with (output_dir / name).open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    with (output_dir / "project_list.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(projects[0].keys()))
        writer.writeheader()
        writer.writerows(projects)

    write_report(
        output_dir / "report.md",
        project,
        metrics,
        finance,
        projects,
        evidence,
        quality,
        visual_plan,
    )
    return {
        "output_dir": str(output_dir),
        "quality_status": quality["status"],
        "artifacts": sorted(path.name for path in output_dir.iterdir()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="片区策划端到端工作流")
    parser.add_argument("project", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.project.resolve(), args.output.resolve()),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
