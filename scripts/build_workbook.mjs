import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(import.meta.dirname, "..");
const outputDir = process.argv[2]
  ? path.resolve(process.argv[2])
  : path.join(root, "output", "demo");
const previewDir = path.join(root, "tmp", "xlsx_previews");
const scenario = JSON.parse(await fs.readFile(path.join(outputDir, "scenario.json"), "utf8"));
const evidence = JSON.parse(await fs.readFile(path.join(outputDir, "evidence.json"), "utf8"));
const quality = JSON.parse(await fs.readFile(path.join(outputDir, "quality_report.json"), "utf8"));
const projectCsv = await fs.readFile(path.join(outputDir, "project_list.csv"), "utf8");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let value = "";
  let quoted = false;
  const clean = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < clean.length; i++) {
    const ch = clean[i];
    if (ch === '"') {
      if (quoted && clean[i + 1] === '"') {
        value += '"';
        i += 1;
      } else {
        quoted = !quoted;
      }
    } else if (ch === "," && !quoted) {
      row.push(value);
      value = "";
    } else if ((ch === "\n" || ch === "\r") && !quoted) {
      if (ch === "\r" && clean[i + 1] === "\n") i += 1;
      row.push(value);
      if (row.some((cell) => cell !== "")) rows.push(row);
      row = [];
      value = "";
    } else {
      value += ch;
    }
  }
  if (value || row.length) {
    row.push(value);
    rows.push(row);
  }
  return rows;
}

const projects = parseCsv(projectCsv);
const project = scenario.project;
const metrics = scenario.metrics;
const assumptions = scenario.assumption_register;
const costs = assumptions.cost_assumptions;
const controls = assumptions.controls;
const mixEntries = Object.entries(assumptions.program_mix);

const wb = Workbook.create();
const cover = wb.worksheets.add("封面");
const inputs = wb.worksheets.add("参数输入");
const indicators = wb.worksheets.add("指标测算");
const finance = wb.worksheets.add("财务测算");
const projectSheet = wb.worksheets.add("项目库");
const sourceSheet = wb.worksheets.add("证据与复核");
const checks = wb.worksheets.add("检查");

const navy = "#203748";
const blue = "#2E74B5";
const lightBlue = "#E8EEF5";
const lightGray = "#F2F4F7";
const white = "#FFFFFF";
const green = "#008000";
const inputBlue = "#0000FF";
const red = "#C00000";
const yellow = "#FFF2CC";
const border = "#D9E1E8";

function styleTitle(sheet, range, fill = navy) {
  sheet.getRange(range).format = {
    fill,
    font: { bold: true, color: white, size: 16 },
    verticalAlignment: "center",
  };
}

function styleHeader(sheet, range) {
  sheet.getRange(range).format = {
    fill: lightBlue,
    font: { bold: true, color: navy },
    borders: { preset: "outside", style: "thin", color: border },
    verticalAlignment: "center",
    wrapText: true,
  };
}

function styleSection(sheet, range) {
  sheet.getRange(range).format = {
    fill: navy,
    font: { bold: true, color: white },
  };
}

for (const sheet of [cover, inputs, indicators, finance, projectSheet, sourceSheet, checks]) {
  sheet.showGridLines = false;
}

cover.mergeCells("A1:H2");
cover.getRange("A1").values = [[project.project_name]];
styleTitle(cover, "A1:H2");
cover.getRange("A1:H2").format.font.size = 22;
cover.mergeCells("A3:H3");
cover.getRange("A3").values = [["片区更新策划、项目库与财务测算工作簿"]];
cover.getRange("A3:H3").format = {
  font: { bold: true, color: blue, size: 13 },
  verticalAlignment: "center",
};
cover.getRange("A5:B10").values = [
  ["项目编号", project.project_id],
  ["区位", project.location],
  ["成果状态", quality.status],
  ["模型版本", "0.1.0"],
  ["单位", "面积：m²；金额：元"],
  ["使用边界", "策划测算，不替代法定规划与投资决策"],
];
cover.getRange("A5:A10").format = { fill: lightGray, font: { bold: true, color: navy } };
cover.getRange("A5:B10").format.borders = { preset: "outside", style: "thin", color: border };
cover.getRange("B5:B10").format.wrapText = true;
cover.mergeCells("A12:H12");
cover.getRange("A12").values = [["使用顺序：参数输入 → 指标测算 → 财务测算 → 项目库 → 证据与复核 → 检查"]];
cover.getRange("A12:H12").format = { fill: yellow, font: { bold: true, color: navy }, wrapText: true };
cover.getRange("A:A").format.columnWidth = 20;
cover.getRange("B:B").format.columnWidth = 52;
cover.getRange("C:H").format.columnWidth = 12;

inputs.mergeCells("A1:D2");
inputs.getRange("A1").values = [["参数输入（蓝色字体为可编辑假设）"]];
styleTitle(inputs, "A1:D2");
inputs.getRange("A4:D4").values = [["类别", "参数", "数值", "单位/状态"]];
styleHeader(inputs, "A4:D4");
const inputRows = [
  ["场地", "总用地面积", metrics.site_area_m2, "m²"],
  ["场地", "现状建筑面积", metrics.existing_gfa_m2, "m²"],
  ["场地", "现状改造面积", 120000, "m²"],
  ["控制", "目标容积率", controls.target_far, controls.source_status],
  ["控制", "容积率上限", controls.max_far, controls.source_status],
  ["控制", "建筑密度上限", controls.max_building_density, controls.source_status],
  ["控制", "绿地率下限", controls.min_green_ratio, controls.source_status],
  ["控制", "公共空间比例", controls.public_space_ratio, controls.source_status],
  ["控制", "平均层高", controls.average_storey_height_m, "m"],
  ["控制", "停车位/千平方米", controls.parking_spaces_per_1000m2, "个/千m²"],
  ["成本", "新建单价", costs.new_construction_yuan_m2, "元/m²"],
  ["成本", "改造单价", costs.renovation_yuan_m2, "元/m²"],
  ["成本", "公共空间单价", costs.public_space_yuan_m2, "元/m²"],
  ["成本", "其他费用率", costs.other_cost_ratio, "%"],
  ["成本", "预备费率", costs.contingency_ratio, "%"],
  ["收益", "直接价值单价", costs.direct_value_yuan_m2, "元/m²"],
  ["收益", "收益实现比例", costs.revenue_realization_ratio, "%"],
];
inputs.getRange(`A5:D${4 + inputRows.length}`).values = inputRows;
inputs.getRange(`C5:C${4 + inputRows.length}`).format.font = { color: inputBlue };
inputs.getRange("C10:C12").format.numberFormat = "0.0%";
inputs.getRange("C18:C19").format.numberFormat = "0.0%";
inputs.getRange("C21:C21").format.numberFormat = "0.0%";
inputs.getRange("C5:C21").format.horizontalAlignment = "right";
inputs.getRange("A23:C23").values = [["业态", "配比", "说明"]];
styleHeader(inputs, "A23:C23");
const mixRows = mixEntries.map(([name, value]) => [name, value, "模型假设"]);
inputs.getRange(`A24:C${23 + mixRows.length}`).values = mixRows;
inputs.getRange(`B24:B${23 + mixRows.length}`).format = {
  font: { color: inputBlue },
  numberFormat: "0.0%",
};
inputs.getRange("A:D").format.columnWidth = 20;
inputs.getRange("B:B").format.columnWidth = 24;
inputs.getRange("D:D").format.columnWidth = 22;
inputs.freezePanes.freezeRows(4);

indicators.mergeCells("A1:D2");
indicators.getRange("A1").values = [["指标测算"]];
styleTitle(indicators, "A1:D2");
indicators.getRange("A4:D4").values = [["指标", "公式/来源", "测算结果", "单位"]];
styleHeader(indicators, "A4:D4");
const indicatorLabels = [
  ["总用地面积", "='参数输入'!C5", null, "m²"],
  ["目标容积率", "=MIN('参数输入'!C8,'参数输入'!C9)", null, "-"],
  ["总建筑面积", "=C5*C6", null, "m²"],
  ["建筑基底上限", "=C5*'参数输入'!C10", null, "m²"],
  ["平均层数", "=ROUNDUP(C7/C8,0)", null, "层"],
  ["实际建筑基底", "=C7/C9", null, "m²"],
  ["实际建筑密度", "=C10/C5", null, "%"],
  ["绿地面积", "=C5*'参数输入'!C11", null, "m²"],
  ["公共空间面积", "=C5*'参数输入'!C12", null, "m²"],
  ["停车位", "=ROUNDUP(C7/1000*'参数输入'!C14,0)", null, "个"],
  ["新增建筑面积", "=MAX(0,C7-'参数输入'!C6)", null, "m²"],
];
indicators.getRange("A5:B15").values = indicatorLabels.map((row) => [row[0], `'${row[1]}`]);
indicators.getRange("D5:D15").values = indicatorLabels.map((row) => [row[3]]);
indicators.getRange("C5:C15").formulas = indicatorLabels.map((row) => [row[1]]);
indicators.getRange("C5:C15").format.font = { color: green };
indicators.getRange("C5:C10").format.numberFormat = "#,##0.0";
indicators.getRange("C11").format.numberFormat = "0.0%";
indicators.getRange("C12:C15").format.numberFormat = "#,##0.0";
indicators.getRange("A17:C17").values = [["业态", "配比", "建筑面积（m²）"]];
styleHeader(indicators, "A17:C17");
const mixStart = 24;
const mixOutput = mixEntries.map(([name], idx) => [
  name,
  `='参数输入'!B${mixStart + idx}`,
  `=$C$7*B${18 + idx}`,
]);
indicators.getRange(`A18:A${17 + mixOutput.length}`).values = mixOutput.map((row) => [row[0]]);
indicators.getRange(`B18:C${17 + mixOutput.length}`).formulas = mixOutput.map((row) => [row[1], row[2]]);
indicators.getRange(`B18:C${17 + mixOutput.length}`).format.font = { color: green };
indicators.getRange(`B18:B${17 + mixOutput.length}`).format.numberFormat = "0.0%";
indicators.getRange(`C18:C${17 + mixOutput.length}`).format.numberFormat = "#,##0";
indicators.getRange("A:D").format.columnWidth = 24;
indicators.getRange("B:B").format.columnWidth = 30;
indicators.freezePanes.freezeRows(4);

finance.mergeCells("A1:D2");
finance.getRange("A1").values = [["财务测算"]];
styleTitle(finance, "A1:D2");
finance.getRange("A4:D4").values = [["项目", "计算逻辑", "金额", "单位"]];
styleHeader(finance, "A4:D4");
const financeRows = [
  ["新建工程", "新增建筑面积×新建单价", "='指标测算'!C15*'参数输入'!C15", "元"],
  ["存量改造", "改造面积×改造单价", "='参数输入'!C7*'参数输入'!C16", "元"],
  ["公共空间", "公共空间面积×单价", "='指标测算'!C13*'参数输入'!C17", "元"],
  ["直接工程费", "以上三项合计", "=SUM(C5:C7)", "元"],
  ["其他费用", "直接工程费×其他费用率", "=C8*'参数输入'!C18", "元"],
  ["预备费", "（直接工程费+其他费用）×预备费率", "=(C8+C9)*'参数输入'!C19", "元"],
  ["总投资", "直接工程费+其他费用+预备费", "=SUM(C8:C10)", "元"],
  ["直接收益", "新增面积×价值单价×实现比例", "='指标测算'!C15*'参数输入'!C20*'参数输入'!C21", "元"],
  ["资金缺口", "总投资-直接收益", "=C11-C12", "元"],
  ["单位建筑面积成本", "总投资/总建筑面积", "=C11/'指标测算'!C7", "元/m²"],
];
finance.getRange("A5:B14").values = financeRows.map((row) => row.slice(0, 2));
finance.getRange("C5:C14").formulas = financeRows.map((row) => [row[2]]);
finance.getRange("D5:D14").values = financeRows.map((row) => [row[3]]);
finance.getRange("C5:C14").format = { font: { color: green }, numberFormat: "#,##0;[Red](#,##0);-" };
finance.getRange("A11:D11").format = { fill: lightBlue, font: { bold: true, color: navy } };
finance.getRange("A13:D13").format = { fill: yellow, font: { bold: true, color: red } };
finance.mergeCells("A16:D17");
finance.getRange("A16").values = [[scenario.finance.warning]];
finance.getRange("A16:D17").format = { fill: lightGray, font: { italic: true, color: navy }, wrapText: true };
finance.getRange("A:A").format.columnWidth = 22;
finance.getRange("B:B").format.columnWidth = 38;
finance.getRange("C:C").format.columnWidth = 20;
finance.getRange("D:D").format.columnWidth = 14;
finance.freezePanes.freezeRows(4);

const projectHeaders = [
  "项目编码", "项目名称", "策划目标", "实施时序", "更新方式",
  "示意建筑面积（m²）", "预期效益", "状态", "需复核",
];
projectSheet.getRange("A1:I1").values = [projectHeaders];
projectSheet.getRange(`A2:I${projects.length}`).values = projects.slice(1);
projectSheet.getRange("A1:I1").format = { fill: navy, font: { bold: true, color: white }, wrapText: true };
projectSheet.getRange(`A1:I${projects.length}`).format.borders = { preset: "outside", style: "thin", color: border };
projectSheet.getRange("A:A").format.columnWidth = 24;
projectSheet.getRange("B:B").format.columnWidth = 25;
projectSheet.getRange("C:C").format.columnWidth = 24;
projectSheet.getRange("D:F").format.columnWidth = 18;
projectSheet.getRange("G:H").format.columnWidth = 20;
projectSheet.getRange("I:I").format.columnWidth = 14;
projectSheet.getRange(`A1:I${projects.length}`).format.wrapText = true;
projectSheet.freezePanes.freezeRows(1);

sourceSheet.getRange("A1:H1").values = [[
  "序号", "知识库", "来源文件", "PDF页码", "文件状态", "抽取方式", "置信度", "原文证据"
]];
styleHeader(sourceSheet, "A1:H1");
const sourceRows = evidence.slice(0, 30).map((item, idx) => [
  idx + 1,
  item.knowledge_base,
  item.source_file,
  item.pdf_page,
  item.document_status,
  item.extraction_method,
  item.confidence,
  item.quotation.replace(/\n/g, " "),
]);
sourceSheet.getRange(`A2:H${1 + sourceRows.length}`).values = sourceRows;
sourceSheet.getRange(`G2:G${1 + sourceRows.length}`).format.numberFormat = "0.0%";
sourceSheet.getRange(`A1:H${1 + sourceRows.length}`).format.wrapText = true;
sourceSheet.getRange("A:A").format.columnWidth = 8;
sourceSheet.getRange("B:B").format.columnWidth = 10;
sourceSheet.getRange("C:C").format.columnWidth = 36;
sourceSheet.getRange("D:G").format.columnWidth = 14;
sourceSheet.getRange("H:H").format.columnWidth = 70;
sourceSheet.freezePanes.freezeRows(1);

checks.mergeCells("A1:F2");
checks.getRange("A1").values = [["模型检查"]];
styleTitle(checks, "A1:F2");
checks.getRange("A4:F4").values = [["检查项", "实际值", "预期值", "差异", "容差", "状态"]];
styleHeader(checks, "A4:F4");
checks.getRange("A5:A9").values = [
  ["业态配比合计"],
  ["目标容积率不超上限"],
  ["建筑密度不超上限"],
  ["项目库存在"],
  ["证据记录存在"],
];
checks.getRange("B5:B9").formulas = [
  [`=SUM('参数输入'!B24:B${23 + mixEntries.length})`],
  ["='指标测算'!C6"],
  ["='指标测算'!C11"],
  [`=COUNTA('项目库'!A2:A${projects.length})`],
  [`=COUNTA('证据与复核'!A2:A${1 + sourceRows.length})`],
];
checks.getRange("C5:C9").formulas = [
  ["=1"],
  ["='参数输入'!C9"],
  ["='参数输入'!C10"],
  ["=1"],
  ["=1"],
];
checks.getRange("D5:D9").formulas = [
  ["=ABS(B5-C5)"],
  ["=MAX(0,B6-C6)"],
  ["=MAX(0,B7-C7)"],
  ["=MAX(0,C8-B8)"],
  ["=MAX(0,C9-B9)"],
];
checks.getRange("E5:E9").values = [[0.001], [0], [0], [0], [0]];
checks.getRange("F5:F9").formulas = [
  ["=IF(D5<=E5,\"OK\",\"检查\")"],
  ["=IF(D6<=E6,\"OK\",\"检查\")"],
  ["=IF(D7<=E7,\"OK\",\"检查\")"],
  ["=IF(D8<=E8,\"OK\",\"检查\")"],
  ["=IF(D9<=E9,\"OK\",\"检查\")"],
];
checks.getRange("B5:E5").format.numberFormat = "0.0%";
checks.getRange("B6:E6").format.numberFormat = "0.0";
checks.getRange("B7:E7").format.numberFormat = "0.0%";
checks.getRange("B5:F9").format.font = { color: green };
checks.getRange("F5:F9").conditionalFormats.add("containsText", {
  text: "OK",
  format: { fill: "#E2F0D9", font: { bold: true, color: "#006100" } },
});
checks.getRange("F5:F9").conditionalFormats.add("containsText", {
  text: "检查",
  format: { fill: "#FCE4D6", font: { bold: true, color: red } },
});
checks.getRange("A11:B15").values = [
  ["人工复核事项", "说明"],
  ...quality.review_items.map((item, idx) => [`R${idx + 1}`, item]),
];
styleHeader(checks, "A11:B11");
checks.getRange("A11:B15").format.wrapText = true;
checks.getRange("A:A").format.columnWidth = 30;
checks.getRange("B:B").format.columnWidth = 65;
checks.getRange("C:F").format.columnWidth = 16;

await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["封面", "参数输入", "指标测算", "财务测算", "项目库", "证据与复核", "检查"]) {
  const preview = await wb.render({ sheetName, autoCrop: "all", scale: 1.2, format: "png" });
  await fs.writeFile(
    path.join(previewDir, `${sheetName}.png`),
    new Uint8Array(await preview.arrayBuffer()),
  );
}

const inspect = await wb.inspect({
  kind: "table",
  range: "检查!A1:F15",
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 8,
});
console.log(inspect.ndjson);
const errors = await wb.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const output = await SpreadsheetFile.exportXlsx(wb);
const outputPath = path.join(outputDir, "片区更新项目库与测算.xlsx");
await output.save(outputPath);
console.log(outputPath);
