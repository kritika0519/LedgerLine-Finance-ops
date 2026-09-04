import { describe, expect, it } from "vitest";
import { deriveDashboardData } from "./utils";

describe("dashboard data derivation", () => {
  it("calculates settlement buckets and amount mismatch totals from API records", () => {
    const result = deriveDashboardData([
      { final_status: "DATE_MISMATCH", date_difference: 4, amount_difference: 0 },
      { final_status: "AMOUNT_MISMATCH", date_difference: 0, amount_difference: -125.5 },
      { final_status: "AMOUNT_MISMATCH", date_difference: 0, amount_difference: 25 },
    ]);

    expect(result.settlement).toEqual({ "4 days": 1 });
    expect(result.amountMismatchTotal).toBe(150.5);
  });
});