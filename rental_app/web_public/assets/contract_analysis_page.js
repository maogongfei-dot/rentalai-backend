/**
 * Phase 4 合同分析页：占位逻辑（文件名展示）。API 调用在后续步骤接入。
 */
(function () {
  var input = document.getElementById("contract-file-input");
  var nameEl = document.getElementById("contract-file-name");
  if (!input || !nameEl) return;

  input.addEventListener("change", function () {
    var f = input.files && input.files[0];
    nameEl.textContent = f ? "已选择：" + f.name : "";
  });
})();
