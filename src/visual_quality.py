from __future__ import annotations

import math
from typing import Any

DEFAULT_GIS_FIGURES = (
    ("2.1.1 区位条件", "区位条件分析图", "satellite_gis"),
    ("2.1.2 土地用途", "现状功能与调查单元分布图", "gis_generated"),
    ("2.1.3 建筑使用", "建筑年代与更新敏感性分析图", "gis_generated"),
    ("2.1.4 人口构成", "人口老龄化分布图", "gis_generated"),
    ("2.1.5 公共服务设施", "公共服务设施覆盖分析图", "gis_generated"),
    ("2.1.6 公共空间", "公共空间与绿色资源线索图", "gis_generated"),
    ("2.1.10 道路交通", "道路交通与慢行联系分析图", "satellite_gis"),
    ("2.2 体检评估", "片区体检问题线索综合图", "gis_generated"),
    ("2.3 潜力资源识别与评价", "更新潜力资源识别图", "gis_generated"),
)

DEFAULT_PLACEHOLDERS = (
    (
        "2.1.2 土地用途",
        "现状土地用途与权属核验图",
        ["三调现状地类", "法定控规", "地籍与权属", "现状建筑使用调查"],
    ),
    (
        "2.1.8 历史文化资源",
        "历史文化资源普查与价值评估图",
        ["文保与历史建筑名录", "地方志与工业遗产线索", "现场踏勘与测绘建档"],
    ),
    (
        "2.1.11 市政设施",
        "地下市政管网与韧性风险图",
        ["给排水", "燃气", "电力通信", "积水与抢险记录"],
    ),
    (
        "2.4 更新意愿调查",
        "居民与权利人更新意愿分析图",
        ["全覆盖问卷", "产权人与经营主体意见", "社区议事与部门座谈"],
    ),
)


def mercator_world(lon: float, lat: float) -> tuple[float, float]:
    x = (lon + 180.0) / 360.0
    siny = min(max(math.sin(math.radians(lat)), -0.9999), 0.9999)
    y = 0.5 - math.log((1 + siny) / (1 - siny)) / (4 * math.pi)
    return x, y


def inverse_mercator_world(x: float, y: float) -> tuple[float, float]:
    lon = x * 360.0 - 180.0
    n = math.pi - 2.0 * math.pi * y
    lat = math.degrees(math.atan(math.sinh(n)))
    return lon, lat


def fit_web_mercator_bounds(
    bounds: list[float] | tuple[float, float, float, float],
    width: int,
    height: int,
) -> list[float]:
    """Expand, never stretch, a lon/lat viewport to the canvas aspect ratio."""
    if width <= 0 or height <= 0:
        raise ValueError("成图宽高必须大于0")
    minlon, minlat, maxlon, maxlat = map(float, bounds)
    if minlon >= maxlon or minlat >= maxlat:
        raise ValueError("bounds顺序无效")
    x0, y0 = mercator_world(minlon, maxlat)
    x1, y1 = mercator_world(maxlon, minlat)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    span_x, span_y = x1 - x0, y1 - y0
    target = width / height
    if span_x / span_y < target:
        span_x = span_y * target
    else:
        span_y = span_x / target
    left, right = cx - span_x / 2, cx + span_x / 2
    top, bottom = cy - span_y / 2, cy + span_y / 2
    minlon2, maxlat2 = inverse_mercator_world(left, top)
    maxlon2, minlat2 = inverse_mercator_world(right, bottom)
    return [minlon2, minlat2, maxlon2, maxlat2]


def map_aspect_ratio_check(
    bounds: list[float] | tuple[float, float, float, float],
    width: int,
    height: int,
    tolerance: float = 1e-6,
) -> dict[str, Any]:
    minlon, minlat, maxlon, maxlat = map(float, bounds)
    x0, y0 = mercator_world(minlon, maxlat)
    x1, y1 = mercator_world(maxlon, minlat)
    canvas_ratio = width / height
    viewport_ratio = (x1 - x0) / (y1 - y0)
    relative_error = abs(viewport_ratio / canvas_ratio - 1)
    return {
        "canvas_ratio": canvas_ratio,
        "mercator_viewport_ratio": viewport_ratio,
        "relative_error": relative_error,
        "tolerance": tolerance,
        "passed": relative_error <= tolerance,
    }


def make_visual_workplan(project: dict[str, Any]) -> dict[str, Any]:
    supplied = project.get("visual_requirements", {})
    rendering = {
        "satellite_basemap_required": supplied.get(
            "satellite_basemap_required", True
        ),
        "source_crs": supplied.get("source_crs", "以源GIS数据为准并记录"),
        "display_crs": supplied.get("display_crs", "EPSG:3857"),
        "preserve_aspect_ratio": supplied.get("preserve_aspect_ratio", True),
        "allow_nonuniform_scaling": supplied.get(
            "allow_nonuniform_scaling", False
        ),
        "aspect_ratio_tolerance": supplied.get(
            "aspect_ratio_tolerance", 1e-6
        ),
        "crs_identification_required": True,
        "crs_transform_log_required": True,
        "scale_bar_method": "依据成图投影和中心纬度计算",
        "required_map_elements": supplied.get(
            "required_map_elements",
            ["边界", "道路", "水系", "指北针", "比例尺", "底图署名"],
        ),
    }
    figures: list[dict[str, Any]] = []
    for index, (section, title, evidence_class) in enumerate(
        DEFAULT_GIS_FIGURES, start=1
    ):
        figures.append(
            {
                "figure_id": f"VIS-{index:02d}",
                "section": section,
                "title": title,
                "evidence_class": evidence_class,
                "production_method": "优先已有正式图纸，否则由现有GIS数据生成",
                "status": "planned",
                "field_verification_required": True,
            }
        )
    start = len(figures) + 1
    for offset, (section, title, required_data) in enumerate(
        DEFAULT_PLACEHOLDERS
    ):
        figures.append(
            {
                "figure_id": f"VIS-{start + offset:02d}",
                "section": section,
                "title": title,
                "evidence_class": "placeholder_brief",
                "production_method": "资料不足时插入制图任务预留图框",
                "status": "placeholder_required",
                "required_data": required_data,
                "drawing_requirements": [
                    "明确建议比例尺",
                    "明确图层与表达要素",
                    "标注资料待补和不得形成现状认定",
                ],
            }
        )
    for photo_index, photo in enumerate(supplied.get("network_photos", []), 1):
        figures.append(
            {
                "figure_id": f"PHOTO-{photo_index:02d}",
                "section": photo.get("section", "待分配"),
                "title": photo.get("object_name", "网络照片线索"),
                "evidence_class": "network_photo_clue",
                "production_method": "网络检索",
                "status": "clue_only",
                "source_page": photo.get("source_page"),
                "source_url": photo.get("source_url"),
                "retrieved_at": photo.get("retrieved_at"),
                "usage_rights_status": photo.get(
                    "usage_rights_status", "needs_review"
                ),
                "field_shotlist": photo.get(
                    "field_shotlist",
                    {
                        "object_name": photo.get("object_name"),
                        "location": "待现场定位",
                        "view_direction": "待现场确定",
                    },
                ),
                "location_match_status": photo.get(
                    "location_match_status", "needs_review"
                ),
                "field_verification_required": True,
            }
        )
    return {
        "version": "2026-07-27",
        "project_id": project["project_id"],
        "rendering_policy": rendering,
        "figures": figures,
        "qa_status": "待制图后逐张与逐页检查",
    }


def validate_visual_workplan(plan: dict[str, Any]) -> dict[str, Any]:
    rendering = plan["rendering_policy"]
    figures = plan["figures"]
    photo_clues = [
        item for item in figures if item["evidence_class"] == "network_photo_clue"
    ]
    placeholders = [
        item for item in figures if item["evidence_class"] == "placeholder_brief"
    ]
    checks = [
        {
            "check": "禁止卫片和GIS图层非等比例拉伸",
            "passed": rendering["preserve_aspect_ratio"]
            and not rendering["allow_nonuniform_scaling"],
        },
        {
            "check": "卫片成图设置比例误差阈值",
            "passed": 0 < float(rendering["aspect_ratio_tolerance"]) <= 1e-6,
        },
        {
            "check": "要求记录源坐标系、转换链路和比例尺依据",
            "passed": rendering["crs_identification_required"]
            and rendering["crs_transform_log_required"]
            and bool(rendering["scale_bar_method"]),
        },
        {
            "check": "缺失图纸预留图框包含资料与制图要求",
            "passed": all(
                item.get("required_data") and item.get("drawing_requirements")
                for item in placeholders
            ),
        },
        {
            "check": "网络照片具备来源与现场复核标记",
            "passed": all(
                item.get("source_page")
                and item.get("source_url")
                and item.get("retrieved_at")
                and item.get("usage_rights_status")
                and item.get("field_shotlist")
                and item.get("field_verification_required")
                for item in photo_clues
            ),
        },
        {
            "check": "专题图具备证据类型和所属小节",
            "passed": all(
                item.get("section") and item.get("evidence_class")
                for item in figures
            ),
        },
    ]
    return {
        "passed": all(item["passed"] for item in checks),
        "checks": checks,
        "review_items": [
            "制图时记录投影视口、画布尺寸和比例误差并执行运行时校核。",
            "网络照片逐图核对对象、城市、拍摄时点和现场现状。",
            "DOCX交付前执行渲染逐页检查；渲染失败时披露并执行结构替代检查。",
        ],
    }
