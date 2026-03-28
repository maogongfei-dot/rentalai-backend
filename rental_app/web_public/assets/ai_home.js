/**
 * P10-4：AI 首页 → POST /api/ai/query → sessionStorage ai_housing_query_last → /ai-result
 */
(function () {
  var ta = document.getElementById("ai-query");
  var btn = document.getElementById("ai-go");
  var err = document.getElementById("ai-err");
  if (!btn || !ta) return;

  function showErr(msg) {
    if (!err) return;
    err.textContent = msg;
    err.classList.remove("hidden");
  }
  function clearErr() {
    if (!err) return;
    err.classList.add("hidden");
    err.textContent = "";
  }

  function submit() {
    var q = (ta.value || "").trim();
    if (!q) {
      showErr("请输入需求后再试（不能只含空格）");
      return;
    }
    clearErr();
    btn.disabled = true;
    var apiBase =
      typeof window.RENTALAI_API_BASE === "string"
        ? window.RENTALAI_API_BASE.replace(/\/$/, "")
        : "";
    fetch(apiBase + "/api/ai/query", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_text: q }),
    })
      .then(function (r) {
        return r.json().then(function (body) {
          if (!r.ok) {
            throw new Error((body && body.message) || "请求失败");
          }
          return body;
        });
      })
      .then(function (data) {
        try {
          sessionStorage.setItem("ai_housing_query_last", JSON.stringify(data));
        } catch (e) {
          showErr("无法保存结果，请检查浏览器是否禁用存储");
          return;
        }
        window.location.href = "/ai-result";
      })
      .catch(function (e) {
        showErr(e.message || "网络错误");
      })
      .finally(function () {
        btn.disabled = false;
      });
  }

  btn.addEventListener("click", submit);
  ta.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  });
})();
