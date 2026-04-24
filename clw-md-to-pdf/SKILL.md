# md-to-pdf

把 Markdown 檔案轉成 PDF，**不需要安裝任何工具**（只要有 Chrome 就夠）。

## 工作流程

```
Markdown → HTML（pandoc）→ PDF（Chrome headless）
```

## 觸發方式

用戶說「轉 PDF」「md 轉 pdf」「convert to PDF」時使用。

## 使用方式

```
python3 md_to_pdf.py <input.md> [output.pdf]
```

- `input.md`：必填，要轉換的 Markdown 檔案
- `output.pdf`：選填，預設輸出到 input 同目錄的同名檔（.md → .pdf）

## 需求

- [pandoc](https://pandoc.org/)：`brew install pandoc`
- Google Chrome（macOS 內建）

## 流程說明

1. 用 pandoc 把 md 轉成 HTML
2. 用 Chrome headless 把 HTML 輸出成 PDF
3. 自動開啟 Finder 並選中輸出檔案

## 限制

- 複雜表格、數學公式（LaTeX）在 PDF 中可能呈現不完整
- 圖片建議使用相對路徑或網址，絕對路徑在 headless 模式可能失效
