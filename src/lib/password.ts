import { compare, hash } from "bcryptjs";
import { scrypt, timingSafeEqual } from "node:crypto";
import { promisify } from "node:util";

const scryptAsync = promisify(scrypt);

/** 新建、重置密码统一使用 bcrypt，与 Python 后端兼容；密码不去除空格。 */
export function passwordError(value: unknown): string | null {
  if (typeof value !== "string" || value.length < 6) return "密码至少需要 6 个字符";
  if (Buffer.byteLength(value, "utf8") > 72) return "密码 UTF-8 长度不能超过 72 字节";
  return null;
}

export async function hashPassword(password: string): Promise<string> {
  const invalid = passwordError(password);
  if (invalid) throw new Error(invalid);
  return hash(password, 12);
}

/** 兼容旧版预览的 scrypt 哈希；格式错误只能登录失败，不能造成 500。 */
export async function verifyPassword(password: string, stored: string): Promise<boolean> {
  if (!password || Buffer.byteLength(password, "utf8") > 72) return false;
  try {
    if (/^\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}$/.test(stored)) {
      return await compare(password, stored.replace(/^\$2y\$/, "$2b$"));
    }
    // 旧版格式：32 位十六进制盐值 + 冒号 + 128 位哈希。验证后由登录接口迁移。
    if (!/^[0-9a-f]{32}:[0-9a-f]{128}$/i.test(stored)) return false;
    const [salt, digest] = stored.split(":");
    const actual = await scryptAsync(password, salt, 64) as Buffer;
    return timingSafeEqual(actual, Buffer.from(digest, "hex"));
  } catch {
    return false;
  }
}
