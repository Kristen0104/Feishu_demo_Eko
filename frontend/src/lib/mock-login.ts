/**
 * 纯前端演示登录（不请求后端）。设置 NEXT_PUBLIC_EKO_MOCK_LOGIN=false 可关闭。
 */

export const EKO_MOCK_EMAIL = "demo@eko.local";
export const EKO_MOCK_PASSWORD = "demo1234";

/** 占位 token；仅当 NEXT_PUBLIC_EKO_VALIDATE_TOKEN=true 时会请求 /api/v1/auth/me 校验 */
export const EKO_MOCK_ACCESS_TOKEN = "eko_mock_access_token_dev_only";

export function isMockLoginEnabled(): boolean {
  return process.env.NEXT_PUBLIC_EKO_MOCK_LOGIN !== "false";
}

export function matchesMockCredentials(email: string, password: string): boolean {
  return email.trim().toLowerCase() === EKO_MOCK_EMAIL && password === EKO_MOCK_PASSWORD;
}
