/**
 * Phase 4 Round7：智能入口 → 目标页一次性预填（与 assistant_intent.js 键名一致）
 * consumeAssistantHandoff 仅应调用一次：会移除 rentalai_assistant_navigate，避免刷新反复写回。
 */
(function (global) {
  var NAV_KEY = "rentalai_assistant_navigate";
  var DRAFT_KEY = "rentalai_assistant_draft";

  /**
   * @param {"property"|"contract"} target
   * @returns {{ draft: string|null, consumed: boolean }|null} nav 不匹配时返回 null（不删键）
   */
  function consumeAssistantHandoff(target) {
    try {
      var nav = sessionStorage.getItem(NAV_KEY);
      if (nav !== target) return null;
      var draft = sessionStorage.getItem(DRAFT_KEY);
      sessionStorage.removeItem(NAV_KEY);
      return {
        draft: draft != null ? String(draft) : null,
        consumed: true,
      };
    } catch (e) {
      return null;
    }
  }

  global.RentalAIAssistantPrefill = {
    NAV_KEY: NAV_KEY,
    DRAFT_KEY: DRAFT_KEY,
    consumeAssistantHandoff: consumeAssistantHandoff,
  };
})(window);
