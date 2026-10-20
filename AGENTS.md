# 全局约定

## 数学公式输出

- 需要结构的公式（分式、根号、上下限、矩阵、多行对齐）用围栏代码块，语言标记写 `math`：

```math
\frac{a}{b} = \sqrt{c} \qquad (1)
```

- 不要使用 `$...$`、`$$...$$`、`\[...\]`、`\(...\)`，终端不渲染行内公式，只会显示源码。
- 单字符符号直接写 Unicode：α、β、γ、∂、∇、∑、∏、∫、≤、≥、≠、≈、≡、→、∞、x²、xᵢ。
- 编号写在行尾 `\qquad (n)`，不要用 `\tag`。
- 单个 `math` 块不超过 6 行、约 80 列；多步推导用 `\begin{aligned} ... \end{aligned}` 并以 `&` 对齐等号。
- 渲染器只支持 KaTeX 子集：`\frac`、`\sqrt`、`\sum`、`\int`、`\prod`、`\partial`、`\nabla`、`\cdot`、`\times`、`\left`、`\right`、`\text`、`\overline`、`\hat`、`\vec`，环境 `aligned`、`align`、`cases`、`matrix`、`pmatrix`、`bmatrix`、`gathered`、`array`。
- 避免 `\tag`、`\mathrm`、`\middle`、`\substack` 等不支持的命令，它们会让整个块回退成源码。
