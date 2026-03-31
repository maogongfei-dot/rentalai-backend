/**
 * Phase 4 Round7：智能入口 — 本地 intent 分流、自动跳转、unclear 二选一（sessionStorage）
 */
(function () {
  var AI = window.RentalAIAssistantIntent;
  var ta = document.getElementById("assistant-input");
  var btn = document.getElementById("assistant-submit");
  var msg = document.getElementById("assistant-msg");
  var panel = document.getElementById("assistant-intent-panel");
  var panelBody = document.getElementById("assistant-intent-body");
  var KEY = "rentalai_assistant_draft";

  if (!ta || !btn || !AI) return;

  function showMsg(text, ok) {
    if (!msg) return;
    msg.textContent = text;
    msg.classList.remove("hidden", "save-banner-ok", "save-banner-err");
    msg.classList.add(ok ? "save-banner-ok" : "save-banner-err");
  }

  function clearIntentPanel() {
    if (panel) panel.classList.add("hidden");
    if (panelBody) panelBody.innerHTML = "";
  }

  function renderIntentResult(result, draft) {
    if (!panel || !panelBody) return;
    panel.classList.remove("hidden");
    panelBody.innerHTML = "";

    var intent = result.intent;
    var sc = result.scores || { property: 0, contract: 0 };

    function go(targetIntent) {
      var spec = AI.routeUserQuery(targetIntent, draft);
      if (spec && spec.href) window.location.href = spec.href;
    }

    function mkBtn(label, isPrimary, onClick) {
      var b = document.createElement("button");
      b.type = "button";
      b.textContent = label;
      b.className = isPrimary
        ? "assistant-intent-btn assistant-intent-btn--primary"
        : "assistant-intent-btn";
      b.addEventListener("click", onClick);
      return b;
    }

    var label = document.createElement("p");
    label.className = "assistant-intent-label";
    if (intent === AI.INTENT_PROPERTY) {
      label.textContent = "判断为：房源分析（property_analysis）";
    } else if (intent === AI.INTENT_CONTRACT) {
      label.textContent = "判断为：合同分析（contract_analysis）";
    } else {
      label.textContent =
        "暂未明确偏向（unclear）— 请任选一条主流程，描述会一并带上。";
    }
    panelBody.appendChild(label);

    if (intent === AI.INTENT_UNCLEAR) {
      var tip = document.createElement("p");
      tip.className = "hint muted assistant-intent-unclear-tip";
      tip.innerHTML =
        "<strong>怎么选？</strong> 提到预算、区域、卧室、通勤等多为<strong>找房</strong>；提到押金、条款、租约、解约等多为<strong>审合同</strong>。也可直接点下方按钮。";
      panelBody.appendChild(tip);
    }

    var hint = document.createElement("p");
    hint.className = "hint assistant-intent-scores";
    hint.textContent =
      "关键词得分 · 房源: " + sc.property + " · 合同: " + sc.contract;
    panelBody.appendChild(hint);

    var row = document.createElement("div");
    row.className = "assistant-intent-actions";

    if (intent === AI.INTENT_PROPERTY) {
      row.appendChild(mkBtn("前往房源分析", true, function () {
        go(AI.INTENT_PROPERTY);
      }));
      row.appendChild(mkBtn("改为合同分析", false, function () {
        go(AI.INTENT_CONTRACT);
      }));
    } else if (intent === AI.INTENT_CONTRACT) {
      row.appendChild(mkBtn("前往合同分析", true, function () {
        go(AI.INTENT_CONTRACT);
      }));
      row.appendChild(mkBtn("改为房源分析", false, function () {
        go(AI.INTENT_PROPERTY);
      }));
    } else {
      row.className =
        "assistant-intent-actions assistant-intent-actions--unclear";
      row.appendChild(mkBtn("去房源分析", true, function () {
        go(AI.INTENT_PROPERTY);
      }));
      row.appendChild(mkBtn("去合同分析", true, function () {
        go(AI.INTENT_CONTRACT);
      }));
    }
    panelBody.appendChild(row);
  }

  try {
    var prev = sessionStorage.getItem(KEY);
    if (prev) ta.value = prev;
  } catch (e) {}

  btn.addEventListener("click", function () {
    clearIntentPanel();
    var t = (ta.value || "").trim();
    if (!t) {
      showMsg("请先输入描述。", false);
      return;
    }

    var result = AI.detectUserIntent(t);

    if (result.intent === AI.INTENT_PROPERTY || result.intent === AI.INTENT_CONTRACT) {
      try {
        sessionStorage.setItem(KEY, t);
      } catch (err) {
        showMsg("无法写入浏览器存储，请检查是否禁用 sessionStorage。", false);
        return;
      }
      var spec = AI.routeUserQuery(result.intent, t);
      if (spec && spec.href) {
        window.location.href = spec.href;
        return;
      }
    }

    try {
      AI.routeUserQuery(AI.INTENT_UNCLEAR, t);
    } catch (e2) {}

    showMsg(
      "暂未识别明确倾向（unclear）。请在下方二选一进入流程，你的描述会一并带上。",
      true
    );
    renderIntentResult(result, t);
  });
})();
