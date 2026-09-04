export const formatNumber = (value) => new Intl.NumberFormat("en-US").format(Number(value || 0));
export const formatPercent = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;
export const formatMoney = (value) => new Intl.NumberFormat("en-US", {
  style: "currency", currency: "USD", maximumFractionDigits: 2,
}).format(Number(value || 0));

export function chartEntries(values = {}) {
  return Object.entries(values).sort(([, a], [, b]) => b - a);
}

export function deriveDashboardData(records = []) {
  const settlement = {};
  let amountMismatchTotal = 0;
  records.forEach((record) => {
    if (record.final_status === "DATE_MISMATCH") {
      const bucket = `${Math.max(0, Math.round(Number(record.date_difference || 0)))} days`;
      settlement[bucket] = (settlement[bucket] || 0) + 1;
    }
    if (record.final_status === "AMOUNT_MISMATCH") {
      amountMismatchTotal += Math.abs(Number(record.amount_difference || 0));
    }
  });
  return { settlement, amountMismatchTotal };
}