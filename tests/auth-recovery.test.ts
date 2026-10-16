import assert from "node:assert/strict";
import { randomBytes, scryptSync } from "node:crypto";
import { test } from "node:test";
import { hashPassword, passwordError, verifyPassword } from "../src/lib/password";

// 纯密码层回归，不读取任何账号库，也不含真实密码。
test("new passwords use bcrypt and match correctly", async () => {
  const password = randomBytes(16).toString("hex");
  const digest = await hashPassword(password);
  assert.match(digest, /^\$2b\$12\$/);
  assert.equal(await verifyPassword(password, digest), true);
  assert.equal(await verifyPassword(password + "wrong", digest), false);
});

test("leading and trailing spaces are retained", async () => {
  const password = " " + randomBytes(8).toString("hex") + " ";
  const digest = await hashPassword(password);
  assert.equal(await verifyPassword(password, digest), true);
  assert.equal(await verifyPassword(password.trim(), digest), false);
});

test("legacy scrypt hash still works", async () => {
  const password = randomBytes(12).toString("hex");
  const salt = randomBytes(16).toString("hex");
  const digest = `${salt}:${scryptSync(password, salt, 64).toString("hex")}`;
  assert.equal(await verifyPassword(password, digest), true);
  assert.equal(await verifyPassword("incorrect", digest), false);
});

test("invalid hashes cannot crash login or accept a password", async () => {
  for (const digest of ["", "plain-text", "salt:invalid", "a:b", "$2b$12$short", "a".repeat(32) + ":" + "0".repeat(10)]) {
    assert.equal(await verifyPassword("some-password", digest), false);
  }
});

test("bcrypt input length is validated by UTF-8 bytes", async () => {
  assert.equal(passwordError("a".repeat(72)), null);
  assert.notEqual(passwordError("a".repeat(73)), null);
  assert.notEqual(passwordError("中文".repeat(13)), null);
  await assert.rejects(() => hashPassword("中文".repeat(13)));
});

test("resetting password changes salted hash and invalidates old password", async () => {
  const before = randomBytes(10).toString("hex");
  const after = randomBytes(12).toString("hex");
  const oldHash = await hashPassword(before);
  const newHash = await hashPassword(after);
  assert.notEqual(oldHash, newHash);
  assert.equal(await verifyPassword(before, newHash), false);
  assert.equal(await verifyPassword(after, newHash), true);
});
