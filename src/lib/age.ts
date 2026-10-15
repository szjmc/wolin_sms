/** 年龄只根据出生日期动态计算，数据库不存 age。 */

export function calculateAge(birthDate: string | null | undefined): number | null {
  if (!birthDate) return null;
  const parts = birthDate.split("-").map(Number);
  if (parts.length < 3) return null;
  const year = parts[0];
  const month = parts[1];
  const day = parts[2];
  const today = new Date();
  let age = today.getFullYear() - year;
  const nowMonth = today.getMonth() + 1;
  const nowDay = today.getDate();
  if (nowMonth < month || (nowMonth === month && nowDay < day)) age -= 1;
  return age;
}

/** 年龄 > ageGt 等价于出生日期 <= 这一天，方便走索引。 */
export function birthDateCutoff(ageGt: number): string {
  const today = new Date();
  const year = today.getFullYear() - (ageGt + 1);
  let month = today.getMonth() + 1;
  let day = today.getDate();
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  if (month === 2 && day === 29 && !leap) day = 28;
  return `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
}

export function annualized(amount: unknown, period: string | null | undefined): string {
  const n = Number(amount ?? 0);
  if (period === "MONTH") return (n * 12).toFixed(2);
  return n.toFixed(2);
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
