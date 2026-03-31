/**
 * Phase 4 Round7 Step2：智能入口 — 本地关键词意图识别（无 AI / 无后端）
 * 导出：detectUserIntent、routeUserQuery
 */
(function (global) {
  /** @typedef {'property_analysis'|'contract_analysis'|'unclear'} AssistantIntent */

  var INTENT_PROPERTY = "property_analysis";
  var INTENT_CONTRACT = "contract_analysis";
  var INTENT_UNCLEAR = "unclear";

  /**
   * 英文 + 中文常见词；长词组放前，避免被子串误伤（简单扫描仍可能重复计分，可接受 Demo 级）
   */
  var PROPERTY_PATTERNS = [
    "compare property",
    "compare houses",
    "per calendar month",
    "pcm",
    "postcode",
    "bedrooms",
    "bedroom",
    "commute",
    "budget",
    "bills",
    "listings",
    "zoopla",
    "rightmove",
    "flat",
    "studio",
    "rent",
    "£",
    "月租",
    "预算",
    "通勤",
    "邮编",
    "卧室",
    "一居室",
    "两居室",
    "三居室",
    "一居",
    "两居",
    "三居",
    "房源",
    "租房",
    "找房",
    "比房",
    "区域",
    "地段",
    "性价比",
    "租金",
  ];

  var CONTRACT_PATTERNS = [
    "tenancy agreement",
    "break clause",
    "landlord",
    "tenant",
    "sublet",
    "notice period",
    "tenancy",
    "contract",
    "clause",
    "deposit",
    "repair",
    "fee",
    "notice",
    "合同",
    "条款",
    "房东",
    "租客",
    "押金",
    "维修费",
    "维修",
    "租约",
    "解约",
    "通知期",
    "违约金",
    "转租",
    "续租",
    "涨租",
  ];

  function normalizeAsciiLower(s) {
    return String(s || "").toLowerCase();
  }

  /**
   * 统计关键词命中次数（每个词最多计 1 次；中英分轨匹配）
   * @param {string} raw
   * @param {string[]} patterns
   */
  function countKeywordHits(raw, patterns) {
    var text = String(raw || "");
    var lower = normalizeAsciiLower(text);
    var score = 0;
    var i;
    for (i = 0; i < patterns.length; i++) {
      var p = patterns[i];
      if (!p) continue;
      if (/[\u4e00-\u9fff]/.test(p)) {
        if (text.indexOf(p) !== -1) score += 1;
      } else if (lower.indexOf(normalizeAsciiLower(p)) !== -1) {
        score += 1;
      }
    }
    return score;
  }

  /**
   * @param {string} rawUserText
   * @returns {{ intent: AssistantIntent, scores: { property: number, contract: number }, reason?: string }}
   */
  function detectUserIntent(rawUserText) {
    var t = String(rawUserText || "").trim();
    if (!t) {
      return {
        intent: INTENT_UNCLEAR,
        scores: { property: 0, contract: 0 },
        reason: "empty",
      };
    }

    var ps = countKeywordHits(t, PROPERTY_PATTERNS);
    var cs = countKeywordHits(t, CONTRACT_PATTERNS);

    if (ps === 0 && cs === 0) {
      return {
        intent: INTENT_UNCLEAR,
        scores: { property: ps, contract: cs },
        reason: "no_keywords",
      };
    }
    if (ps > cs) {
      return {
        intent: INTENT_PROPERTY,
        scores: { property: ps, contract: cs },
        reason: "property_higher",
      };
    }
    if (cs > ps) {
      return {
        intent: INTENT_CONTRACT,
        scores: { property: ps, contract: cs },
        reason: "contract_higher",
      };
    }
    return {
      intent: INTENT_UNCLEAR,
      scores: { property: ps, contract: cs },
      reason: "tie",
    };
  }

  var DRAFT_KEY = "rentalai_assistant_draft";
  var INTENT_KEY = "rentalai_assistant_intent";
  /** 目标页消费一次后 remove，用于预填 #ai-query / contract-text */
  var NAV_KEY = "rentalai_assistant_navigate";

  /**
   * 写入草稿、意图与一次性导航标记；返回建议 href（由调用方 location.href）
   * @param {AssistantIntent} intent
   * @param {string} [draftText]
   * @returns {{ href: string|null, intent: AssistantIntent }}
   */
  function routeUserQuery(intent, draftText) {
    try {
      if (draftText != null) {
        sessionStorage.setItem(DRAFT_KEY, String(draftText));
      }
      sessionStorage.setItem(INTENT_KEY, intent);
      if (intent === INTENT_PROPERTY) {
        sessionStorage.setItem(NAV_KEY, "property");
      } else if (intent === INTENT_CONTRACT) {
        sessionStorage.setItem(NAV_KEY, "contract");
      } else {
        sessionStorage.removeItem(NAV_KEY);
      }
    } catch (e) {}
    if (intent === INTENT_PROPERTY) {
      return { href: "/#ai-rental-heading", intent: intent };
    }
    if (intent === INTENT_CONTRACT) {
      return { href: "/contract-analysis", intent: intent };
    }
    return { href: null, intent: INTENT_UNCLEAR };
  }

  global.RentalAIAssistantIntent = {
    INTENT_PROPERTY: INTENT_PROPERTY,
    INTENT_CONTRACT: INTENT_CONTRACT,
    INTENT_UNCLEAR: INTENT_UNCLEAR,
    DRAFT_KEY: DRAFT_KEY,
    INTENT_KEY: INTENT_KEY,
    NAV_KEY: NAV_KEY,
    detectUserIntent: detectUserIntent,
    routeUserQuery: routeUserQuery,
  };
})(window);
