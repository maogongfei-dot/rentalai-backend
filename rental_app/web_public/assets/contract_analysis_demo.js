/**
 * Phase 4 联调：与仓库内 contract_analysis/samples/sample_contract.txt 对齐的示例，
 * 供「填入示例文本 / 填入示例路径」一键预填（仅开发/自测，不参与生产逻辑）。
 */
(function (global) {
  /** 与 sample_contract.txt 一致，便于本地与 file-path 结果对照 */
  var SAMPLE_CONTRACT_TEXT =
    "ASSURED SHORTHOLD TENANCY AGREEMENT — SAMPLE (Part 4 fixed files)\n\n" +
    "This is a minimal demo contract text file for RentalAI document reader tests.\n\n" +
    "1. Rent: The rent shall be £850 per calendar month, payable in advance on the 1st of each month.\n\n" +
    "2. Deposit: A tenancy deposit of five weeks' rent shall be paid and protected in a government-approved scheme (DPS / TDS / MyDeposits). The landlord will provide prescribed information within 30 days.\n\n" +
    "3. Notice: The landlord may give not less than two months' notice to end the tenancy after the fixed term; the tenant may give not less than one month's notice.\n\n" +
    "4. Repairs: The landlord is responsible for structural repairs; the tenant must report defects promptly.\n\n" +
    "5. Entry: The landlord or agent may enter for inspections with at least 24 hours' written notice except in genuine emergencies.\n";

  /** 相对 rental_app 根，供 POST /api/contract/analysis/file-path */
  var SAMPLE_FILE_PATH = "contract_analysis/samples/sample_contract.txt";

  global.RentalAIContractAnalysisDemo = {
    SAMPLE_CONTRACT_TEXT: SAMPLE_CONTRACT_TEXT,
    SAMPLE_FILE_PATH: SAMPLE_FILE_PATH,
  };
})(window);
