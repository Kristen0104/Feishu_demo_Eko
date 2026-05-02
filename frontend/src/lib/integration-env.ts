/** When true, login calls POST `/api/v1/auth/dev/token` after mock credential check (backend needs ALLOW_DEV_TOKEN=true). */
export function shouldFetchBackendDevToken(): boolean {
  return process.env.NEXT_PUBLIC_EKO_USE_DEV_AUTH === "true";
}
