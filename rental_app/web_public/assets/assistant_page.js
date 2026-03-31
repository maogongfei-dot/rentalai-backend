/**
 * Phase 4 Round7 Step1：智能入口 — 仅保存草稿到 sessionStorage（rentalai_assistant_draft）
 */
(function () {
  var ta = document.getElementById("assistant-input");
  var btn = document.getElementById("assistant-submit");
  var msg = document.getElementById("assistant-msg");
  var KEY = "rentalai_assistant_draft";

  if (!ta || !btn) return;

  try {
    var prev = sessionStorage.getItem(KEY);
    if (prev) ta.value = prev;
  } catch (e) {}

  btn.addEventListener("click", function () {
    var t = (ta.value || "").trim();
    if (!t) {
      if (msg) {
        msg.textContent = "请先输入描述，再保存草稿。";
        msg.classList.remove("hidden", "save-banner-ok");
        msg.classList.add("save-banner-err");
      }
      return;
    }
    try {
      sessionStorage.setItem(KEY, t);
    } catch (e) {
      if (msg) {
        msg.textContent = "无法写入浏览器存储，请检查是否禁用 sessionStorage。";
        msg.classList.remove("hidden", "save-banner-ok");
        msg.classList.add("save-banner-err");
      }
      return;
    }
    if (msg) {
      msg.textContent =
        "草稿已保存在本机会话。你可从下方链接进入房源分析或合同分析；后续将支持自动识别意图并预填。";
      msg.classList.remove("hidden", "save-banner-err");
      msg.classList.add("save-banner-ok");
    }
  });
})();
